import sqlite3
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from design_workbench.application.contracts import EditRequest
from design_workbench.application.design_contracts import CandidateOpen, DesignDecision
from design_workbench.bootstrap import Workbench
from design_workbench.config import Settings
from design_workbench.domain.errors import WorkbenchError
from design_workbench.interfaces.http import create_app
from design_workbench.interfaces.tools import Tools


def setup(
    tmp_path: Path,
    *,
    existing: bool = False,
    budget: dict[str, int] | None = None,
    auto: bool = False,
) -> tuple[Tools, str, str]:
    tools = Tools(
        Workbench(
            Settings(
                data_dir=tmp_path / "data", cache_dir=tmp_path / "cache", log_dir=tmp_path / "log"
            )
        ),
        isolated=False,
    )
    project = tools.call(
        "project.create", {"request_id": "create", "request": {"name": "设计测试"}}
    )["project_id"]
    if existing:
        tools.call("scene.commit_edit", {"project": project, "request": edit(0, "initial")})
    run = tools.call(
        "design.start",
        {
            "project": project,
            "request_id": "run",
            "expected_revision": int(existing),
            "prompt": "保留主体，修改一格",
            "auto_build": auto,
            "budget": budget or {},
        },
    )
    return tools, project, run["run_id"]


def edit(revision: int, request: str, state: str = "stone") -> dict[str, object]:
    return {
        "expected_revision": revision,
        "request_id": request,
        "operations": [
            {"op": "set", "blocks": [{"position": [0, 0, 0], "state": {"name": state}}]}
        ],
    }


def propose(tools: Tools, run: str, revision: int, key: str = "propose") -> dict:
    return tools.call(
        "design.propose",
        {
            "run_id": run,
            "request_id": key,
            "request": edit(revision, key, "oak_planks"),
            "explanation": "替换一格为橡木",
        },
    )


def test_existing_building_requires_approval_and_stale_preview_cannot_overwrite(
    tmp_path: Path,
) -> None:
    tools, project, run = setup(tmp_path, existing=True)
    with pytest.raises(WorkbenchError, match="设计任务管理"):
        tools.call("scene.commit_edit", {"project": project, "request": edit(1, "bypass")})
    pending = tools.call(
        "design.call",
        {
            "run_id": run,
            "request_id": "call",
            "tool": "scene.commit_edit",
            "arguments": {"request": edit(1, "change", "oak_planks")},
        },
    )
    assert pending["status"] == "awaiting_approval"
    assert tools.workbench.service(tools.project_path(project)).summary()["revision"] == 1
    # Manual editing remains available while AI waits for approval.
    tools.workbench.service(tools.project_path(project)).edit(
        EditRequest.model_validate(edit(1, "human", "glass"))
    )
    decision = DesignDecision(
        run_id=run, request_id="approve", proposal_id=pending["pending"]["proposal_id"]
    )
    result = tools.designs.decide(decision, True)
    assert result["error"]["code"] == "REVISION_CONFLICT"
    assert tools.designs.status(run)["status"] == "failed"
    assert (
        tools.workbench.service(tools.project_path(project))
        .repository.load()
        .cells[(0, 0, 0)]
        .state.name
        == "minecraft:glass"
    )
    tools.close()


def test_approval_is_idempotent_and_rejection_does_not_write(tmp_path: Path) -> None:
    tools, project, run = setup(tmp_path)
    pending = propose(tools, run, 0)
    decision = DesignDecision(
        run_id=run, request_id="approve", proposal_id=pending["pending"]["proposal_id"]
    )
    result = tools.designs.decide(decision, True)
    assert result["usage"]["revisions"] == 1
    assert tools.designs.decide(decision, True) == result
    rejected = propose(tools, run, 1, "second")
    tools.designs.decide(
        DesignDecision(
            run_id=run, request_id="reject", proposal_id=rejected["pending"]["proposal_id"]
        ),
        False,
    )
    assert tools.workbench.service(tools.project_path(project)).summary()["revision"] == 1
    assert "design.approve" not in {item["name"] for item in tools.descriptions()}
    tools.close()


def test_budget_retries_cancellation_and_resume_persist_across_processes(tmp_path: Path) -> None:
    tools, project, run = setup(tmp_path, budget={"tool_calls": 1})
    call = {"run_id": run, "request_id": "read", "tool": "scene.summary", "arguments": {}}
    first = tools.call("design.call", call)
    assert tools.call("design.call", call) == first
    assert tools.call("design.status", {"run_id": run})["status"] == "active"
    assert (
        tools.call("design.call", {**call, "request_id": "over"})["error"]["code"]
        == "DESIGN_STOPPED"
    )
    assert tools.call("design.status", {"run_id": run})["status"] == "budget_exceeded"
    tools.close()
    new = Tools(Workbench(tools.workbench.settings), isolated=False)
    assert new.call("design.status", {"run_id": run})["usage"]["tool_calls"] == 1
    result = new.call(
        "design.resume", {"run_id": run, "request_id": "extend", "budget": {"tool_calls": 10}}
    )
    assert result["status"] == "active" and result["usage"]["tool_calls"] == 1
    new.call("design.cancel", {"run_id": run, "request_id": "cancel"})
    assert (
        new.call("design.call", {**call, "request_id": "cancelled-read"})["error"]["code"]
        == "DESIGN_STOPPED"
    )
    assert new.call("design.resume", {"run_id": run, "request_id": "resume"})["status"] == "active"
    assert new.workbench.service(new.project_path(project)).summary()["revision"] == 0
    new.close()


def test_cumulative_tokens_and_cost_cannot_be_double_counted_or_lowered(tmp_path: Path) -> None:
    tools, _, run = setup(tmp_path, budget={"tokens": 99})
    usage = {
        "run_id": run,
        "request_id": "usage",
        "input_tokens": 80,
        "cached_input_tokens": 60,
        "output_tokens": 20,
        "source": "actual cumulative provider counters",
    }
    result = tools.call("design.usage", usage)
    assert result["status"] == "budget_exceeded"
    assert tools.call("design.usage", usage) == result
    assert result["usage"]["cost_usd"] is None
    assert result["usage"]["input_tokens"] + result["usage"]["output_tokens"] == 100
    assert (
        tools.call("design.usage", {**usage, "request_id": "lower", "input_tokens": 70})["error"][
            "code"
        ]
        == "INVALID_USAGE"
    )
    tools.close()


def test_candidate_is_immutable_preserves_nbt_and_opens_as_independent_project(
    tmp_path: Path,
) -> None:
    tools, project, run = setup(tmp_path, existing=True)
    path = tools.project_path(project)
    with sqlite3.connect(path) as connection:
        connection.execute(
            "INSERT INTO attachments VALUES('litematic',?)", (b"original NBT fixture",)
        )
    request = {
        "run_id": run,
        "request_id": "save",
        "expected_revision": 1,
        "name": "第一稿",
        "feedback": "保留入口",
    }
    candidate = tools.call("candidate.save", request)
    assert tools.call("candidate.save", request) == candidate
    tools.workbench.service(path).edit(EditRequest.model_validate(edit(1, "later", "glass")))
    tools.close()
    reopened = Tools(Workbench(tools.workbench.settings), isolated=False)
    body = CandidateOpen(request_id="open")
    clone = reopened.designs.open_candidate(run, candidate["candidate_id"], body)
    assert reopened.designs.open_candidate(run, candidate["candidate_id"], body) == clone
    assert clone["project_id"] != project
    assert "保留入口" in reopened.designs.status(clone["run_id"])["prompt"]
    scene, source = reopened.workbench.service(
        reopened.project_path(clone["project_id"])
    ).repository.snapshot()
    assert scene.revision == 1 and scene.cells[(0, 0, 0)].state.name == "minecraft:stone"
    assert source == b"original NBT fixture"
    with sqlite3.connect(path) as connection:
        assert json_value(connection, "scene")["revision"] == 2
    reopened.close()


def json_value(connection: sqlite3.Connection, key: str) -> dict:
    import json

    return json.loads(
        connection.execute("SELECT value FROM meta WHERE key=?", (key,)).fetchone()[0]
    )


def test_concurrent_duplicate_proposals_have_one_receipt(tmp_path: Path) -> None:
    tools, _, run = setup(tmp_path)
    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(propose, tools, run, 0) for _ in range(2)]
        results = [future.result() for future in futures]
    assert results[0] == results[1]
    assert tools.designs.status(run)["usage"]["tool_calls"] == 1
    tools.close()


def test_last_budgeted_proposal_can_be_approved_and_waiting_pauses_elapsed_time(
    tmp_path: Path,
) -> None:
    tools, project, run = setup(tmp_path, budget={"tool_calls": 1, "revisions": 1})
    pending = propose(tools, run, 0)
    record = tools.designs.status(run)
    assert record["status"] == "awaiting_approval"
    with tools.designs.store.edit(run) as saved:
        assert saved["active_since"] is None
    approved = tools.designs.decide(
        DesignDecision(
            run_id=run, request_id="approve-last", proposal_id=pending["pending"]["proposal_id"]
        ),
        True,
    )
    assert approved["status"] == "active"
    assert approved["usage"]["revisions"] == 1
    assert tools.workbench.service(tools.project_path(project)).summary()["revision"] == 1
    tools.close()


def test_manual_edit_revokes_empty_project_auto_build_permission(tmp_path: Path) -> None:
    tools, project, run = setup(tmp_path, auto=True)
    tools.call("design.update", {"run_id": run, "request_id": "building", "stage": "building"})
    tools.workbench.service(tools.project_path(project)).edit(
        EditRequest.model_validate(edit(0, "human", "glass"))
    )
    result = tools.call(
        "design.call",
        {
            "run_id": run,
            "request_id": "overwrite",
            "tool": "scene.commit_edit",
            "arguments": {"request": edit(1, "ai", "stone")},
        },
    )
    assert result["status"] == "awaiting_approval" and not result["auto_build"]
    assert (
        tools.workbench.service(tools.project_path(project))
        .repository.load()
        .cells[(0, 0, 0)]
        .state.name
        == "minecraft:glass"
    )
    tools.close()


def test_auto_build_is_revoked_after_visual_review_and_retry_remains_idempotent(
    tmp_path: Path,
) -> None:
    tools, project, run = setup(tmp_path, auto=True)
    tools.call("design.update", {"run_id": run, "request_id": "build-stage", "stage": "building"})
    call = {
        "run_id": run,
        "request_id": "build",
        "tool": "scene.commit_edit",
        "arguments": {"request": edit(0, "build")},
    }
    result = tools.call("design.call", call)
    assert result["revision"] == 1
    tools.call("design.update", {"run_id": run, "request_id": "review", "stage": "reviewing"})
    assert tools.call("design.call", call) == result
    tools.call("design.update", {"run_id": run, "request_id": "build-again", "stage": "building"})
    proposal = tools.call(
        "design.call",
        {**call, "request_id": "revision", "arguments": {"request": edit(1, "revision", "glass")}},
    )
    assert proposal["status"] == "awaiting_approval"
    assert tools.workbench.service(tools.project_path(project)).summary()["revision"] == 1
    tools.close()


def test_user_http_decision_and_candidate_download_survive_service_restart(tmp_path: Path) -> None:
    tools, project, run = setup(tmp_path)
    pending = propose(tools, run, 0)
    with TestClient(create_app(tools.workbench.settings)) as client:
        result = client.post(
            f"/api/design-runs/{run}/decision",
            json={
                "run_id": run,
                "request_id": "human-approve",
                "proposal_id": pending["pending"]["proposal_id"],
                "approve": True,
            },
        )
        assert result.status_code == 200 and result.json()["status"] == "active"
        candidate = client.post(
            f"/api/design-runs/{run}/candidates",
            json={"run_id": run, "request_id": "candidate", "name": "存档", "expected_revision": 1},
        ).json()
        assert client.get(f"/api/projects/{project}/design-runs").json()["items"][0]["candidates"]
    with TestClient(create_app(tools.workbench.settings)) as client:
        saved = client.get(
            f"/api/design-runs/{run}/candidates/{candidate['candidate_id']}/download"
        )
        assert saved.status_code == 200 and saved.content.startswith(b"SQLite format 3")
        assert client.get(f"/api/design-runs/{run}").json()["usage"]["revisions"] == 1
    tools.close()
