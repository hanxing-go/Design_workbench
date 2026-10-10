"""External stdio MCP client for interactive AI acceptance and replayable evidence.

Each invocation performs a real initialize/list_tools/call_tool exchange. The
caller chooses the next tool after reading JSON and PNGs; this is not an AI mock
or an automatic building script.
"""

import argparse
import asyncio
import base64
import importlib.metadata
import json
import os
import sys
import time
from datetime import timedelta
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("tool")
    parser.add_argument("request", type=Path)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    arguments = json.loads(args.request.read_text(encoding="utf-8"))
    parameters = StdioServerParameters(
        command=sys.executable,
        args=[
            "-m",
            "design_workbench.interfaces.cli",
            "mcp",
            "--config",
            str(args.config.resolve()),
        ],
        env={**os.environ, "PYTHONUTF8": "1"},
    )
    async with (
        stdio_client(parameters) as (read, write),
        ClientSession(read, write, read_timeout_seconds=timedelta(seconds=140)) as session,
    ):
        initialized = await session.initialize()
        descriptions = await session.list_tools()
        assert args.tool in {tool.name for tool in descriptions.tools}
        result = await session.call_tool(args.tool, arguments)
        value = result.structuredContent or {
            "content": [item.model_dump() for item in result.content if item.type == "text"]
        }
        images = [item for item in result.content if item.type == "image"]
        for index, content in enumerate(images):
            target = args.output_dir / value["images"][index]["file"]
            target.write_bytes(base64.b64decode(content.data, validate=True))
            value["images"][index]["path"] = str(target.resolve())
        record = {
            "client": "MCP Python SDK",
            "client_version": importlib.metadata.version("mcp"),
            "server": initialized.serverInfo.model_dump(),
            "protocol": initialized.protocolVersion,
            "tool": args.tool,
            "arguments": arguments,
            "result": value,
            "isError": result.isError,
            "image_count": len(images),
            "timestamp_ns": time.time_ns(),
        }
        filename = args.output_dir / f"{record['timestamp_ns']}-{args.tool}.json"
        filename.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(record, ensure_ascii=False, indent=2))
        failed = result.isError
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    asyncio.run(main())
