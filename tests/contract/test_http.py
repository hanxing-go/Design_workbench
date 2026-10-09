from pathlib import Path

from fastapi.testclient import TestClient

from design_workbench.application.contracts import EditRequest
from design_workbench.config import Settings
from design_workbench.interfaces.http import create_app


def test_http_and_application_share_semantics(tmp_path: Path) -> None:
    settings = Settings(
        data_dir=tmp_path / "data", cache_dir=tmp_path / "cache", log_dir=tmp_path / "log"
    )
    app = create_app(settings)
    with TestClient(app) as client:
        created = client.post("/api/projects", json={"name": "契约测试"})
        assert created.status_code == 201
        identifier = created.json()["project_id"]
        path = f"/api/projects/{identifier}"
        request = {
            "expected_revision": 0,
            "request_id": "contract",
            "operations": [
                {
                    "op": "fill",
                    "bounds": {"low": [0, 0, 0], "high": [3, 2, 3]},
                    "state": {"name": "stone"},
                }
            ],
        }
        preview = client.post(path + "/preview", json=request)
        assert preview.json()["changed"] == 48
        assert client.get(path).json()["revision"] == 0
        result = client.post(path + "/edit", json=request)
        assert result.status_code == 200
        service = app.state.workbench.service(
            settings.data_dir / "projects" / f"{identifier}.dwbench"
        )
        assert service.edit(EditRequest.model_validate(request)) == result.json()
        assert client.get(path).json()["blocks"] == 48
        request["request_id"] = "stale"
        conflict = client.post(path + "/edit", json=request)
        assert conflict.status_code == 409
        assert conflict.json()["error"]["revision"] == 1
        assert conflict.json()["error"]["request_id"]
        request["operations"][0]["unknown"] = True
        invalid = client.post(path + "/edit", json=request)
        assert invalid.status_code == 422
        assert invalid.json()["error"]["code"] == "INVALID_REQUEST"
        assert client.post("/api/projects", json={"name": "x", "unknown": True}).status_code == 422
