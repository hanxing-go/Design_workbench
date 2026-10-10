import asyncio
import hashlib
import json
import os
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from typer.testing import CliRunner

from design_workbench.bootstrap import Workbench
from design_workbench.config import Settings
from design_workbench.domain.errors import WorkbenchError
from design_workbench.interfaces.cli import app as cli
from design_workbench.interfaces.http import create_app
from design_workbench.interfaces.tools import Tools


def configured(tmp_path: Path, **values: object) -> Settings:
    return Settings(
        data_dir=tmp_path / "data",
        cache_dir=tmp_path / "cache",
        log_dir=tmp_path / "logs",
        **values,
    )


def request(revision: int = 0, identifier: str = "fill") -> dict:
    return {
        "expected_revision": revision,
        "request_id": identifier,
        "operations": [
            {
                "op": "fill",
                "bounds": {"low": [0, 0, 0], "high": [3, 2, 3]},
                "state": {"name": "stone"},
            }
        ],
    }


def test_cli_http_mcp_share_requests_retries_and_conflicts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    settings = configured(tmp_path)
    for key, value in settings.json_dict().items():
        if key in {"data_dir", "cache_dir", "log_dir"}:
            monkeypatch.setenv(f"DW_{key.upper()}", str(value))
    with TestClient(create_app(settings)) as client:
        creation = {"request_id": "create", "request": {"name": "三入口契约"}}
        created = client.post("/api/tools/v1/project.create", json=creation).json()
        project = created["project_id"]
        assert client.post("/api/tools/v1/project.create", json=creation).json() == created
        body = {"project": project, "request": request()}
        source = tmp_path / "edit.json"
        source.write_text(json.dumps(body), encoding="utf-8")
        preview = CliRunner().invoke(cli, ["tool", "scene.preview_edit", str(source)])
        assert preview.exit_code == 0, preview.output
        assert json.loads(preview.output)["changed"] == 48
        assert client.get(f"/api/projects/{project}").json()["revision"] == 0

        async def through_mcp() -> dict:
            parameters = StdioServerParameters(
                command=sys.executable,
                args=["-m", "design_workbench.interfaces.cli", "mcp"],
                env={**os.environ, "PYTHONUTF8": "1"},
            )
            async with (
                stdio_client(parameters) as (read, write),
                ClientSession(read, write) as session,
            ):
                initialized = await session.initialize()
                assert initialized.serverInfo.version == "1.0.0"
                tools = await session.list_tools()
                assert {
                    "scene.commit_edit",
                    "render.views",
                    "design.start",
                    "design.propose",
                    "candidate.save",
                } <= {tool.name for tool in tools.tools}
                assert "design.approve" not in {tool.name for tool in tools.tools}
                assert all(
                    tool.inputSchema.get("additionalProperties") is False for tool in tools.tools
                )
                committed = await session.call_tool("scene.commit_edit", body)
                assert not committed.isError
                assert (
                    await session.call_tool("scene.commit_edit", body)
                ).structuredContent == committed.structuredContent
                invalid = await session.call_tool("catalog.search", {"schema_version": 2})
                assert (
                    invalid.isError
                    and invalid.structuredContent["error"]["code"] == "INVALID_REQUEST"
                )
                stale = await session.call_tool(
                    "scene.commit_edit",
                    {"project": project, "request": request(identifier="stale")},
                )
                assert stale.isError and stale.structuredContent["error"]["revision"] == 1
                return committed.structuredContent

        committed = asyncio.run(through_mcp())
        assert client.post("/api/tools/v1/scene.commit_edit", json=body).json() == committed
        assert client.get(f"/api/projects/{project}").json()["blocks"] == 48
        read = client.post(
            "/api/tools/v1/scene.inspect",
            json={"project": project, "selector": {"name": "stone"}, "limit": 2},
        ).json()
        assert read["total"] == 48 and read["truncated"] and len(read["blocks"]) == 2
        assert (
            client.post("/api/tools/v1/catalog.search", json={"unexpected": 1}).status_code == 422
        )


def test_export_receipt_survives_edits_and_preserves_original_bytes(tmp_path: Path) -> None:
    tools = Tools(Workbench(configured(tmp_path)))
    try:
        project = tools.call(
            "project.create", {"request_id": "project", "request": {"name": "导出重试"}}
        )["project_id"]
        tools.call("scene.commit_edit", {"project": project, "request": request()})
        body = {"project": project, "expected_revision": 1, "request_id": "export"}
        exported = tools.call("asset.export", body)
        data = Path(exported["path"]).read_bytes()
        assert hashlib.sha256(data).hexdigest() == exported["sha256"]
        tools.call(
            "history.undo",
            {"project": project, "request": {"expected_revision": 1, "request_id": "undo"}},
        )
        assert tools.call("asset.export", body) == exported
        assert Path(exported["path"]).read_bytes() == data
        with pytest.raises(WorkbenchError, match="不能用于不同请求"):
            tools.call("asset.export", {**body, "expected_revision": 2})
        tools.call(
            "history.redo",
            {"project": project, "request": {"expected_revision": 2, "request_id": "redo"}},
        )
        imported = tools.call(
            "project.create", {"request_id": "second", "request": {"name": "回读"}}
        )["project_id"]
        import_request = {
            "project": imported,
            "source": exported["path"],
            "request": {"expected_revision": 0, "request_id": "import"},
        }
        first = tools.call("asset.import", import_request)
        assert tools.call("asset.import", import_request) == first
        assert tools.call("scene.summary", {"project": imported})["blocks"] == 48
    finally:
        tools.close()


def test_tool_limits_and_response_truncation(tmp_path: Path) -> None:
    tools = Tools(
        Workbench(configured(tmp_path, max_tool_response_bytes=4096, max_selection_volume=8))
    )
    try:
        project = tools.call(
            "project.create", {"request_id": "limits", "request": {"name": "limits"}}
        )["project_id"]
        preview = tools.call("scene.preview_edit", {"project": project, "request": request()})
        assert preview["changed"] == 48 and preview["response_truncated"]
        assert len(json.dumps(preview, ensure_ascii=False).encode()) <= 4096
        with pytest.raises(WorkbenchError) as failure:
            tools.call(
                "scene.inspect",
                {
                    "project": project,
                    "selector": {"bounds": {"low": [0, 0, 0], "high": [10, 10, 10]}},
                },
            )
        assert (
            failure.value.code == "SELECTION_LIMIT" and failure.value.location == "selector.bounds"
        )
        with pytest.raises(WorkbenchError) as failure:
            tools.call(
                "catalog.material",
                {"state": {"name": "oak_stairs", "properties": {"facing": "up"}}},
            )
        assert failure.value.code == "INVALID_STATE"
        with pytest.raises(WorkbenchError) as failure:
            tools.call(
                "scene.commit_edit",
                {
                    "project": project,
                    "request": {
                        **request(),
                        "operations": [
                            {
                                "op": "delete",
                                "selector": {"bounds": {"low": [0.5, 0, 0], "high": [1, 1, 1]}},
                            }
                        ],
                    },
                },
            )
        assert failure.value.code == "INVALID_REQUEST" and "low.0" in failure.value.location
    finally:
        tools.close()
    timed = Tools(Workbench(configured(tmp_path / "timeout", tool_timeout=0.001)))
    try:
        with pytest.raises(WorkbenchError) as failure:
            timed.call("catalog.search", {})
        assert failure.value.code == "TOOL_TIMEOUT"
    finally:
        timed.close()


@pytest.mark.parametrize(
    "changes",
    [
        {"views": [{"name": "front"}] * 7},
        {"width": 1600, "height": 1600},
        {"views": [{"name": "custom"}]},
        {"views": [{"name": "custom", "camera": {"position": [0, 0, 0], "target": [0, 0, 0]}}]},
        {
            "views": [
                {
                    "name": "custom",
                    "camera": {"position": [float("nan"), 0, 1], "target": [0, 0, 0]},
                }
            ]
        },
        {
            "views": [
                {
                    "name": "custom",
                    "camera": {"position": [1_000_001, 0, 1], "target": [0, 0, 0]},
                }
            ]
        },
    ],
)
def test_invalid_capture_requests_do_not_start_jobs(tmp_path: Path, changes: dict) -> None:
    tools = Tools(Workbench(configured(tmp_path)))
    try:
        with pytest.raises(WorkbenchError) as failure:
            tools.call(
                "render.views",
                {
                    "project": "unused",
                    "request": {"expected_revision": 0, "request_id": "invalid", **changes},
                },
            )
        assert failure.value.code == "INVALID_REQUEST"
        assert tools._renderer is None
    finally:
        tools.close()
