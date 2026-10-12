import ast
import builtins
from pathlib import Path

import pytest
from pydantic import ValidationError
from typer.testing import CliRunner

from design_workbench.config import Settings
from design_workbench.interfaces.cli import app


def test_config_precedence_and_portable_relative_paths(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config = tmp_path / "config.toml"
    config.write_text('data_dir = "data"\nmax_blocks = 1000\n', encoding="utf-8")
    monkeypatch.setenv("DW_MAX_BLOCKS", "2000")
    assert Settings.load(config).data_dir == tmp_path / "data"
    assert Settings.load(config).max_blocks == 2000
    assert Settings.load(config, max_blocks=3000).max_blocks == 3000
    config.write_text("unknown = true", encoding="utf-8")
    with pytest.raises(ValidationError):
        Settings.load(config)


def test_cli_works_from_other_directory(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    result = CliRunner().invoke(app, ["--help"])
    assert result.exit_code == 0
    result = CliRunner().invoke(app, ["info"])
    assert result.exit_code == 0
    assert '"minecraft_version": "1.20.1"' in result.stdout


@pytest.mark.parametrize("missing", ["uvicorn", "fastapi"])
def test_serve_missing_gui_dependency(monkeypatch: pytest.MonkeyPatch, missing: str) -> None:
    original_import = builtins.__import__

    def import_without_gui(name: str, *args: object, **kwargs: object) -> object:
        if name == missing or (missing == "fastapi" and name == "design_workbench.interfaces.http"):
            raise ModuleNotFoundError(f"No module named '{missing}'", name=missing)
        return original_import(name, *args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(builtins, "__import__", import_without_gui)
    result = CliRunner().invoke(app, ["serve"])
    assert result.exit_code == 1
    assert "GUI_DEPENDENCY_MISSING" in result.stdout
    assert "uv run --extra gui design-workbench serve" in result.stdout
    assert "Traceback" not in result.stdout


def test_domain_dependency_direction() -> None:
    import design_workbench

    root = Path(design_workbench.__file__).parent
    banned = (
        "fastapi",
        "typer",
        "pydantic",
        "sqlite3",
        "nbtlib",
        "design_workbench.adapters",
        "design_workbench.interfaces",
        "design_workbench.config",
    )
    for file in (root / "domain").rglob("*.py"):
        for node in ast.walk(ast.parse(file.read_text(encoding="utf-8"))):
            if isinstance(node, ast.Import):
                imports = [entry.name for entry in node.names]
            elif isinstance(node, ast.ImportFrom):
                imports = [node.module or ""]
            else:
                continue
            assert not any(name.startswith(banned) for name in imports), (file, imports)
