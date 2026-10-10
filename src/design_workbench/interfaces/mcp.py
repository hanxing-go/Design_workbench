"""MCP is a thin transport over the same versioned tools as CLI and HTTP."""

import asyncio
import base64
import json
from pathlib import Path
from typing import Any

from mcp.server.lowlevel import Server
from mcp.server.stdio import stdio_server
from mcp.types import CallToolResult, ContentBlock, ImageContent, TextContent, Tool, ToolAnnotations

from design_workbench.bootstrap import Workbench
from design_workbench.config import Settings
from design_workbench.domain.errors import WorkbenchError
from design_workbench.interfaces.tools import Tools


async def run_server(settings: Settings) -> None:
    tools = Tools(Workbench(settings))
    server = Server(
        "design-workbench",
        version="1.0.0",
        instructions="Use schema_version=1. Read scene revisions before edits. On conflicts re-observe. "
        "Render actual views and inspect their images before revising a design. All mutations use atomic scene services.",
    )

    @server.list_tools()  # type: ignore[no-untyped-call, untyped-decorator]
    async def list_tools() -> list[Tool]:
        return [
            Tool(
                **description,
                annotations=ToolAnnotations(
                    readOnlyHint=description["name"]
                    in {
                        "catalog.search",
                        "catalog.material",
                        "project.list",
                        "scene.summary",
                        "scene.inspect",
                        "scene.preview_edit",
                        "render.views",
                        "render.status",
                        "design.list",
                        "design.status",
                    },
                    destructiveHint=description["name"]
                    in {
                        "scene.commit_edit",
                        "asset.import",
                        "history.undo",
                        "history.redo",
                        "design.call",
                    },
                    openWorldHint=False,
                ),
            )
            for description in tools.descriptions()
        ]

    @server.call_tool(validate_input=False)  # type: ignore[untyped-decorator]
    async def call_tool(name: str, arguments: dict[str, Any]) -> CallToolResult:
        try:
            result = await asyncio.to_thread(tools.call, name, arguments)
            content: list[ContentBlock] = [
                TextContent(type="text", text=json.dumps(result, ensure_ascii=False))
            ]
            for image in result.get("images", []):
                data = Path(image["path"]).read_bytes()
                content.append(
                    ImageContent(
                        type="image", data=base64.b64encode(data).decode(), mimeType="image/png"
                    )
                )
            return CallToolResult(
                content=content, structuredContent=result, isError=bool(result.get("error"))
            )
        except WorkbenchError as error:
            result = {"schema_version": 1, "error": error.as_dict()}
            return CallToolResult(
                content=[TextContent(type="text", text=json.dumps(result, ensure_ascii=False))],
                structuredContent=result,
                isError=True,
            )
        except (OSError, ValueError) as error:
            result = {
                "schema_version": 1,
                "error": {"code": "TOOL_FAILED", "message": str(error)[:2000]},
            }
            return CallToolResult(
                content=[TextContent(type="text", text=json.dumps(result, ensure_ascii=False))],
                structuredContent=result,
                isError=True,
            )

    try:
        async with stdio_server() as (read, write):
            await server.run(read, write, server.create_initialization_options())
    finally:
        await asyncio.to_thread(tools.close)
