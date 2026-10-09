import hashlib
import json
import logging
import time
from typing import Any

from design_workbench.domain.editing import Editor, selected
from design_workbench.domain.errors import WorkbenchError
from design_workbench.domain.models import Scene

from .contracts import EditRequest, HistoryRequest, RenameRequest, Selector
from .ports import FormatAdapter, SceneRepository

LOGGER = logging.getLogger("design_workbench.application")


def fingerprint(kind: str, body: dict[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps({"kind": kind, "body": body}, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


class SceneService:
    def __init__(
        self, repository: SceneRepository, editor: Editor, formats: FormatAdapter | None = None
    ) -> None:
        self.repository = repository
        self.editor = editor
        self.formats = formats

    def summary(self) -> dict[str, Any]:
        return {**self.repository.load().summary(), **self.repository.history_info()}

    def rename(self, request: RenameRequest) -> dict[str, Any]:
        digest = fingerprint("rename", request.model_dump())
        replay = self.repository.replay(request.request_id, digest)
        if replay is not None:
            return replay
        scene = self.repository.load()
        scene.name = request.name
        return self.repository.commit(
            scene, [], request.expected_revision, request.request_id, digest
        )

    def inspect(self, selector: Selector, limit: int = 128) -> dict[str, Any]:
        scene = self.repository.load()
        chosen = selected(scene.cells, selector.model_dump(exclude_none=True))
        if not 1 <= limit <= 2048:
            raise WorkbenchError("INVALID_LIMIT", "查看上限为 1..2048。")
        return {
            "revision": scene.revision,
            "total": len(chosen),
            "truncated": len(chosen) > limit,
            "blocks": [
                {"position": point, **cell.as_dict()}
                for point, cell in list(chosen.items())[:limit]
            ],
        }

    def edit(self, request: EditRequest, preview: bool = False) -> dict[str, Any]:
        started = time.perf_counter()
        body = request.model_dump(mode="json", exclude_none=True, by_alias=True)
        # Preserve the v0.1.0 request digest when the new optional behavior is off.
        for operation in body["operations"]:
            if operation.get("complete_beds") is False:
                operation.pop("complete_beds")
        digest = fingerprint("edit", body)
        if not preview:
            result = self.repository.replay(request.request_id, digest)
            if result is not None:
                return result
        scene = self.repository.load()
        if scene.revision != request.expected_revision:
            raise WorkbenchError(
                "REVISION_CONFLICT", "场景已被修改，请重新读取。", revision=scene.revision
            )
        plan = self.editor.plan(scene, body["operations"])
        if preview:
            return {
                "revision": scene.revision,
                "changed": len(plan.changes),
                "touched": plan.touched,
                "truncated": len(plan.changes) > 10_000,
                "changes": [
                    {
                        "position": point,
                        "before": old.as_dict() if old else None,
                        "after": new.as_dict() if new else None,
                    }
                    for point, old, new in plan.changes[:10_000]
                ],
            }
        scene.cells = plan.cells
        result = self.repository.commit(
            scene, plan.changes, request.expected_revision, request.request_id, digest
        )
        LOGGER.info(
            "scene.edit",
            extra={
                "request_id": request.request_id,
                "revision": result["revision"],
                "elapsed_ms": round((time.perf_counter() - started) * 1000, 2),
            },
        )
        return result

    def history(self, direction: str, request: HistoryRequest) -> dict[str, Any]:
        if direction not in {"undo", "redo"}:
            raise WorkbenchError("INVALID_HISTORY", "历史操作必须为 undo/redo。")
        return self.repository.history(
            direction,
            request.expected_revision,
            request.request_id,
            fingerprint(direction, request.model_dump()),
        )

    def import_asset(self, payload: bytes, request: HistoryRequest) -> dict[str, Any]:
        if self.formats is None:
            raise WorkbenchError("FORMAT_UNAVAILABLE", "蓝图适配器未配置。")
        body = {**request.model_dump(), "sha256": hashlib.sha256(payload).hexdigest()}
        digest = fingerprint("import", body)
        replay = self.repository.replay(request.request_id, digest)
        if replay is not None:
            _, replay_report = self.formats.read(payload)
            return {**replay, "import_report": replay_report}
        before = self.repository.load()
        if before.revision != request.expected_revision:
            raise WorkbenchError(
                "REVISION_CONFLICT", "导入前场景已被修改。", revision=before.revision
            )
        imported, report = self.formats.read(payload)
        if imported.minecraft_version != before.minecraft_version:
            raise WorkbenchError(
                "VERSION_MISMATCH", "蓝图游戏版本与项目不同；请使用对应版本的项目。"
            )
        if len(imported.cells) > self.editor.limits.max_blocks or any(
            not before.bounds.contains(point) for point in imported.cells
        ):
            raise WorkbenchError("IMPORT_LIMIT", "蓝图超过工作区边界或方块预算。")
        for cell in imported.cells.values():
            self.editor.registry.normalize(cell.state)
        imported.id, imported.bounds = before.id, before.bounds
        changes = [
            (point, before.cells.get(point), imported.cells.get(point))
            for point in sorted(before.cells.keys() | imported.cells.keys())
            if before.cells.get(point) != imported.cells.get(point)
        ]
        result = self.repository.commit(
            imported, changes, request.expected_revision, request.request_id, digest, payload
        )
        return {**result, "import_report": report}

    def export_asset(
        self, expected_revision: int, allow_lossy: bool = False
    ) -> tuple[bytes, dict[str, Any]]:
        if self.formats is None:
            raise WorkbenchError("FORMAT_UNAVAILABLE", "蓝图适配器未配置。")
        scene: Scene = self.repository.load()
        if expected_revision != scene.revision:
            raise WorkbenchError(
                "REVISION_CONFLICT", "导出前场景已被修改。", revision=scene.revision
            )
        return self.formats.write(scene, self.repository.attachment(), allow_lossy)
