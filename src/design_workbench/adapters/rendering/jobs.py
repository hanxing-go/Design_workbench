"""Bounded snapshot capture jobs, with owned process trees and explicit states."""

import base64
import hashlib
import json
import logging
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
import time
import uuid
from concurrent.futures import Future, ThreadPoolExecutor
from contextlib import suppress
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from design_workbench.application.render_contracts import RenderRequest
from design_workbench.config import Settings
from design_workbench.domain.errors import WorkbenchError
from design_workbench.domain.models import Bounds
from design_workbench.runtime import worker_command

from ..resources.catalog import Catalog
from ..resources.pack import ResourceManager, ResourcePack
from ..storage.sqlite import SqliteStore
from .capture_worker import write_json

LOGGER = logging.getLogger("design_workbench.render")
TERMINAL = {"succeeded", "failed", "timed_out", "cancelled"}


@dataclass
class CaptureJob:
    id: str
    revision: int
    resource_hash: str
    directory: Path
    digest: str
    started: float = field(default_factory=time.monotonic)
    state: str = "queued"
    result: dict[str, Any] = field(default_factory=dict)
    cancel: threading.Event = field(default_factory=threading.Event)
    done: threading.Event = field(default_factory=threading.Event)
    future: Future[None] | None = None
    finished: float | None = None


class RenderJobs:
    def __init__(self, settings: Settings, catalog: Catalog, pack: ResourcePack | None) -> None:
        self.settings, self.catalog, self.pack = settings, catalog, pack
        settings.cache_dir.mkdir(parents=True, exist_ok=True)
        self.directory = Path(tempfile.mkdtemp(prefix="dw-capture-", dir=settings.cache_dir))
        self.jobs: dict[str, CaptureJob] = {}
        self.requests: dict[tuple[str, str], str] = {}
        self.lock = threading.RLock()
        self.executor = ThreadPoolExecutor(
            max_workers=settings.render_workers, thread_name_prefix="capture"
        )
        self.closed = False

    def submit(self, project: Path, request: RenderRequest) -> dict[str, Any]:
        for index, view in enumerate(request.views):
            if (
                view.bounds
                and Bounds(view.bounds.low, view.bounds.high).volume
                > self.settings.max_selection_volume
            ):
                raise WorkbenchError(
                    "SELECTION_LIMIT", "截图取景范围超过空间预算。", f"views.{index}.bounds"
                )
        body = request.model_dump(mode="json", exclude={"wait"})
        digest = hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()
        key = (str(project.resolve()), request.request_id)
        with self.lock:
            if self.closed:
                raise WorkbenchError("RENDER_CLOSED", "截图服务已关闭。")
            identifier = self.requests.get(key)
            if identifier and identifier in self.jobs:
                job = self.jobs[identifier]
                if job.digest != digest:
                    raise WorkbenchError("REQUEST_ID_REUSED", "截图 request_id 已用于另一组参数。")
            else:
                version, data_version = SqliteStore(
                    project, self.settings.database_timeout
                ).game_version()
                catalog = self.catalog if version == self.catalog.version else Catalog(version)
                if data_version != catalog.data_version:
                    raise WorkbenchError("VERSION_MISMATCH", "项目游戏版本与 DataVersion 不一致。")
                pack = (
                    self.pack
                    if self.pack is not None and self.pack.manifest["minecraft_version"] == version
                    else ResourceManager(self.settings.cache_dir / "resources").active(version)
                )
                if pack is None:
                    raise WorkbenchError("RESOURCES_NOT_READY", "先通过 resources setup 安装资源。")
                if len(self.jobs) >= self.settings.max_render_jobs:
                    expired = next(
                        (item for item in self.jobs.values() if item.done.is_set()), None
                    )
                    if expired is None:
                        raise WorkbenchError(
                            "RENDER_QUEUE_FULL", "截图队列已满，请等待或取消任务。"
                        )
                    self._remove_directory(expired.directory)
                    self.jobs.pop(expired.id)
                    self.requests = {
                        key: value for key, value in self.requests.items() if value != expired.id
                    }
                scene, source = SqliteStore(project, self.settings.database_timeout).snapshot()
                if scene.revision != request.expected_revision:
                    raise WorkbenchError(
                        "REVISION_CONFLICT",
                        "截图前场景已修改，请重新观察。",
                        revision=scene.revision,
                    )
                if len(scene.cells) > self.settings.max_render_cells:
                    raise WorkbenchError(
                        "RENDER_CELL_LIMIT", "截图场景超过方块预算。", "scene.cells", scene.revision
                    )
                identifier = uuid.uuid4().hex
                directory = self.directory / identifier
                directory.mkdir()
                job = CaptureJob(
                    identifier, scene.revision, pack.manifest["bundle_hash"], directory, digest
                )
                self.jobs[identifier] = job
                self.requests[key] = identifier

                def run() -> None:
                    process: subprocess.Popen[bytes] | None = None
                    try:
                        if job.cancel.is_set():
                            job.state = "cancelled"
                            return
                        job.state = "preparing"
                        snapshot = {
                            "id": scene.id,
                            "name": scene.name,
                            "minecraft_version": scene.minecraft_version,
                            "data_version": scene.data_version,
                            "revision": scene.revision,
                            "bounds": scene.bounds.as_dict(),
                            "cells": [
                                [point, cell.as_dict()]
                                for point, cell in sorted(scene.cells.items())
                            ],
                            "protected": sorted(scene.protected),
                            "source": base64.b64encode(source).decode() if source else None,
                        }
                        if len(json.dumps(snapshot).encode()) > 96_000_000:
                            raise WorkbenchError(
                                "RENDER_SNAPSHOT_LIMIT", "截图快照超过 96 MB。", "scene"
                            )
                        write_json(directory / "snapshot.json", snapshot)
                        shutil.copyfile(pack.directory / "atlas.png", directory / "atlas.png")
                        write_json(
                            directory / "request.json",
                            {
                                **body,
                                "timeout": min(request.timeout, self.settings.render_timeout),
                                "browser_channel": self.settings.browser_channel,
                                "max_bytes": self.settings.max_render_bytes,
                                "pack_directory": str(pack.directory.resolve()),
                                "resource_hash": job.resource_hash,
                            },
                        )
                        timeout = min(request.timeout, self.settings.render_timeout)
                        if job.cancel.is_set():
                            job.state = "cancelled"
                            return
                        if time.monotonic() - job.started >= timeout:
                            job.state = "timed_out"
                            return
                        creationflags = 0
                        if sys.platform == "win32":
                            creationflags = subprocess.CREATE_NO_WINDOW
                        with (directory / "worker.log").open("wb") as log:
                            process = subprocess.Popen(
                                worker_command(
                                    "design_workbench.adapters.rendering.capture_worker",
                                    str(directory),
                                ),
                                stdout=log,
                                stderr=log,
                                stdin=subprocess.DEVNULL,
                                start_new_session=os.name != "nt",
                                creationflags=creationflags,
                            )
                            job.state = "running"
                            while process.poll() is None:
                                if job.cancel.wait(0.05):
                                    job.state = "cancelled"
                                    self._stop(process)
                                    return
                                if time.monotonic() - job.started >= timeout:
                                    job.state = "timed_out"
                                    self._stop(process)
                                    return
                        if not (directory / "result.json").is_file():
                            raise WorkbenchError(
                                "RENDER_FAILED", f"截图进程退出（{process.returncode}），没有结果。"
                            )
                        result = json.loads((directory / "result.json").read_text(encoding="utf-8"))
                        result["worker_elapsed_ms"] = result.pop("elapsed_ms", None)
                        job.result = result
                        job.state = "succeeded" if result["ok"] else "failed"
                    except Exception as error:
                        job.state = "failed"
                        job.result = {
                            "error": error.as_dict()
                            if isinstance(error, WorkbenchError)
                            else {
                                "code": "RENDER_FAILED",
                                "message": str(error)[:2000],
                                "location": "render",
                            }
                        }
                    finally:
                        if process is not None and process.poll() is None:
                            self._stop(process)
                        for filename in ("snapshot.json", "atlas.png", "request.json"):
                            (directory / filename).unlink(missing_ok=True)
                        if job.state != "succeeded":
                            for path in directory.glob("*.png"):
                                path.unlink()
                        job.finished = time.monotonic()
                        job.done.set()
                        LOGGER.info(
                            "render.finished",
                            extra={"task_id": job.id, "revision": job.revision, "state": job.state},
                        )

                job.future = self.executor.submit(run)
        if request.wait:
            job.done.wait(min(request.timeout, self.settings.render_timeout) + 3)
        return self.status(job.id)

    @staticmethod
    def _stop(process: subprocess.Popen[bytes]) -> None:
        if process.poll() is not None:
            return
        if sys.platform == "win32":
            subprocess.run(
                ["taskkill", "/PID", str(process.pid), "/T", "/F"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=10,
                check=False,
            )
        else:
            with suppress(ProcessLookupError):
                os.killpg(process.pid, signal.SIGKILL)
        process.wait(timeout=10)

    def status(self, identifier: str) -> dict[str, Any]:
        with self.lock:
            job = self.jobs.get(identifier)
            if job is None:
                raise WorkbenchError("RENDER_NOT_FOUND", "截图任务不存在或已被回收。", "task_id")
            result = {
                "schema_version": 1,
                "task_id": job.id,
                "status": job.state,
                "revision": job.revision,
                "resource_hash": job.resource_hash,
                "elapsed_ms": round(((job.finished or time.monotonic()) - job.started) * 1000, 2),
                **job.result,
            }
            progress = job.directory / "progress.json"
            if progress.is_file():
                result["progress"] = json.loads(progress.read_text(encoding="utf-8"))
            if job.state in {"timed_out", "cancelled"}:
                result["error"] = {
                    "code": "RENDER_TIMEOUT" if job.state == "timed_out" else "RENDER_CANCELLED",
                    "message": "截图已超时。" if job.state == "timed_out" else "截图已取消。",
                    "location": "render",
                }
            if job.state == "succeeded":
                result["images"] = [
                    {
                        **item,
                        "path": str(job.directory / item["file"]),
                        "revision": job.revision,
                        "resource_hash": job.resource_hash,
                    }
                    for item in job.result["images"]
                ]
            return result

    def image(self, identifier: str, index: int) -> Path:
        result = self.status(identifier)
        images = result.get("images", [])
        if result["status"] != "succeeded" or not 0 <= index < len(images):
            raise WorkbenchError("RENDER_IMAGE_NOT_FOUND", "截图尚未生成或图片编号非法。", "index")
        return Path(images[index]["path"])

    def cancel(self, identifier: str) -> dict[str, Any]:
        with self.lock:
            if identifier not in self.jobs:
                raise WorkbenchError("RENDER_NOT_FOUND", "截图任务不存在或已被回收。", "task_id")
            job = self.jobs[identifier]
            if not job.done.is_set():
                job.cancel.set()
                if job.future and job.future.cancel():
                    job.state = "cancelled"
                    job.finished = time.monotonic()
                    job.done.set()
        job.done.wait(12)
        return self.status(identifier)

    def close(self) -> None:
        with self.lock:
            self.closed = True
            for job in self.jobs.values():
                job.cancel.set()
                if job.future and job.future.cancel():
                    job.state = "cancelled"
                    job.finished = time.monotonic()
                    job.done.set()
        self.executor.shutdown(wait=True)
        self._remove_directory(self.directory)

    def _remove_directory(self, directory: Path) -> None:
        """Windows can briefly retain child log handles after process termination."""
        if not directory.resolve().is_relative_to(self.directory.resolve()):
            raise ValueError("只能清理此截图服务拥有的临时目录")
        deadline = time.monotonic() + 2
        while True:
            try:
                shutil.rmtree(directory)
                return
            except FileNotFoundError:
                if not directory.exists():
                    return
                raise
            except PermissionError:
                if sys.platform != "win32" or time.monotonic() >= deadline:
                    raise
                time.sleep(0.05)
