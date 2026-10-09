"""Verify the built wheel in a clean venv outside the source checkout."""

import argparse
import json
import os
import subprocess
import tempfile
import venv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", default="artifacts/install-smoke-windows.json")
    args = parser.parse_args()
    wheel = max((ROOT / "dist").glob("*.whl"), key=lambda path: path.stat().st_mtime)
    with tempfile.TemporaryDirectory(prefix="dw-install-") as temporary:
        directory = Path(temporary)
        environment = directory / "environment"
        venv.EnvBuilder(with_pip=True).create(environment)
        binary = environment / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        env = {
            key: value
            for key, value in os.environ.items()
            if key not in {"PYTHONPATH", "VIRTUAL_ENV"}
        }
        env["PYTHONUTF8"] = "1"
        env.update(
            {
                "DW_DATA_DIR": str(directory / "data"),
                "DW_CACHE_DIR": str(directory / "cache"),
                "DW_LOG_DIR": str(directory / "logs"),
            }
        )
        subprocess.run(
            [str(binary), "-m", "pip", "install", f"{wheel}[gui]"],
            check=True,
            env=env,
            cwd=directory,
        )
        subprocess.run(
            [str(binary), "-m", "design_workbench.interfaces.cli", "--help"],
            check=True,
            env=env,
            cwd=directory,
        )
        subprocess.run(
            [str(binary), "-m", "design_workbench.interfaces.cli", "info"],
            check=True,
            env=env,
            cwd=directory,
        )
        check = subprocess.run(
            [str(binary), "-c", "import design_workbench; print(design_workbench.__file__)"],
            check=True,
            capture_output=True,
            text=True,
            env=env,
            cwd=directory,
        )
        assert Path(check.stdout.strip()).is_relative_to(environment)
        command = [str(binary), "-m", "design_workbench.interfaces.cli"]
        project = directory / "portable.dwbench"
        request = directory / "edit.json"
        request.write_text(
            json.dumps(
                {
                    "expected_revision": 0,
                    "request_id": "install",
                    "operations": [
                        {
                            "op": "fill",
                            "bounds": {"low": [0, 0, 0], "high": [2, 1, 2]},
                            "state": {"name": "oak_planks"},
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )
        for arguments in (
            ["create", str(project)],
            ["edit", str(project), str(request)],
            ["export", str(project), str(directory / "portable.litematic"), "--revision", "1"],
        ):
            subprocess.run(command + arguments, check=True, env=env, cwd=directory)
        validate = """
from pathlib import Path
import design_workbench
from design_workbench.adapters.resources.catalog import Catalog
from design_workbench.adapters.formats.litematic import Litematic
root=Path(design_workbench.__file__).parent
assert (root/'static/index.html').is_file()
assert list((root/'static/assets').glob('*.js'))
assert len(Catalog().blocks)==1003
scene,report=Litematic(Catalog()).read(Path('portable.litematic').read_bytes())
assert scene.summary()['blocks']==18
print('Wheel frontend/catalog/create/edit/export verified')
"""
        subprocess.run([str(binary), "-c", validate], check=True, env=env, cwd=directory)
        report = {
            "wheel": wheel.name,
            "isolated_install": True,
            "installed_path": check.stdout.strip(),
            "source_checkout_required": False,
            "create_edit_export": True,
            "frontend_and_registry_in_wheel": True,
        }
        (ROOT / "artifacts").mkdir(exist_ok=True)
        (ROOT / args.report).write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(json.dumps(report))


if __name__ == "__main__":
    main()
