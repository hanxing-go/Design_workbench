from pathlib import Path

from design_workbench.adapters.formats.litematic import Litematic
from design_workbench.adapters.resources.catalog import Catalog
from design_workbench.adapters.resources.pack import ResourceManager
from design_workbench.adapters.storage.sqlite import SqliteStore
from design_workbench.application.scenes import SceneService
from design_workbench.config import Settings
from design_workbench.domain.editing import EditLimits, Editor
from design_workbench.logging import configure_logging


class Workbench:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        configure_logging(settings.log_dir)
        self.catalog = Catalog(settings.minecraft_version)
        self.resources = ResourceManager(settings.cache_dir / "resources")
        self.pack = self.resources.active(settings.minecraft_version)
        if self.pack:
            self.catalog.language = self.pack.language
        self.editor = Editor(
            self.catalog,
            EditLimits(settings.max_blocks, settings.max_edit_cells, settings.max_operations),
        )
        self.formats = Litematic(
            self.catalog,
            self.catalog.version,
            self.catalog.data_version,
            settings.max_selection_volume,
        )

    def service(self, project: Path) -> SceneService:
        return SceneService(
            SqliteStore(project, self.settings.database_timeout), self.editor, self.formats
        )
