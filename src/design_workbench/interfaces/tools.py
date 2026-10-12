"""One versioned tool facade used by CLI, HTTP and MCP transports."""

import base64
import hashlib
import json
import os
import re
import subprocess
import sys
import threading
import uuid
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ValidationError

from design_workbench.adapters.rendering.jobs import RenderJobs
from design_workbench.adapters.resources.catalog import Catalog
from design_workbench.adapters.storage.sqlite import SqliteStore
from design_workbench.application.contracts import Selector
from design_workbench.application.design_contracts import (
    CandidateSave,
    DesignAction,
    DesignCall,
    DesignCreate,
    DesignFinish,
    DesignList,
    DesignPropose,
    DesignRef,
    DesignResume,
    DesignUpdate,
    DesignUsage,
)
from design_workbench.application.scenes import fingerprint
from design_workbench.application.tool_contracts import (
    CreateTool,
    EditTool,
    ExportTool,
    HistoryTool,
    ImportTool,
    InspectTool,
    MaterialTool,
    ProjectTool,
    RenderTool,
    SearchTool,
    TaskTool,
    ToolRequest,
)
from design_workbench.bootstrap import Workbench
from design_workbench.domain.errors import WorkbenchError
from design_workbench.domain.models import BlockState, Bounds
from design_workbench.interfaces.designs import Designs
from design_workbench.runtime import worker_command

TOOL_CONTRACTS: dict[str, tuple[type[BaseModel], str]] = {
    "design.start": (
        DesignCreate,
        "Start a persistent externally driven design task with explicit budget. This does not launch a model. Existing buildings require user approval for every edit.",
    ),
    "design.list": (DesignList, "List persistent design tasks for a project."),
    "design.status": (
        DesignRef,
        "Read stage, cumulative usage, remaining budget, pending proposal, candidates and recent events. Read again before continuing after a failure.",
    ),
    "design.update": (DesignUpdate, "Report the current design stage and progress message."),
    "design.usage": (
        DesignUsage,
        "Report cumulative actual external model counters and their source. Cached inputs are already included in input_tokens. Never invent usage or cost.",
    ),
    "design.call": (
        DesignCall,
        "Call an existing tool within the persistent task budget. scene.commit_edit becomes a pending preview for user approval. Read-only tools and actual screenshots are supported. Cancelled/failed tasks refuse further operations.",
    ),
    "design.propose": (
        DesignPropose,
        "Preview and persist a proposed edit with an explanation. Only the user-facing approval endpoint can apply it; poll design.status for the decision.",
    ),
    "design.cancel": (
        DesignAction,
        "Cancel a task and stop owned screenshot jobs; applied edits and saved candidates are retained.",
    ),
    "design.resume": (
        DesignResume,
        "Explicitly resume a stopped task, optionally extending its budget. Consumed counters are never reset; re-read the current scene revision.",
    ),
    "design.finish": (
        DesignFinish,
        "Record success or failure. Success requires at least one saved independent candidate.",
    ),
    "candidate.save": (
        CandidateSave,
        "Save an immutable complete SQLite candidate at an expected revision, including full block states, NBT and history, independently of undo/redo.",
    ),
    "catalog.search": (
        SearchTool,
        "Search versioned materials by Chinese/English name; bounded pagination.",
    ),
    "catalog.material": (
        MaterialTool,
        "Validate a block state; return legal properties, normalized state and render support.",
    ),
    "project.list": (ToolRequest, "List managed projects and revisions."),
    "versions.list": (
        ToolRequest,
        "List supported Java versions, DataVersions and installed resources. Each project keeps its own version; this does not convert projects.",
    ),
    "project.create": (
        CreateTool,
        "Create a project. Reuse the same request_id and arguments to retry safely.",
    ),
    "scene.summary": (
        ProjectTool,
        "Read scene revision, bounds, material counts, groups and history.",
    ),
    "scene.inspect": (
        InspectTool,
        "Inspect a selection by bounds, material, group or region; results include revision and truncation.",
    ),
    "scene.preview_edit": (
        EditTool,
        "Preview batched operations without writing. Commit still checks expected_revision.",
    ),
    "scene.commit_edit": (
        EditTool,
        "Atomically apply operations. Reuse request_id on retries. On REVISION_CONFLICT re-observe before editing.",
    ),
    "history.undo": (
        HistoryTool,
        "Undo one transaction; requires current revision and an idempotency key.",
    ),
    "history.redo": (
        HistoryTool,
        "Redo one transaction; requires current revision and an idempotency key.",
    ),
    "asset.import": (
        ImportTool,
        "Import a local litematic file into the project, with revision and idempotency checks.",
    ),
    "asset.export": (
        ExportTool,
        "Export current revision to a local litematic file and return hash and preservation report.",
    ),
    "render.views": (
        RenderTool,
        "Capture actual PNG views of an immutable revision. wait=false returns a task; use render.status/cancel. Images keep the captured revision even if users edit concurrently.",
    ),
    "render.status": (
        TaskTool,
        "Read screenshot progress/result; succeeded jobs include actual PNG images.",
    ),
    "render.cancel": (
        TaskTool,
        "Cancel a screenshot job and stop its owned browser processes; scene data is unaffected.",
    ),
}


def atomic_output(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.is_file() and path.read_bytes() == payload:
            return
        raise WorkbenchError("FILE_EXISTS", "输出目标已存在且内容不同；不会覆盖。", "output")
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        temporary.write_bytes(payload)
        # link is an atomic no-overwrite publish, including concurrent exporters.
        os.link(temporary, path)
    except FileExistsError as error:
        if path.read_bytes() != payload:
            raise WorkbenchError("FILE_EXISTS", "输出目标已被另一请求创建。", "output") from error
    finally:
        temporary.unlink(missing_ok=True)


class Tools:
    def __init__(self, workbench: Workbench, isolated: bool = True) -> None:
        self.workbench = workbench
        self.projects = workbench.settings.data_dir / "projects"
        self.projects.mkdir(parents=True, exist_ok=True)
        self._renderer: RenderJobs | None = None
        self._lock = threading.RLock()
        self.isolated = isolated
        self._designs: Designs | None = None

    @property
    def designs(self) -> Designs:
        with self._lock:
            if self._designs is None:
                self._designs = Designs(self)
            return self._designs

    @property
    def renderer(self) -> RenderJobs:
        with self._lock:
            if self._renderer is None:
                self._renderer = RenderJobs(
                    self.workbench.settings, self.workbench.catalog, self.workbench.pack
                )
            return self._renderer

    def close(self) -> None:
        if self._designs is not None:
            self._designs.close()
        if self._renderer is not None:
            self._renderer.close()

    def project_path(self, identifier: str) -> Path:
        if not re.fullmatch(r"[a-zA-Z0-9_-]{1,80}", identifier):
            raise WorkbenchError("INVALID_PROJECT_ID", "项目标识非法。", "project")
        return self.projects / f"{identifier}.dwbench"

    def descriptions(self) -> list[dict[str, Any]]:
        return [
            {"name": name, "description": description, "inputSchema": contract.model_json_schema()}
            for name, (contract, description) in TOOL_CONTRACTS.items()
        ]

    def call(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        if name not in TOOL_CONTRACTS:
            raise WorkbenchError("UNKNOWN_TOOL", "未知工具。", "tool")
        if len(json.dumps(arguments).encode()) > 4_000_000:
            raise WorkbenchError("TOOL_INPUT_LIMIT", "工具请求超过 4 MB。", "arguments")
        try:
            request = TOOL_CONTRACTS[name][0].model_validate(arguments)
        except ValidationError as error:
            item = error.errors()[0]
            raise WorkbenchError(
                "INVALID_REQUEST", item["msg"], ".".join(map(str, item["loc"]))
            ) from error
        is_design = name.startswith("design.") or name == "candidate.save"
        if not is_design and name in {
            "scene.commit_edit",
            "asset.import",
            "history.undo",
            "history.redo",
        }:
            runs = self.designs.store.list(str(arguments.get("project", "")))
            if runs and runs[0]["status"] != "succeeded":
                raise WorkbenchError(
                    "DESIGN_TASK_REQUIRED",
                    "此项目由设计任务管理，AI 修改请通过 design.call 或 design.propose；取消后必须明确继续任务。",
                )
        value = (
            self._design_dispatch(name, request)
            if is_design
            else self._bounded_call(name, arguments)
            if self.isolated and not name.startswith("render.")
            else self._dispatch(name, request)
        )
        value = {"schema_version": 1, **value}
        maximum = self.workbench.settings.max_tool_response_bytes
        for key in ("changes", "blocks", "items", "changed_chunks"):
            if key in value and isinstance(value[key], list):
                count = len(value[key])
                while value[key] and len(json.dumps(value, ensure_ascii=False).encode()) > maximum:
                    value[key] = value[key][: len(value[key]) // 2]
                if len(value[key]) < count:
                    value["response_truncated"] = True
                    value[f"{key}_total"] = count
        if len(json.dumps(value, ensure_ascii=False).encode()) > maximum:
            raise WorkbenchError("TOOL_OUTPUT_LIMIT", "工具响应超过预算，请缩小查询范围。")
        return value

    def _design_dispatch(self, name: str, request: BaseModel) -> dict[str, Any]:
        control = self.designs
        if isinstance(request, DesignCreate):
            return control.create(request)
        if isinstance(request, DesignList):
            return control.list(request.project)
        if isinstance(request, DesignCall):
            return control.call(request)
        if isinstance(request, DesignUsage):
            return control.usage(request)
        if isinstance(request, DesignPropose):
            return control.propose(request)
        if isinstance(request, DesignUpdate):
            return control.update(request)
        if isinstance(request, DesignResume):
            return control.resume(request)
        if isinstance(request, DesignFinish):
            return control.finish(request)
        if isinstance(request, CandidateSave):
            return control.candidate(request)
        if name == "design.cancel" and isinstance(request, DesignAction):
            return control.cancel(request)
        if isinstance(request, DesignRef):
            return control.status(request.run_id)
        raise WorkbenchError("UNKNOWN_TOOL", "未知设计工具。")

    def _bounded_call(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """A killed worker cannot keep running an edit after a timeout response."""
        body = {
            "settings": self.workbench.settings.json_dict(),
            "name": name,
            "arguments": arguments,
        }
        creationflags = 0
        if sys.platform == "win32":
            creationflags = subprocess.CREATE_NO_WINDOW
        try:
            process = subprocess.run(
                worker_command("design_workbench.interfaces.tool_worker"),
                input=json.dumps(body).encode(),
                capture_output=True,
                timeout=self.workbench.settings.tool_timeout,
                creationflags=creationflags,
                check=False,
            )
        except subprocess.TimeoutExpired as error:
            raise WorkbenchError(
                "TOOL_TIMEOUT",
                "工具执行超时；修改可能已完成，请以相同 request_id 重试或重新读取修订。",
                name,
            ) from error
        if process.returncode != 0:
            raise WorkbenchError(
                "TOOL_WORKER_FAILED", process.stderr.decode("utf-8", "replace")[-2000:], name
            )
        value: dict[str, Any] = json.loads(process.stdout)
        if "error" in value:
            details = value["error"]
            raise WorkbenchError(
                details["code"],
                details["message"],
                details.get("location", ""),
                details.get("revision"),
            )
        return value

    def _dispatch(self, name: str, request: BaseModel) -> dict[str, Any]:
        workbench = self.workbench
        if name == "versions.list":
            return {
                "default": workbench.catalog.version,
                "items": [
                    {
                        "minecraft_version": version,
                        "data_version": Catalog(version).data_version,
                        "resources_ready": workbench.resources.active(version) is not None,
                    }
                    for version in Catalog.versions()
                ],
            }
        if isinstance(request, (SearchTool, MaterialTool)):
            workbench = (
                workbench.for_project(self.project_path(request.project))
                if request.project
                else workbench.for_version(request.minecraft_version)
            )
            if request.minecraft_version and workbench.catalog.version != request.minecraft_version:
                raise WorkbenchError("VERSION_MISMATCH", "材料查询版本与项目版本不一致。")
        if isinstance(request, SearchTool):
            result = workbench.catalog.search(
                request.query, request.offset, request.limit, request.category
            )
            for item in result["items"]:
                item["support"] = (
                    workbench.pack.support(workbench.catalog.default(item["name"]))
                    if workbench.pack
                    else {"status": "missing", "reason": "尚未配置资源"}
                )
            return result
        if isinstance(request, MaterialTool):
            state = workbench.catalog.normalize(
                BlockState.make(request.state.name, request.state.properties)
            )
            return {
                **workbench.catalog.describe(state.name),
                "state": state.as_dict(),
                "support": workbench.pack.support(state)
                if workbench.pack
                else {"status": "missing", "reason": "尚未配置资源"},
            }
        if isinstance(request, CreateTool):
            workbench = workbench.for_version(request.request.minecraft_version)
            # Keep creation receipts from before the optional version field retryable.
            encoded = request.model_dump_json(
                exclude={"request": {"minecraft_version"}}
                if request.request.minecraft_version is None
                else None
            )
            digest = hashlib.sha256(encoded.encode()).hexdigest()
            identifier = hashlib.sha256(request.request_id.encode()).hexdigest()[:32]
            path = self.project_path(identifier)
            if path.exists():
                receipt = SqliteStore(path).creation()
                if receipt is None or receipt["digest"] != digest:
                    raise WorkbenchError(
                        "REQUEST_ID_REUSED", "创建 request_id 已用于不同参数。", "request_id"
                    )
                return receipt["result"]  # type: ignore[no-any-return]
            body = request.request
            result = {
                "project_id": identifier,
                "revision": 0,
                "name": body.name,
                "bounds": body.bounds.model_dump(),
                "request_id": request.request_id,
                "minecraft_version": workbench.catalog.version,
                "data_version": workbench.catalog.data_version,
            }
            try:
                SqliteStore.create(
                    path,
                    body.name,
                    workbench.catalog.version,
                    workbench.catalog.data_version,
                    Bounds(body.bounds.low, body.bounds.high),
                    workbench.settings.database_timeout,
                    creation={"digest": digest, "result": result},
                )
            except WorkbenchError as error:
                if error.code != "PROJECT_EXISTS":
                    raise
                receipt = SqliteStore(path).creation()
                if receipt is None or receipt["digest"] != digest:
                    raise WorkbenchError(
                        "REQUEST_ID_REUSED", "创建 request_id 参数冲突。", "request_id"
                    ) from error
                return receipt["result"]  # type: ignore[no-any-return]
            return result
        if isinstance(request, TaskTool):
            return (
                self.renderer.cancel(request.task_id)
                if name == "render.cancel"
                else self.renderer.status(request.task_id)
            )
        if isinstance(request, ProjectTool):
            path = self.project_path(request.project)
            service = workbench.service(path)
            if isinstance(request, RenderTool):
                return self.renderer.submit(path, request.request)
            if isinstance(request, InspectTool):
                self.check_selector(request.selector)
                return service.inspect(request.selector, request.limit)
            if isinstance(request, EditTool):
                return service.edit(request.request, preview=name == "scene.preview_edit")
            if isinstance(request, ImportTool):
                source = Path(request.source).expanduser().resolve()
                if not source.is_file():
                    raise WorkbenchError("ASSET_NOT_FOUND", "蓝图文件不存在。", "source")
                with source.open("rb") as handle:
                    payload = handle.read(32_000_001)
                if len(payload) > 32_000_000:
                    raise WorkbenchError("IMPORT_LIMIT", "蓝图压缩文件超过 32 MB。", "source")
                return service.import_asset(payload, request.request)
            if isinstance(request, HistoryTool):
                return service.history(
                    "undo" if name == "history.undo" else "redo", request.request
                )
            if isinstance(request, ExportTool):
                target = (
                    Path(request.output).expanduser().resolve()
                    if request.output
                    else workbench.settings.data_dir
                    / "exports"
                    / f"{request.project}-r{request.expected_revision}.litematic"
                )
                digest = fingerprint("tool.export", request.model_dump(mode="json"))
                receipt_path = (
                    workbench.settings.data_dir
                    / "exports"
                    / ".receipts"
                    / request.project
                    / (hashlib.sha256(request.request_id.encode()).hexdigest() + ".json")
                )

                def publish() -> dict[str, Any]:
                    if receipt_path.is_file():
                        cached = json.loads(receipt_path.read_text(encoding="utf-8"))
                        if cached["digest"] != digest:
                            raise WorkbenchError(
                                "REQUEST_ID_REUSED", "导出 request_id 参数冲突。", "request_id"
                            )
                        payload = base64.b64decode(cached["payload"], validate=True)
                        report = cached["report"]
                    else:
                        payload, report = service.export_asset(
                            request.expected_revision, request.allow_lossy
                        )
                        atomic_output(
                            receipt_path,
                            json.dumps(
                                {
                                    "digest": digest,
                                    "payload": base64.b64encode(payload).decode(),
                                    "report": report,
                                }
                            ).encode(),
                        )
                    atomic_output(target, payload)
                    return {
                        "revision": request.expected_revision,
                        "path": str(target),
                        "bytes": len(payload),
                        "sha256": hashlib.sha256(payload).hexdigest(),
                        "report": report,
                        "request_id": request.request_id,
                    }

                return SqliteStore(path).receipt(request.request_id, digest, publish)
            return service.summary()
        items, errors = [], []
        for path in sorted(self.projects.glob("*.dwbench")):
            try:
                items.append({"project_id": path.stem, **workbench.service(path).summary()})
            except WorkbenchError as error:
                errors.append({"project_id": path.stem, "error": error.as_dict()})
        return {"items": items, "errors": errors}

    def check_selector(self, selector: Selector) -> None:
        if (
            selector.bounds
            and Bounds(selector.bounds.low, selector.bounds.high).volume
            > self.workbench.settings.max_selection_volume
        ):
            raise WorkbenchError("SELECTION_LIMIT", "选区超过空间范围预算。", "selector.bounds")
