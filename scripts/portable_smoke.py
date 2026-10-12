"""Exercise an actual frozen bundle outside the checkout and without Python on PATH."""

import argparse
import json
import os
import re
import shutil
import socket
import subprocess
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


def smoke(bundle: Path) -> None:
    with tempfile.TemporaryDirectory(prefix="dw-portable-") as temporary:
        directory = Path(temporary) / "便携包 test"
        shutil.copytree(bundle, directory)
        executable = directory / "WorkbenchCLI.exe"
        assert executable.is_file() and (directory / "DesignWorkbench.exe").is_file()
        environment = {
            key: value for key, value in os.environ.items() if not key.startswith(("DW_", "PYTHON"))
        }
        environment["PATH"] = str(Path(os.environ["SYSTEMROOT"]) / "System32")
        environment["PYTHONUTF8"] = "1"
        config = directory / "smoke.toml"
        config.write_text(
            'data_dir = "userdata/data"\ncache_dir = "userdata/cache"\nlog_dir = "userdata/logs"\n',
            encoding="utf-8",
        )

        def cli(*args: str) -> dict[str, Any]:
            result = subprocess.run(
                [str(executable), *args, "--config", str(config)],
                cwd=directory,
                env=environment,
                capture_output=True,
                timeout=90,
            )
            assert result.returncode == 0, result.stderr.decode(
                "utf-8", "replace"
            ) + result.stdout.decode("utf-8", "replace")
            return json.loads(result.stdout)

        assert cli("info")["version"]
        assert cli("tools")["tools"]
        with socket.socket() as listener:
            listener.bind(("127.0.0.1", 0))
            port = listener.getsockname()[1]
        url = f"http://127.0.0.1:{port}"

        def request(route: str, body: dict[str, Any] | None = None) -> Any:
            data = json.dumps(body).encode() if body is not None else None
            with urllib.request.urlopen(
                urllib.request.Request(
                    url + route, data=data, headers={"Content-Type": "application/json"}
                ),
                timeout=10,
            ) as response:
                return json.load(response)

        def start() -> subprocess.Popen[bytes]:
            process = subprocess.Popen(
                [str(executable), "serve", "--port", str(port), "--config", str(config)],
                cwd=directory,
                env=environment,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
            )
            for _ in range(150):
                if process.poll() is not None:
                    raise AssertionError(process.communicate()[1].decode("utf-8", "replace"))
                try:
                    assert request("/api/info")["minecraft_version"] == "1.20.1"
                    return process
                except (urllib.error.URLError, TimeoutError):
                    time.sleep(0.2)
            process.kill()
            process.wait()
            raise AssertionError("Frozen server did not become ready")

        def stop(process: subprocess.Popen[bytes]) -> None:
            process.terminate()
            process.communicate(timeout=20)

        process = start()
        try:
            with urllib.request.urlopen(url + "/", timeout=10) as response:
                html = response.read().decode("utf-8")
                assert "<html" in html
            assets = re.findall(r'(?:src|href)="(/assets/[^\"]+)"', html)
            assert assets, "Frontend asset references missing"
            for asset in assets:
                with urllib.request.urlopen(url + asset, timeout=10) as response:
                    content = response.read()
                    assert content and b"<html" not in content[:100], asset
            identifier = request("/api/projects", {"name": "便携包验收"})["project_id"]
            path = f"/api/projects/{identifier}"
            edit = {
                "expected_revision": 0,
                "request_id": "portable-smoke",
                "operations": [
                    {
                        "op": "fill",
                        "bounds": {"low": [0, 0, 0], "high": [1, 1, 1]},
                        "state": {"name": "minecraft:stone"},
                    }
                ],
            }
            assert request(path + "/preview", edit)["changed"] == 8
            assert request(path + "/edit", edit)["revision"] == 1
            assert request(path)["blocks"] == 8
        finally:
            stop(process)
        tool = directory / "query.json"
        tool.write_text(json.dumps({"project": identifier}), encoding="utf-8")
        result = cli("tool", "scene.summary", str(tool))
        assert "error" not in result, result
        project = directory / "userdata/data/projects" / f"{identifier}.dwbench"
        exported = directory / "export.litematic"
        cli("export", str(project), str(exported), "--revision", "1")
        assert exported.stat().st_size > 0
        process = start()
        try:
            assert request(path)["blocks"] == 8
            assert request(path)["revision"] == 1
        finally:
            stop(process)
        print(
            "Portable smoke passed: relocated bundle, HTTP UI, edits, persistence, export, frozen worker"
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("bundle", type=Path)
    smoke(parser.parse_args().bundle.resolve())
