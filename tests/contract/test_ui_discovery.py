from pathlib import Path

from fastapi.testclient import TestClient

from design_workbench.adapters.resources.pack import ResourceManager
from design_workbench.config import Settings
from design_workbench.interfaces.http import create_app


def test_version_listing_does_not_upgrade_packs(tmp_path: Path, monkeypatch) -> None:
    app = create_app(
        Settings(
            data_dir=tmp_path / "data", cache_dir=tmp_path / "cache", log_dir=tmp_path / "logs"
        )
    )

    def forbidden_load(*args, **kwargs):
        raise AssertionError("Version discovery must not load or upgrade resource packs")

    monkeypatch.setattr(ResourceManager, "active", forbidden_load)
    with TestClient(app) as client:
        response = client.get("/api/versions")
        assert response.status_code == 200
        assert len(response.json()["items"]) > 1
        assert all(not item["resources_ready"] for item in response.json()["items"])
