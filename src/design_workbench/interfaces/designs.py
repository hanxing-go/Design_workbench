"""Durable control plane over the existing AI tools; no model-specific SDK."""

import hashlib
import json
import threading
import time
import uuid
from collections.abc import Callable
from contextlib import suppress
from pathlib import Path
from typing import TYPE_CHECKING, Any

from design_workbench.adapters.storage.design_runs import DesignStore
from design_workbench.application.contracts import EditRequest
from design_workbench.application.design_contracts import (
    CandidateOpen,
    CandidateSave,
    DesignAction,
    DesignCall,
    DesignCreate,
    DesignDecision,
    DesignFinish,
    DesignPropose,
    DesignResume,
    DesignUpdate,
    DesignUsage,
)
from design_workbench.application.scenes import fingerprint
from design_workbench.domain.errors import WorkbenchError

if TYPE_CHECKING:
    from design_workbench.interfaces.tools import Tools

ACTIVE = {"active", "awaiting_approval"}
READ_TOOLS = {
    "catalog.search",
    "catalog.material",
    "scene.summary",
    "scene.inspect",
    "scene.preview_edit",
    "asset.export",
}


class Designs:
    def __init__(self, tools: "Tools") -> None:
        self.tools = tools
        self.store = DesignStore(
            tools.workbench.settings.data_dir, tools.workbench.settings.database_timeout
        )
        self._stop = threading.Event()
        self._monitor: threading.Thread | None = None
        self._watch: dict[str, set[str]] = {}
        self._watch_lock = threading.RLock()

    def watch_render(self, identifier: str, task: str) -> None:
        with self._watch_lock:
            self._watch.setdefault(identifier, set()).add(task)
            if self._monitor is None:
                self._monitor = threading.Thread(
                    target=self._monitor_renders, daemon=True, name="design-render-controls"
                )
                self._monitor.start()

    def _monitor_renders(self) -> None:
        while not self._stop.wait(0.1):
            with self._watch_lock:
                pending = [
                    (identifier, task)
                    for identifier, tasks in self._watch.items()
                    for task in tasks
                ]
            for identifier, task in pending:
                try:
                    run = self.status(identifier)
                    if run["status"] not in ACTIVE:
                        self.tools.renderer.cancel(task)
                    result = self.render_status(identifier, task)
                    if result["status"] in {"succeeded", "failed", "timed_out", "cancelled"}:
                        with self._watch_lock:
                            self._watch.get(identifier, set()).discard(task)
                except (WorkbenchError, OSError) as error:
                    with self.store.edit(identifier) as run:
                        if run["status"] in ACTIVE:
                            self.stop(run, "failed")
                            run["message"] = str(error)[:2000]
                            self.event(run, "failed", run["message"])
                    with self._watch_lock:
                        self._watch.get(identifier, set()).discard(task)

    def close(self) -> None:
        self._stop.set()
        if self._monitor:
            self._monitor.join(timeout=15)

    @staticmethod
    def event(run: dict[str, Any], kind: str, message: str, **details: Any) -> None:
        run["events"].append({"at": time.time(), "kind": kind, "message": message, **details})

    @staticmethod
    def elapsed(run: dict[str, Any]) -> float:
        return float(
            run["elapsed_seconds"]
            + (max(0, time.time() - run["active_since"]) if run["active_since"] is not None else 0)
        )

    def stop(self, run: dict[str, Any], status: str) -> None:
        run["elapsed_seconds"] = self.elapsed(run)
        run["active_since"] = None
        run["status"] = status

    def limits(
        self, run: dict[str, Any], *, next_tool: bool = False, next_edit: bool = False
    ) -> str | None:
        budget, used = run["budget"], run["usage"]
        values = {
            "seconds": self.elapsed(run),
            "tokens": used["input_tokens"] + used["output_tokens"],
            "tool_calls": used["tool_calls"],
            "model_calls": used["model_calls"],
            "revisions": used["revisions"],
            "cost_usd": used["cost_usd"],
        }
        for key, value in values.items():
            reached = (
                value is not None
                and budget[key] is not None
                and (
                    value > budget[key]
                    or (
                        value == budget[key]
                        and (key == "seconds" or next_tool or (next_edit and key == "revisions"))
                    )
                )
            )
            if reached:
                if run["status"] in ACTIVE:
                    self.stop(run, "budget_exceeded")
                    self.event(run, "budget", f"{key} 已达到预算", dimension=key)
                return key
        return None

    def public(self, run: dict[str, Any]) -> dict[str, Any]:
        value = {
            key: val
            for key, val in run.items()
            if key not in {"digest", "receipts", "pending", "active_since", "events"}
        }
        value["elapsed_seconds"] = round(self.elapsed(run), 2)
        value["events"] = run["events"][-100:]
        value["pending"] = (
            {key: val for key, val in run["pending"].items() if key != "request"}
            if run["pending"]
            else None
        )
        maximum = self.tools.workbench.settings.max_tool_response_bytes
        if value["pending"]:
            preview = value["pending"]["preview"]
            while preview["changes"] and len(json.dumps(value).encode()) > maximum:
                preview["changes"] = preview["changes"][: len(preview["changes"]) // 2]
                preview["truncated"] = True
        value["usage"]["measurement"] = (
            "external_report" if value["usage"]["source"] else "not_reported"
        )
        return dict(json.loads(json.dumps(value)))

    def status(self, identifier: str) -> dict[str, Any]:
        with self.store.edit(identifier) as run:
            self.limits(run)
            result = self.public(run)
        if result["status"] == "budget_exceeded" and self.tools._renderer is not None:
            for task in result["renders"]:
                with suppress(WorkbenchError):
                    self.tools.renderer.cancel(task)
        return result

    def list(self, project: str) -> dict[str, Any]:
        return {"items": [self.status(run["run_id"]) for run in self.store.list(project)[:100]]}

    def create(self, request: DesignCreate) -> dict[str, Any]:
        identifier = hashlib.sha256(f"{request.project}:{request.request_id}".encode()).hexdigest()[
            :32
        ]
        digest = fingerprint("design.create", request.model_dump())
        existing = next(
            (item for item in self.store.list(request.project) if item["run_id"] == identifier),
            None,
        )
        if existing:
            if existing["digest"] != digest:
                raise WorkbenchError("REQUEST_ID_REUSED", "任务 request_id 已用于另一组参数。")
            return self.status(identifier)
        summary = self.tools.workbench.service(self.tools.project_path(request.project)).summary()
        if summary["revision"] != request.expected_revision:
            raise WorkbenchError(
                "REVISION_CONFLICT", "启动任务前项目已变化。", revision=summary["revision"]
            )
        if request.auto_build and summary["blocks"]:
            raise WorkbenchError("APPROVAL_REQUIRED", "已有建筑的修改必须先预演确认。")
        now = time.time()
        run = {
            "run_id": identifier,
            "project": request.project,
            "prompt": request.prompt,
            "model": request.model,
            "driver": "external",
            "auto_build": request.auto_build,
            "initial_revision": summary["revision"],
            "created_at": now,
            "active_since": now,
            "elapsed_seconds": 0,
            "stage": "planning",
            "status": "active",
            "message": "等待外部 AI 接入任务",
            "budget": request.budget.model_dump(),
            "usage": {
                "input_tokens": 0,
                "cached_input_tokens": 0,
                "output_tokens": 0,
                "model_calls": 0,
                "cost_usd": None,
                "source": "",
                "tool_calls": 0,
                "revisions": 0,
            },
            "pending": None,
            "candidates": [],
            "renders": [],
            "events": [],
            "receipts": {},
        }
        self.event(run, "created", "设计任务已创建", revision=summary["revision"])
        return self.public(self.store.create(identifier, digest, run))

    def action(
        self,
        request: DesignAction,
        kind: str,
        perform: Callable[[dict[str, Any]], dict[str, Any]],
        *,
        gated: bool = True,
        count: bool = False,
    ) -> dict[str, Any]:
        digest = fingerprint(kind, request.model_dump())
        with self.store.edit(request.run_id) as run:
            key = request.request_id
            receipt = run["receipts"].get(key)
            if receipt:
                if receipt["digest"] != digest:
                    raise WorkbenchError("REQUEST_ID_REUSED", "任务 request_id 已用于另一项操作。")
                return dict(receipt["result"])
            self.limits(run, next_tool=count)
            if gated and run["status"] != "active":
                return {
                    "error": {
                        "code": "DESIGN_STOPPED",
                        "message": f"任务状态为 {run['status']}，请先确认、拒绝或继续任务。",
                    }
                }
            if count:
                run["usage"]["tool_calls"] += 1
            try:
                result = perform(run)
            except (WorkbenchError, OSError, ValueError) as failure:
                error = (
                    failure
                    if isinstance(failure, WorkbenchError)
                    else WorkbenchError("DESIGN_FAILED", str(failure)[:2000])
                )
                self.stop(run, "failed")
                run["message"] = error.message
                self.event(run, "failed", error.message, code=error.code)
                result = {"error": error.as_dict()}
            result = dict(json.loads(json.dumps(result)))
            run["receipts"][key] = {"digest": digest, "result": result}
            return result

    def update(self, request: DesignUpdate) -> dict[str, Any]:
        def perform(run: dict[str, Any]) -> dict[str, Any]:
            run.update(stage=request.stage, message=request.message)
            if request.stage in {"reviewing", "revising", "exporting"}:
                run["auto_build"] = False
            self.event(run, "stage", request.message, stage=request.stage)
            return self.public(run)

        return self.action(request, "update", perform)

    def usage(self, request: DesignUsage) -> dict[str, Any]:
        def perform(run: dict[str, Any]) -> dict[str, Any]:
            values = request.model_dump(exclude={"run_id", "request_id", "schema_version"})
            if request.cached_input_tokens > request.input_tokens:
                raise WorkbenchError("INVALID_USAGE", "缓存输入已经包含在输入 tokens 中。")
            for key in (
                "input_tokens",
                "cached_input_tokens",
                "output_tokens",
                "model_calls",
                "cost_usd",
            ):
                previous, current = run["usage"][key], values[key]
                if previous is not None and current is not None and current < previous:
                    raise WorkbenchError("INVALID_USAGE", "累计用量不能降低。", key)
            if values["cost_usd"] is None:
                values["cost_usd"] = run["usage"]["cost_usd"]
            run["usage"].update(values)
            self.event(run, "usage", "已记录外部模型累计用量", source=request.source)
            self.limits(run)
            return self.public(run)

        return self.action(request, "usage", perform, gated=False)

    def propose(self, request: DesignPropose) -> dict[str, Any]:
        def perform(run: dict[str, Any]) -> dict[str, Any]:
            return self._propose(run, request.request, request.explanation)

        return self.action(request, "propose", perform, count=True)

    def _propose(
        self, run: dict[str, Any], request: EditRequest, explanation: str
    ) -> dict[str, Any]:
        result = self.tools.call(
            "scene.preview_edit",
            {"project": run["project"], "request": request.model_dump(mode="json")},
        )
        proposal = {
            "proposal_id": uuid.uuid4().hex,
            "explanation": explanation,
            "expected_revision": request.expected_revision,
            "request": request.model_dump(mode="json"),
            "preview": result,
        }
        run["pending"] = proposal
        self.stop(run, "awaiting_approval")
        run["message"] = "修改已预演，等待你确认"
        self.event(
            run,
            "proposal",
            explanation,
            changed=result["changed"],
            proposal_id=proposal["proposal_id"],
        )
        return self.public(run)

    def decide(self, request: DesignDecision, approve: bool) -> dict[str, Any]:
        def perform(run: dict[str, Any]) -> dict[str, Any]:
            pending = run["pending"]
            if (
                run["status"] != "awaiting_approval"
                or not pending
                or pending["proposal_id"] != request.proposal_id
            ):
                raise WorkbenchError("PROPOSAL_EXPIRED", "预演已失效，请重新观察并预演。")
            if approve and self.limits(run, next_edit=True):
                return {
                    "error": {
                        "code": "DESIGN_BUDGET",
                        "message": "预算已用完，请提高预算后重新预演。",
                    }
                }
            if approve:
                result = self.tools.workbench.service(self.tools.project_path(run["project"])).edit(
                    EditRequest.model_validate(pending["request"])
                )
                run["usage"]["revisions"] += 1
                self.event(
                    run,
                    "approved",
                    "已确认并应用修改",
                    revision=result["revision"],
                    changed=result["changed"],
                )
            else:
                self.event(run, "rejected", "已拒绝修改，场景保持原样")
            run.update(
                pending=None,
                status="active",
                active_since=time.time(),
                message="修改已应用" if approve else "修改已拒绝，请重新设计",
            )
            return self.public(run)

        return self.action(request, "approve" if approve else "reject", perform, gated=False)

    def call(self, request: DesignCall) -> dict[str, Any]:
        if request.tool not in READ_TOOLS | {"scene.commit_edit", "render.views"}:
            raise WorkbenchError(
                "DESIGN_TOOL_NOT_ALLOWED", "此工具不能在受控设计任务中调用。", "tool"
            )
        arguments = dict(request.arguments)
        current = self.status(request.run_id)
        if "project" in arguments and arguments["project"] != current["project"]:
            raise WorkbenchError("DESIGN_PROJECT_MISMATCH", "不能通过任务修改其他项目。")
        from pydantic import ValidationError

        from design_workbench.interfaces.tools import TOOL_CONTRACTS

        if not request.tool.startswith("catalog."):
            arguments["project"] = current["project"]
        try:
            parsed = TOOL_CONTRACTS[request.tool][0].model_validate(arguments)
        except ValidationError as error:
            raise WorkbenchError("INVALID_REQUEST", error.errors()[0]["msg"]) from error
        arguments = parsed.model_dump(mode="json")
        render_wait = False
        if request.tool == "render.views":
            arguments["request"] = {**arguments["request"]}
            render_wait = arguments["request"].get("wait", True)
            arguments["request"]["wait"] = False

        def perform(run: dict[str, Any]) -> dict[str, Any]:
            arguments["project"] = (
                run["project"]
                if not request.tool.startswith("catalog.")
                else arguments.get("project")
            )
            if request.tool.startswith("catalog."):
                arguments.pop("project", None)
            if request.tool == "scene.commit_edit":
                scene = self.tools.workbench.service(
                    self.tools.project_path(run["project"])
                ).summary()
                expected = run["initial_revision"] + run["usage"]["revisions"]
                if scene["revision"] != expected:
                    run["auto_build"] = False
                if not run["auto_build"] or run["stage"] != "building":
                    return self._propose(
                        run, EditRequest.model_validate(arguments["request"]), "AI 提议修改当前建筑"
                    )
                if self.limits(run, next_edit=True):
                    return {"error": {"code": "DESIGN_BUDGET", "message": "修改批次预算已用完。"}}
                result = self.tools.workbench.service(self.tools.project_path(run["project"])).edit(
                    EditRequest.model_validate(arguments["request"])
                )
            else:
                result = self.tools.call(request.tool, arguments)
            if request.tool == "scene.commit_edit":
                run["usage"]["revisions"] += 1
            if request.tool == "render.views":
                run["renders"].append(result["task_id"])
            self.event(run, "tool", request.tool, revision=result.get("revision"))
            return result

        result = self.action(request, "call", perform, count=True)
        if request.tool == "render.views" and "task_id" in result:
            self.watch_render(request.run_id, result["task_id"])
        if request.tool == "render.views" and "task_id" in result and render_wait:
            result = self.render_status(request.run_id, result["task_id"])
            while result["status"] not in {"succeeded", "failed", "timed_out", "cancelled"}:
                run = self.status(request.run_id)
                if run["status"] not in ACTIVE:
                    result = self.tools.renderer.cancel(result["task_id"])
                    break
                time.sleep(0.1)
                result = self.render_status(request.run_id, result["task_id"])
            return self.capture_result(request.run_id, result)
        return result

    def capture_result(self, identifier: str, result: dict[str, Any]) -> dict[str, Any]:
        if result["status"] in {"queued", "preparing", "running", "capturing", "rendering"}:
            return result
        if result["status"] != "succeeded":
            with self.store.edit(identifier) as run:
                if run["status"] in ACTIVE:
                    self.stop(run, "failed")
                    run["message"] = "截图失败，可继续任务后重新截图"
                    self.event(run, "failed", run["message"], render_status=result["status"])
            return result
        directory = self.store.directory / identifier / result["task_id"]
        directory.mkdir(parents=True, exist_ok=True)
        from design_workbench.interfaces.tools import atomic_output

        for index, item in enumerate(result.get("images", [])):
            path = directory / f"{index}.png"
            atomic_output(path, Path(item["path"]).read_bytes())
            item.update(
                path=str(path),
                url=f"/api/design-runs/{identifier}/images/{result['task_id']}/{index}.png",
            )
        with self.store.edit(identifier) as run:
            entry = {
                "task_id": result["task_id"],
                "revision": result["revision"],
                "images": result.get("images", []),
                "resource_hash": result.get("resource_hash"),
                "snapshot_hash": result.get("snapshot_hash"),
            }
            if not any(item["task_id"] == result["task_id"] for item in run.get("screenshots", [])):
                run.setdefault("screenshots", []).append(entry)
        return result

    def render_status(self, identifier: str, task: str) -> dict[str, Any]:
        run = self.status(identifier)
        if task not in run["renders"]:
            raise WorkbenchError("RENDER_NOT_FOUND", "截图不属于此设计任务。")
        saved = next((item for item in run.get("screenshots", []) if item["task_id"] == task), None)
        if saved:
            return {"status": "succeeded", **saved}
        try:
            return self.capture_result(identifier, self.tools.renderer.status(task))
        except WorkbenchError as error:
            if error.code == "RENDER_NOT_FOUND":
                with self.store.edit(identifier) as record:
                    if record["status"] in ACTIVE:
                        self.stop(record, "interrupted")
                        record["message"] = "服务已重启，未完成的截图需重试"
            raise

    def cancel(self, request: DesignAction) -> dict[str, Any]:
        def perform(run: dict[str, Any]) -> dict[str, Any]:
            if run["status"] == "succeeded":
                raise WorkbenchError("DESIGN_FINISHED", "已完成的任务无需取消。")
            self.stop(run, "cancelled")
            run.update(pending=None, message="任务已取消；已保存修改和候选稿仍保留")
            self.event(run, "cancelled", run["message"])
            return self.public(run)

        result = self.action(request, "cancel", perform, gated=False)
        for task in result.get("renders", []):
            with suppress(WorkbenchError):
                self.tools.renderer.cancel(task)
        return result

    def resume(self, request: DesignResume) -> dict[str, Any]:
        def perform(run: dict[str, Any]) -> dict[str, Any]:
            if run["status"] not in {"failed", "cancelled", "budget_exceeded", "interrupted"}:
                raise WorkbenchError("DESIGN_NOT_RESUMABLE", "此任务当前不需要恢复。")
            if any(
                other["run_id"] != run["run_id"] and other["status"] in ACTIVE
                for other in self.store.list(run["project"])
            ):
                raise WorkbenchError("DESIGN_BUSY", "此项目另有进行中的任务，请先取消或完成。")
            if request.budget:
                replacement = request.budget.model_dump()
                for key, value in replacement.items():
                    previous = run["budget"][key]
                    if previous is not None and value is not None and value < previous:
                        raise WorkbenchError("INVALID_BUDGET", "继续任务只能维持或增加预算。", key)
                run["budget"] = replacement
            if self.limits(run):
                return {
                    "error": {
                        "code": "DESIGN_BUDGET",
                        "message": "剩余预算不足，请明确增加预算后继续。",
                    }
                }
            run.update(
                status="active",
                active_since=time.time(),
                pending=None,
                message="任务已恢复，请读取当前修订后继续",
            )
            self.event(run, "resumed", run["message"])
            return self.public(run)

        return self.action(request, "resume", perform, gated=False)

    def finish(self, request: DesignFinish) -> dict[str, Any]:
        def perform(run: dict[str, Any]) -> dict[str, Any]:
            if request.outcome == "succeeded" and not run["candidates"]:
                raise WorkbenchError("CANDIDATE_REQUIRED", "完成前请保存至少一份独立候选稿。")
            self.stop(run, request.outcome)
            run["message"] = request.message
            self.event(run, request.outcome, request.message)
            return self.public(run)

        return self.action(request, "finish", perform)

    def candidate(self, request: CandidateSave) -> dict[str, Any]:
        def perform(run: dict[str, Any]) -> dict[str, Any]:
            if len(run["candidates"]) >= 64:
                raise WorkbenchError("CANDIDATE_LIMIT", "每个任务最多保留 64 份候选稿。")
            identifier = hashlib.sha256(
                f"{request.run_id}:{request.request_id}".encode()
            ).hexdigest()[:32]
            sha256, size = self.store.snapshot(
                self.tools.project_path(run["project"]), identifier, request.expected_revision
            )
            value = {
                "candidate_id": identifier,
                "name": request.name,
                "revision": request.expected_revision,
                "feedback": request.feedback,
                "created_at": time.time(),
                "sha256": sha256,
                "bytes": size,
                "prompt": run["prompt"],
                "model": run["model"],
                "usage": dict(run["usage"]),
                "screenshots": [
                    item
                    for item in run.get("screenshots", [])
                    if item["revision"] == request.expected_revision
                ],
            }
            run["candidates"].append(value)
            self.event(
                run,
                "candidate",
                f"已保存候选稿：{request.name}",
                revision=request.expected_revision,
            )
            return value

        return self.action(request, "candidate", perform, gated=False)

    def find_candidate(self, identifier: str, candidate: str) -> dict[str, Any]:
        item = next(
            (
                item
                for item in self.status(identifier)["candidates"]
                if item["candidate_id"] == candidate
            ),
            None,
        )
        if item is None:
            raise WorkbenchError("CANDIDATE_NOT_FOUND", "候选稿不存在。")
        path = self.store.candidate_path(candidate)
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != item["sha256"]:
            raise WorkbenchError("CANDIDATE_CORRUPT", "候选稿快照缺失或校验失败。")
        return dict(item)

    def open_candidate(
        self, identifier: str, candidate: str, request: CandidateOpen
    ) -> dict[str, Any]:
        item = self.find_candidate(identifier, candidate)
        project = self.store.open_candidate(
            candidate, request.request_id, self.tools.projects, item["name"], item["sha256"]
        )
        origin = self.status(identifier)
        prompt = (
            f"基于候选稿「{item['name']}」继续修改。\n原始需求：{item.get('prompt', origin['prompt'])}\n用户反馈：{item['feedback']}"
        )[:16000]
        run = self.create(
            DesignCreate(
                project=project,
                request_id=f"candidate-{candidate}",
                expected_revision=item["revision"],
                prompt=prompt,
                model=item.get("model", origin["model"]),
                budget=origin["budget"],
            )
        )
        return {"project_id": project, "candidate": item, "run_id": run["run_id"]}
