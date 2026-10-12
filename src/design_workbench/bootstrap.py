from pathlib import Path
from threading import RLock

from design_workbench.adapters.formats.litematic import Litematic
from design_workbench.adapters.resources.catalog import Catalog
from design_workbench.adapters.resources.pack import ResourceManager, ResourcePack
from design_workbench.adapters.storage.sqlite import SqliteStore
from design_workbench.application.scenes import SceneService
from design_workbench.config import Settings
from design_workbench.domain.editing import EditLimits, Editor
from design_workbench.domain.errors import WorkbenchError
from design_workbench.logging import configure_logging


class Workbench:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._versions: dict[str, Workbench] = {}
        self._version_lock = RLock()
        configure_logging(settings.log_dir)
        self.catalog = Catalog(settings.minecraft_version)
        self.resources = ResourceManager(settings.cache_dir / "resources")
        self._pack = self.resources.active(settings.minecraft_version)
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

    @property
    def pack(self) -> ResourcePack | None:
        # A running server may precede the first resource import.
        if self._pack is None:
            self._pack = self.resources.active(self.catalog.version)
            if self._pack is not None:
                self.catalog.language = self._pack.language
        return self._pack

    @pack.setter
    def pack(self, value: ResourcePack | None) -> None:
        self._pack = value

    def for_version(self, version: str | None = None) -> "Workbench":
        version = version or self.catalog.version
        if version == self.catalog.version:
            return self
        with self._version_lock:
            if version not in self._versions:
                self._versions[version] = Workbench(
                    self.settings.model_copy(update={"minecraft_version": version})
                )
            return self._versions[version]

    def for_project(self, project: Path) -> "Workbench":
        version, data_version = SqliteStore(project, self.settings.database_timeout).game_version()
        workbench = self.for_version(version)
        if workbench.catalog.data_version != data_version:
            raise WorkbenchError("VERSION_MISMATCH", "项目游戏版本与 DataVersion 不一致。")
        return workbench

    def service(self, project: Path) -> SceneService:
        workbench = self.for_project(project)
        return SceneService(
            SqliteStore(project, self.settings.database_timeout),
            workbench.editor,
            workbench.formats,
        )
