from pathlib import Path
from types import SimpleNamespace

import pytest

from design_workbench.adapters.resources import pack


@pytest.mark.parametrize("winerror", [5, 32, 33])
def test_publication_retries_windows_scanner_locks(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, winerror: int
) -> None:
    temporary = tmp_path / "temporary"
    temporary.mkdir()
    (temporary / "manifest.json").write_text("{}", encoding="utf-8")
    destination = tmp_path / "published"
    original_rename = Path.rename
    attempts = 0
    delays: list[float] = []
    error = PermissionError("Resource directory is temporarily locked")
    error.winerror = winerror

    def rename(source: Path, target: Path) -> Path:
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            raise error
        return original_rename(source, target)

    monkeypatch.setattr(pack, "os", SimpleNamespace(name="nt"))
    monkeypatch.setattr(pack.time, "sleep", delays.append)
    monkeypatch.setattr(Path, "rename", rename)
    pack.publish_directory(temporary, destination)
    assert attempts == 3
    assert delays == [0.1, 0.2]
    assert not temporary.exists()
    assert (destination / "manifest.json").read_text(encoding="utf-8") == "{}"


@pytest.mark.parametrize("platform, winerror", [("posix", 5), ("nt", None), ("nt", 123)])
def test_publication_preserves_unrelated_permission_errors(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, platform: str, winerror: int | None
) -> None:
    error = PermissionError("Publication is not permitted")
    if winerror is not None:
        error.winerror = winerror
    attempts = 0
    delays: list[float] = []

    def rename(source: Path, target: Path) -> Path:
        nonlocal attempts
        attempts += 1
        raise error

    monkeypatch.setattr(pack, "os", SimpleNamespace(name=platform))
    monkeypatch.setattr(pack.time, "sleep", delays.append)
    monkeypatch.setattr(Path, "rename", rename)
    with pytest.raises(PermissionError) as raised:
        pack.publish_directory(tmp_path / "temporary", tmp_path / "published")
    assert raised.value is error
    assert attempts == 1
    assert not delays


def test_publication_stops_retrying_a_persistent_windows_lock(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    error = PermissionError("Resource directory remains locked")
    error.winerror = 32
    attempts = 0
    delays: list[float] = []

    def rename(source: Path, target: Path) -> Path:
        nonlocal attempts
        attempts += 1
        raise error

    monkeypatch.setattr(pack, "os", SimpleNamespace(name="nt"))
    monkeypatch.setattr(pack.time, "sleep", delays.append)
    monkeypatch.setattr(Path, "rename", rename)
    with pytest.raises(PermissionError) as raised:
        pack.publish_directory(tmp_path / "temporary", tmp_path / "published")
    assert raised.value is error
    assert attempts == 10
    assert delays == pytest.approx([0.1 * attempt for attempt in range(1, 10)])
