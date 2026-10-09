from pathlib import Path

import pytest

from design_workbench.adapters.formats.litematic import Litematic
from design_workbench.adapters.resources.catalog import Catalog
from design_workbench.adapters.storage.sqlite import SqliteStore
from design_workbench.application.scenes import SceneService
from design_workbench.domain.editing import EditLimits, Editor
from design_workbench.domain.models import Bounds


@pytest.fixture(scope="session")
def catalog() -> Catalog:
    return Catalog()


@pytest.fixture
def service(tmp_path: Path, catalog: Catalog) -> SceneService:
    store = SqliteStore.create(
        tmp_path / "scene.dwbench",
        "测试",
        catalog.version,
        catalog.data_version,
        Bounds((-128, -64, -128), (127, 127, 127)),
    )
    return SceneService(store, Editor(catalog, EditLimits()), Litematic(catalog))
