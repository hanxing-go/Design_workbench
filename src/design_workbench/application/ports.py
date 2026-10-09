from typing import Any, Protocol

from design_workbench.domain.models import Cell, Point, Scene


class SceneRepository(Protocol):
    def load(self) -> Scene: ...
    def replay(self, request_id: str, fingerprint: str) -> dict[str, Any] | None: ...
    def commit(
        self,
        scene: Scene,
        changes: list[tuple[Point, Cell | None, Cell | None]],
        expected_revision: int,
        request_id: str,
        fingerprint: str,
        attachment: bytes | None = None,
    ) -> dict[str, Any]: ...
    def history(
        self, direction: str, expected_revision: int, request_id: str, fingerprint: str
    ) -> dict[str, Any]: ...
    def attachment(self) -> bytes | None: ...
    def history_info(self) -> dict[str, Any]: ...


class FormatAdapter(Protocol):
    def read(self, payload: bytes) -> tuple[Scene, dict[str, Any]]: ...
    def write(
        self, scene: Scene, source: bytes | None = None, allow_lossy: bool = False
    ) -> tuple[bytes, dict[str, Any]]: ...
