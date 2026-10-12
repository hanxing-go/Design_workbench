import json
import logging
import re
import time
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from threading import Lock
from typing import Annotated, Any

from fastapi import FastAPI, File, Form, Request, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles

from design_workbench.adapters.formats.litematic import Litematic
from design_workbench.adapters.rendering.cache import RenderCache
from design_workbench.adapters.resources.acquire import fetch_official
from design_workbench.adapters.resources.catalog import Catalog
from design_workbench.adapters.storage.sqlite import SqliteStore
from design_workbench.application.contracts import (
    CreateRequest,
    EditRequest,
    ExportRequest,
    HistoryRequest,
    RenameRequest,
    Selector,
    VersionRequest,
)
from design_workbench.application.design_contracts import (
    CandidateOpen,
    CandidateSave,
    DesignAction,
    DesignCreate,
    DesignDecision,
    DesignFinish,
    DesignResume,
)
from design_workbench.application.render_contracts import RenderRequest
from design_workbench.bootstrap import Workbench
from design_workbench.config import Settings
from design_workbench.domain.errors import WorkbenchError
from design_workbench.domain.models import Bounds
from design_workbench.domain.validation import inspect_consistency
from design_workbench.interfaces.tools import Tools

LOGGER = logging.getLogger("design_workbench.http")


def create_app(settings: Settings) -> FastAPI:
    workbench = Workbench(settings)
    render_cache = RenderCache()
    tools = Tools(workbench)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        try:
            yield
        finally:
            render_cache.close()
            tools.close()

    app = FastAPI(title="Design Workbench", version="0.1.0", lifespan=lifespan)
    app.state.workbench = workbench
    app.state.render_cache = render_cache
    app.state.tools = tools
    projects = settings.data_dir / "projects"
    projects.mkdir(parents=True, exist_ok=True)
    resource_lock = Lock()

    def project_path(identifier: str) -> Path:
        if not re.fullmatch(r"[a-zA-Z0-9_-]{1,80}", identifier):
            raise WorkbenchError("INVALID_PROJECT_ID", "项目标识非法。")
        return projects / f"{identifier}.dwbench"

    def context(project: str | None = None, minecraft_version: str | None = None) -> Workbench:
        selected = (
            workbench.for_project(project_path(project))
            if project
            else workbench.for_version(minecraft_version)
        )
        if minecraft_version and selected.catalog.version != minecraft_version:
            raise WorkbenchError("VERSION_MISMATCH", "请求版本与项目版本不一致。")
        return selected

    @app.middleware("http")
    async def request_log(request: Request, call_next: Any) -> Response:
        request_id = request.headers.get("x-request-id", uuid.uuid4().hex)[:128]
        request.state.request_id = request_id
        started = time.perf_counter()
        response: Response = await call_next(request)
        response.headers["x-request-id"] = request_id
        LOGGER.info(
            "http.request",
            extra={
                "request_id": request_id,
                "elapsed_ms": round((time.perf_counter() - started) * 1000, 2),
            },
        )
        return response

    @app.exception_handler(WorkbenchError)
    async def workbench_error(request: Request, error: WorkbenchError) -> JSONResponse:
        status = (
            504
            if error.code == "TOOL_TIMEOUT"
            else 429
            if error.code == "RENDER_QUEUE_FULL"
            else 409
            if error.code
            in {
                "REVISION_CONFLICT",
                "EDIT_COLLISION",
                "REQUEST_ID_REUSED",
                "PROJECT_EXISTS",
                "DESIGN_BUSY",
            }
            else 404
            if error.code
            in {
                "PROJECT_NOT_FOUND",
                "RENDER_NOT_FOUND",
                "RENDER_IMAGE_NOT_FOUND",
                "ASSET_NOT_FOUND",
                "DESIGN_NOT_FOUND",
                "CANDIDATE_NOT_FOUND",
            }
            else 422
        )
        return JSONResponse(
            status_code=status,
            content={
                "error": {**error.as_dict(), "request_id": getattr(request.state, "request_id", "")}
            },
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, error: RequestValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": "INVALID_REQUEST",
                    "message": "请求字段不符合数据契约。",
                    "details": json.loads(error.json())
                    if hasattr(error, "json")
                    else [
                        {"location": list(item["loc"]), "message": item["msg"]}
                        for item in error.errors()
                    ],
                    "request_id": getattr(request.state, "request_id", ""),
                }
            },
        )

    @app.get("/api/info")
    def info(project: str | None = None, minecraft_version: str | None = None) -> dict[str, Any]:
        selected = context(project, minecraft_version)
        return {
            "version": "0.1.0",
            "minecraft_version": selected.catalog.version,
            "data_version": selected.catalog.data_version,
            "resources_ready": selected.pack is not None,
            "resource_manifest": selected.pack.manifest if selected.pack else None,
        }

    @app.get("/api/versions")
    def versions() -> dict[str, Any]:
        return {
            "default": settings.minecraft_version,
            "items": [
                {
                    "minecraft_version": version,
                    "data_version": Catalog(version).data_version,
                    "resources_ready": workbench.resources.active(version) is not None,
                }
                for version in Catalog.versions()
            ],
        }

    @app.post("/api/resources/setup")
    def setup_resources(request: VersionRequest) -> dict[str, Any]:
        selected = workbench.for_version(request.minecraft_version)
        with resource_lock:
            if selected.pack is None:
                try:
                    jar, provenance = fetch_official(
                        selected.catalog.version, settings.cache_dir / "downloads"
                    )
                    selected.resources.import_jar(
                        jar, selected.catalog.version, Path(provenance["language_path"]), provenance
                    )
                except OSError as error:
                    raise WorkbenchError(
                        "RESOURCE_DOWNLOAD_FAILED", f"官方素材下载失败，请重试：{error}"
                    ) from error
        return info(minecraft_version=selected.catalog.version)

    @app.post("/api/blueprints/info")
    def blueprint_info(file: Annotated[UploadFile, File()]) -> dict[str, Any]:
        document = Litematic.parse(file.file.read(32_000_001))
        catalog = Catalog.for_data_version(int(document["MinecraftDataVersion"]))
        return info(minecraft_version=catalog.version)

    @app.get("/api/catalog")
    def catalog(
        query: str = "",
        offset: int = 0,
        limit: int = 24,
        category: str = "",
        project: str | None = None,
        minecraft_version: str | None = None,
    ) -> dict[str, Any]:
        workbench = context(project, minecraft_version)
        result = workbench.catalog.search(query, offset, limit, category)
        for item in result["items"]:
            item["support"] = (
                workbench.pack.support(workbench.catalog.default(item["name"]))
                if workbench.pack
                else {"status": "missing", "reason": "尚未配置资源"}
            )
        return result

    @app.get("/api/material/{name}")
    def material(
        name: str,
        properties: str = "{}",
        project: str | None = None,
        minecraft_version: str | None = None,
    ) -> dict[str, Any]:
        workbench = context(project, minecraft_version)
        from design_workbench.domain.models import BlockState

        try:
            values = json.loads(properties)
        except json.JSONDecodeError as error:
            raise WorkbenchError("INVALID_STATE", "属性必须是 JSON 对象。") from error
        if not isinstance(values, dict) or any(
            not isinstance(key, str) or not isinstance(value, str) for key, value in values.items()
        ):
            raise WorkbenchError("INVALID_STATE", "属性键和值必须是字符串。")
        state = workbench.catalog.normalize(BlockState.make(name, values))
        if workbench.pack is None:
            raise WorkbenchError("RESOURCES_NOT_READY", "先通过 resources setup 安装资源。")
        geometry = workbench.pack.geometry(state)
        return {**geometry, **state.as_dict(), "atlas": workbench.pack.atlas}

    @app.get("/api/atlas.png")
    def atlas(project: str | None = None, minecraft_version: str | None = None) -> FileResponse:
        workbench = context(project, minecraft_version)
        if workbench.pack is None:
            raise WorkbenchError("RESOURCES_NOT_READY", "素材尚未配置。")
        return FileResponse(workbench.pack.directory / "atlas.png", media_type="image/png")

    @app.get("/api/ui/sprites/{name}.png")
    def ui_sprite(name: str) -> FileResponse:
        sprites = {
            "diamond": "item/diamond",
            "emerald": "item/emerald",
            "iron_pickaxe": "item/iron_pickaxe",
            "book": "item/book",
            "torch": "block/torch",
        }
        if name not in sprites or workbench.pack is None:
            raise WorkbenchError("ASSET_NOT_FOUND", "界面物品贴图不可用。")
        path = (
            workbench.pack.directory / "assets" / "minecraft" / "textures" / f"{sprites[name]}.png"
        )
        if not path.is_file():
            raise WorkbenchError("ASSET_NOT_FOUND", "界面物品贴图不可用。")
        return FileResponse(path, media_type="image/png", headers={"Cache-Control": "no-cache"})

    @app.get("/api/projects")
    def list_projects() -> dict[str, Any]:
        items, errors = [], []
        for path in sorted(projects.glob("*.dwbench")):
            try:
                items.append(
                    {
                        "project_id": path.stem,
                        **render_cache.summary(path, settings.database_timeout),
                    }
                )
            except WorkbenchError as error:
                errors.append({"project_id": path.stem, "error": error.as_dict()})
        return {"items": items, "errors": errors}

    @app.post("/api/projects", status_code=201)
    def create_project(request: CreateRequest) -> dict[str, Any]:
        workbench = context(minecraft_version=request.minecraft_version)
        identifier = uuid.uuid4().hex
        SqliteStore.create(
            project_path(identifier),
            request.name,
            workbench.catalog.version,
            workbench.catalog.data_version,
            Bounds(request.bounds.low, request.bounds.high),
        )
        return {
            "project_id": identifier,
            **render_cache.summary(project_path(identifier), settings.database_timeout),
        }

    @app.get("/api/projects/{identifier}")
    def summary(identifier: str) -> dict[str, Any]:
        return render_cache.summary(project_path(identifier), settings.database_timeout)

    @app.patch("/api/projects/{identifier}")
    def rename_project(identifier: str, request: RenameRequest) -> dict[str, Any]:
        return workbench.service(project_path(identifier)).rename(request)

    @app.post("/api/projects/{identifier}/inspect")
    def inspect_scene(identifier: str, selector: Selector, limit: int = 128) -> dict[str, Any]:
        return workbench.service(project_path(identifier)).inspect(selector, limit)

    @app.post("/api/projects/{identifier}/preview")
    def preview(identifier: str, request: EditRequest) -> dict[str, Any]:
        return workbench.service(project_path(identifier)).edit(request, True)

    @app.post("/api/projects/{identifier}/edit")
    def edit(identifier: str, request: EditRequest) -> dict[str, Any]:
        return workbench.service(project_path(identifier)).edit(request)

    @app.post("/api/projects/{identifier}/history/{direction}")
    def history(identifier: str, direction: str, request: HistoryRequest) -> dict[str, Any]:
        return workbench.service(project_path(identifier)).history(direction, request)

    @app.post("/api/projects/{identifier}/import")
    def import_asset(
        identifier: str,
        expected_revision: Annotated[int, Form()],
        request_id: Annotated[str, Form()],
        file: Annotated[UploadFile, File()],
    ) -> dict[str, Any]:
        payload = file.file.read(32_000_001)
        return workbench.service(project_path(identifier)).import_asset(
            payload, HistoryRequest(expected_revision=expected_revision, request_id=request_id)
        )

    @app.post("/api/projects/{identifier}/export")
    def export_asset(identifier: str, request: ExportRequest) -> Response:
        payload, report = workbench.service(project_path(identifier)).export_asset(
            request.expected_revision, request.allow_lossy
        )
        return Response(
            payload,
            media_type="application/octet-stream",
            headers={
                "Content-Disposition": f'attachment; filename="design-r{report["revision"]}.litematic"',
                "X-Export-Report": json.dumps(report, separators=(",", ":")),
            },
        )

    @app.post("/api/projects/{identifier}/render")
    def render(identifier: str, known: dict[str, str] | None = None) -> dict[str, Any]:
        workbench = context(project=identifier)
        if workbench.pack is None:
            raise WorkbenchError("RESOURCES_NOT_READY", "素材尚未配置。")
        return render_cache.render(
            project_path(identifier),
            workbench.catalog,
            workbench.pack,
            known,
            settings.database_timeout,
        )

    @app.get("/api/projects/{identifier}/consistency")
    def consistency(identifier: str) -> dict[str, object]:
        return inspect_consistency(workbench.service(project_path(identifier)).repository.load())

    @app.get("/api/tools/v1")
    def tool_descriptions() -> dict[str, Any]:
        return {"schema_version": 1, "tools": tools.descriptions()}

    @app.post("/api/tools/v1/{name}")
    def call_tool(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        return image_links(tools.call(name, arguments))

    def image_links(result: dict[str, Any]) -> dict[str, Any]:
        if "images" in result:
            result["images"] = [
                {
                    **item,
                    "url": item.get(
                        "url", f"/api/render-jobs/{result['task_id']}/images/{index}.png"
                    ),
                }
                for index, item in enumerate(result["images"])
            ]
        return result

    @app.get("/api/projects/{identifier}/design-runs")
    def design_list(identifier: str) -> dict[str, Any]:
        workbench.service(project_path(identifier)).summary()
        return tools.designs.list(identifier)

    @app.post("/api/projects/{identifier}/design-runs", status_code=201)
    def design_create(identifier: str, request: DesignCreate) -> dict[str, Any]:
        if identifier != request.project:
            raise WorkbenchError("DESIGN_PROJECT_MISMATCH", "设计任务项目不匹配。")
        return tools.designs.create(request)

    @app.get("/api/design-runs/{run_id}")
    def design_status(run_id: str) -> dict[str, Any]:
        return tools.designs.status(run_id)

    def check_run(run_id: str, body: DesignAction) -> None:
        if body.run_id != run_id:
            raise WorkbenchError("DESIGN_RUN_MISMATCH", "设计任务标识不匹配。")

    @app.post("/api/design-runs/{run_id}/cancel")
    def design_cancel(run_id: str, request: DesignAction) -> dict[str, Any]:
        check_run(run_id, request)
        return tools.designs.cancel(request)

    @app.post("/api/design-runs/{run_id}/resume")
    def design_resume(run_id: str, request: DesignResume) -> dict[str, Any]:
        check_run(run_id, request)
        return tools.designs.resume(request)

    @app.post("/api/design-runs/{run_id}/finish")
    def design_finish(run_id: str, request: DesignFinish) -> dict[str, Any]:
        check_run(run_id, request)
        return tools.designs.finish(request)

    @app.post("/api/design-runs/{run_id}/decision")
    def design_decision(run_id: str, body: dict[str, Any]) -> dict[str, Any]:
        # This user endpoint is deliberately absent from the AI tool catalog.
        approve = body.pop("approve", None)
        if not isinstance(approve, bool):
            raise WorkbenchError("INVALID_REQUEST", "approve 必须是布尔值。")
        try:
            request = DesignDecision.model_validate(body)
        except ValueError as error:
            raise WorkbenchError("INVALID_REQUEST", "确认请求格式非法。") from error
        check_run(run_id, request)
        return tools.designs.decide(request, approve)

    @app.post("/api/design-runs/{run_id}/candidates")
    def candidate_save(run_id: str, request: CandidateSave) -> dict[str, Any]:
        check_run(run_id, request)
        return tools.designs.candidate(request)

    @app.post("/api/design-runs/{run_id}/candidates/{candidate_id}/open")
    def candidate_open(run_id: str, candidate_id: str, request: CandidateOpen) -> dict[str, Any]:
        return tools.designs.open_candidate(run_id, candidate_id, request)

    @app.get("/api/design-runs/{run_id}/candidates/{candidate_id}/download")
    def candidate_download(run_id: str, candidate_id: str) -> FileResponse:
        item = tools.designs.find_candidate(run_id, candidate_id)
        return FileResponse(
            tools.designs.store.candidate_path(candidate_id),
            filename=f"{item['name']}.dwbench",
            media_type="application/octet-stream",
        )

    @app.get("/api/design-runs/{run_id}/renders/{task_id}")
    def design_render_status(run_id: str, task_id: str) -> dict[str, Any]:
        return tools.designs.render_status(run_id, task_id)

    @app.get("/api/design-runs/{run_id}/images/{task_id}/{index}.png")
    def design_image(run_id: str, task_id: str, index: int) -> FileResponse:
        run = tools.designs.status(run_id)
        capture = next(
            (item for item in run.get("screenshots", []) if item["task_id"] == task_id), None
        )
        if capture is None or index < 0 or index >= len(capture["images"]):
            raise WorkbenchError("RENDER_IMAGE_NOT_FOUND", "任务图片不存在。")
        return FileResponse(Path(capture["images"][index]["path"]), media_type="image/png")

    @app.post("/api/projects/{identifier}/views")
    def render_views(identifier: str, request: RenderRequest) -> dict[str, Any]:
        return image_links(tools.renderer.submit(project_path(identifier), request))

    @app.get("/api/render-jobs/{task_id}")
    def render_status(task_id: str) -> dict[str, Any]:
        return image_links(tools.call("render.status", {"task_id": task_id}))

    @app.post("/api/render-jobs/{task_id}/cancel")
    def render_cancel(task_id: str) -> dict[str, Any]:
        return tools.call("render.cancel", {"task_id": task_id})

    @app.get("/api/render-jobs/{task_id}/images/{index}.png")
    def render_image(task_id: str, index: int) -> FileResponse:
        return FileResponse(
            tools.renderer.image(task_id, index),
            media_type="image/png",
            headers={"Cache-Control": "no-store"},
        )

    static = Path(__file__).parents[1] / "static"
    if static.is_dir():
        app.mount("/", StaticFiles(directory=static, html=True), name="ui")
    return app
