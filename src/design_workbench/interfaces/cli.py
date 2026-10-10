import json
import uuid
from collections.abc import Callable
from functools import wraps
from pathlib import Path
from typing import Annotated, Any

import typer
from pydantic import ValidationError

from design_workbench import __version__
from design_workbench.adapters.storage.sqlite import SqliteStore
from design_workbench.application.contracts import EditRequest, HistoryRequest
from design_workbench.bootstrap import Workbench
from design_workbench.config import Settings
from design_workbench.domain.errors import WorkbenchError
from design_workbench.domain.models import Bounds

app = typer.Typer(no_args_is_help=True, help="Minecraft 建筑设计工作台。")
resources = typer.Typer(no_args_is_help=True, help="版本素材管理")
app.add_typer(resources, name="resources")


def emit(value: Any) -> None:
    typer.echo(json.dumps(value, ensure_ascii=False, indent=2, default=str))


def handled(function: Callable[..., Any]) -> Callable[..., Any]:
    @wraps(function)
    def wrapped(*args: Any, **kwargs: Any) -> Any:
        try:
            return function(*args, **kwargs)
        except WorkbenchError as error:
            emit({"error": error.as_dict()})
            raise typer.Exit(1) from error
        except (ValidationError, ValueError, OSError) as error:
            emit({"error": {"code": "INVALID_INPUT", "message": str(error)}})
            raise typer.Exit(1) from error

    return wrapped


@app.callback()
def main(version: bool = typer.Option(False, "--version", help="显示程序版本")) -> None:
    if version:
        typer.echo(__version__)
        raise typer.Exit()


@app.command()
@handled
def info(config: Annotated[Path | None, typer.Option(help="配置 TOML 路径")] = None) -> None:
    """显示版本及有效配置。"""
    settings = Settings.load(config)
    typer.echo(
        json.dumps(
            {"version": __version__, "settings": settings.json_dict()}, ensure_ascii=False, indent=2
        )
    )


@resources.command("setup")
@handled
def setup_resources(
    config: Annotated[Path | None, typer.Option()] = None,
    jar: Annotated[Path | None, typer.Option(help="已有官方客户端 jar")] = None,
    language: Annotated[Path | None, typer.Option(help="zh_cn.json")] = None,
) -> None:
    """获取或导入版本一致的官方客户端静态素材。"""
    from design_workbench.adapters.resources.acquire import fetch_official

    settings = Settings.load(config)
    workbench = Workbench(settings)
    if jar is None:
        jar, provenance = fetch_official(
            settings.minecraft_version, settings.cache_dir / "downloads"
        )
        language = Path(provenance["language_path"])
    else:
        provenance = {"source": "user-provided-client", "filename": jar.name}
    pack = workbench.resources.import_jar(jar, settings.minecraft_version, language, provenance)
    emit(pack.manifest)


@resources.command("audit")
@handled
def audit_resources(output: Path, config: Annotated[Path | None, typer.Option()] = None) -> None:
    """逐状态检查资源支持范围并写出报告。"""
    from collections import Counter

    workbench = Workbench(Settings.load(config))
    if workbench.pack is None:
        raise WorkbenchError("RESOURCES_NOT_READY", "先执行 resources setup。")
    total: Counter[str] = Counter()
    blocks = {}
    for name in workbench.catalog.blocks:
        counts: Counter[str] = Counter()
        for state in workbench.catalog.states(name):
            counts[workbench.pack.support(state)["status"]] += 1
        total.update(counts)
        blocks[name] = dict(counts)
    report = {
        "minecraft_version": workbench.catalog.version,
        "blocks": len(blocks),
        "states": sum(total.values()),
        "status_counts": dict(total),
        "by_block": blocks,
        "resource_manifest": workbench.pack.manifest,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    emit({key: value for key, value in report.items() if key != "by_block"})


@app.command("create")
@handled
def create_project(
    project: Path,
    name: Annotated[str, typer.Option()] = "新建筑",
    config: Annotated[Path | None, typer.Option()] = None,
) -> None:
    workbench = Workbench(Settings.load(config))
    SqliteStore.create(
        project,
        name,
        workbench.catalog.version,
        workbench.catalog.data_version,
        Bounds((-512, -64, -512), (511, 511, 511)),
    )
    emit(workbench.service(project).summary())


@app.command("summary")
@handled
def summary(project: Path, config: Annotated[Path | None, typer.Option()] = None) -> None:
    emit(Workbench(Settings.load(config)).service(project).summary())


@app.command("edit")
@handled
def edit(
    project: Path,
    request: Path,
    preview: Annotated[bool, typer.Option()] = False,
    config: Annotated[Path | None, typer.Option()] = None,
) -> None:
    emit(
        Workbench(Settings.load(config))
        .service(project)
        .edit(EditRequest.model_validate_json(request.read_text(encoding="utf-8")), preview)
    )


@app.command("history")
@handled
def history(
    project: Path,
    direction: str,
    revision: Annotated[int, typer.Option()],
    request_id: Annotated[str | None, typer.Option()] = None,
    config: Annotated[Path | None, typer.Option()] = None,
) -> None:
    emit(
        Workbench(Settings.load(config))
        .service(project)
        .history(
            direction,
            HistoryRequest(expected_revision=revision, request_id=request_id or uuid.uuid4().hex),
        )
    )


@app.command("import")
@handled
def import_asset(
    project: Path,
    source: Path,
    revision: Annotated[int, typer.Option()],
    config: Annotated[Path | None, typer.Option()] = None,
) -> None:
    emit(
        Workbench(Settings.load(config))
        .service(project)
        .import_asset(
            source.read_bytes(),
            HistoryRequest(expected_revision=revision, request_id=uuid.uuid4().hex),
        )
    )


@app.command("export")
@handled
def export_asset(
    project: Path,
    output: Path,
    revision: Annotated[int, typer.Option()],
    config: Annotated[Path | None, typer.Option()] = None,
) -> None:
    if output.exists():
        raise WorkbenchError("FILE_EXISTS", "导出目标已存在。")
    payload, report = Workbench(Settings.load(config)).service(project).export_asset(revision)
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_name(output.name + f".{uuid.uuid4().hex}.tmp")
    try:
        temporary.write_bytes(payload)
        temporary.rename(output)
    finally:
        temporary.unlink(missing_ok=True)
    emit(report)


@app.command("serve")
@handled
def serve(
    port: Annotated[int, typer.Option(min=1024, max=65535)] = 8765,
    config: Annotated[Path | None, typer.Option()] = None,
) -> None:
    """打开本地三维工作台服务。"""
    import uvicorn

    from design_workbench.interfaces.http import create_app

    uvicorn.run(create_app(Settings.load(config)), host="127.0.0.1", port=port)


@app.command("tools")
@handled
def describe_tools(config: Annotated[Path | None, typer.Option()] = None) -> None:
    """列出版本化 AI 工具和 JSON Schema。"""
    from design_workbench.interfaces.tools import Tools

    tools = Tools(Workbench(Settings.load(config)))
    try:
        emit({"schema_version": 1, "tools": tools.descriptions()})
    finally:
        tools.close()


@app.command("tool")
@handled
def call_tool(
    name: str,
    request: Path,
    config: Annotated[Path | None, typer.Option()] = None,
    server: Annotated[
        str | None, typer.Option(help="调用正在运行的 HTTP 服务，支持异步截图任务")
    ] = None,
    output_dir: Annotated[
        Path | None, typer.Option(help="把实际 PNG 和 manifest.json 保存到此目录")
    ] = None,
) -> None:
    """调用 AI 工具；请求是 JSON 文件，结果为 JSON。截图需指定 --output-dir。"""
    import urllib.error
    import urllib.request

    from design_workbench.interfaces.tools import Tools, atomic_output

    if request.stat().st_size > 4_000_000:
        raise WorkbenchError("TOOL_INPUT_LIMIT", "工具请求超过 4 MB。", "request")
    body = json.loads(request.read_text(encoding="utf-8"))
    tools = Tools(Workbench(Settings.load(config)))
    try:
        if server:
            remote = urllib.request.Request(
                f"{server.rstrip('/')}/api/tools/v1/{name}",
                data=json.dumps(body).encode(),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            try:
                with urllib.request.urlopen(remote, timeout=125) as response:
                    result = json.load(response)
            except urllib.error.HTTPError as error:
                details = json.load(error)["error"]
                raise WorkbenchError(
                    details["code"],
                    details["message"],
                    details.get("location", ""),
                    details.get("revision"),
                ) from error
        else:
            if name == "render.views" or (
                name == "design.call" and body.get("tool") == "render.views"
            ):
                render_body = body if name == "render.views" else body.get("arguments", {})
                if not render_body.get("request", {}).get("wait", True):
                    raise WorkbenchError(
                        "ASYNC_RENDER_REQUIRES_SERVER", "异步截图请使用 --server。", "request.wait"
                    )
                if output_dir is None:
                    raise WorkbenchError(
                        "OUTPUT_REQUIRED",
                        "本地截图必须指定 --output-dir，以保留结果。",
                        "output_dir",
                    )
            result = tools.call(name, body)
        if result.get("images") and output_dir:
            output_dir = output_dir.expanduser().resolve()
            for image in result["images"]:
                if server:
                    with urllib.request.urlopen(
                        server.rstrip("/") + image["url"], timeout=30
                    ) as response:
                        payload = response.read()
                else:
                    payload = Path(image["path"]).read_bytes()
                target = output_dir / image["file"]
                atomic_output(target, payload)
                image["path"] = str(target)
            atomic_output(
                output_dir / f"manifest-{result['task_id']}.json",
                json.dumps(result, ensure_ascii=False, indent=2).encode(),
            )
        emit(result)
        if result.get("error"):
            raise typer.Exit(1)
    finally:
        tools.close()


@app.command("catalog")
@handled
def search_catalog(
    query: str = "",
    limit: Annotated[int, typer.Option()] = 24,
    config: Annotated[Path | None, typer.Option()] = None,
) -> None:
    """按中英文查询材料。"""
    from design_workbench.interfaces.tools import Tools

    tools = Tools(Workbench(Settings.load(config)))
    try:
        emit(tools.call("catalog.search", {"query": query, "limit": limit}))
    finally:
        tools.close()


@app.command("inspect")
@handled
def inspect_scene(
    project: Path,
    selector: Annotated[Path | None, typer.Option(help="JSON 选区；省略时查看整个场景")] = None,
    limit: Annotated[int, typer.Option()] = 128,
    config: Annotated[Path | None, typer.Option()] = None,
) -> None:
    """按坐标、材料、分组或区域检查场景。"""
    from design_workbench.application.contracts import Selector
    from design_workbench.interfaces.tools import Tools

    tools = Tools(Workbench(Settings.load(config)))
    try:
        selection = (
            Selector.model_validate_json(selector.read_text(encoding="utf-8"))
            if selector
            else Selector()
        )
        tools.check_selector(selection)
        emit(tools.workbench.service(project).inspect(selection, limit))
    finally:
        tools.close()


@app.command("mcp")
@handled
def serve_mcp(config: Annotated[Path | None, typer.Option()] = None) -> None:
    """运行 stdio MCP 服务（安装 ai extra）。"""
    import asyncio

    try:
        from design_workbench.interfaces.mcp import run_server
    except ModuleNotFoundError as error:
        raise WorkbenchError(
            "AI_DEPENDENCY_MISSING", "请安装 minecraft-design-workbench[ai]。"
        ) from error
    asyncio.run(run_server(Settings.load(config)))


if __name__ == "__main__":
    app()
