import contextlib
import subprocess
import sys
import textwrap
import time
from pathlib import Path

import pytest

from design_workbench.interfaces.desktop import desktop_settings, local_socket
from design_workbench.runtime import worker_command


def test_desktop_helpers_work_without_tkinter(tmp_path: Path) -> None:
    script = textwrap.dedent(
        """
        import importlib.abc
        import sys
        from pathlib import Path

        class BlockTkinter(importlib.abc.MetaPathFinder):
            def find_spec(self, fullname, path=None, target=None):
                if fullname == "tkinter" or fullname.startswith("tkinter."):
                    raise ModuleNotFoundError("tkinter is unavailable", name=fullname)
                return None

        sys.meta_path.insert(0, BlockTkinter())
        from design_workbench.interfaces.desktop import desktop_settings, local_socket

        directory = Path(sys.argv[1])
        (directory / "portable.flag").touch()
        settings = desktop_settings(directory)
        assert settings.data_dir == directory / "userdata" / "data"
        with local_socket() as listener:
            assert listener.getsockname()[0] == "127.0.0.1"
            assert listener.getsockname()[1] > 0
        assert "tkinter" not in sys.modules
        """
    )
    result = subprocess.run(
        [sys.executable, "-c", script, str(tmp_path)], capture_output=True, text=True
    )
    assert result.returncode == 0, result.stderr


def test_portable_paths_survive_relocation(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DW_DATA_DIR", str(tmp_path / "external"))
    directory = tmp_path / "中文 portable"
    directory.mkdir()
    (directory / "portable.flag").touch()
    (directory / "config.toml").write_text(
        'max_blocks = 12345\ndata_dir = "other"\n', encoding="utf-8"
    )
    settings = desktop_settings(directory)
    assert settings.data_dir == directory / "userdata/data"
    assert settings.cache_dir == directory / "userdata/cache"
    assert settings.max_blocks == 12345


def test_busy_port_falls_back_without_releasing_socket() -> None:
    first = local_socket()
    second = local_socket()
    try:
        assert first.getsockname()[0] == second.getsockname()[0] == "127.0.0.1"
        assert first.getsockname()[1] != second.getsockname()[1]
    finally:
        first.close()
        second.close()


def test_frozen_workers_use_bundled_console_executable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", str(Path("bundle") / "DesignWorkbench.exe"))
    assert worker_command("worker", "argument") == [
        str(Path("bundle") / "WorkbenchCLI.exe"),
        "-m",
        "worker",
        "argument",
    ]


@pytest.mark.skipif(sys.platform != "win32", reason="Windows file lock")
def test_instance_lock_is_released_on_close(tmp_path: Path) -> None:
    from design_workbench.interfaces.desktop import InstanceLock

    first = InstanceLock(tmp_path)
    try:
        first.publish("http://127.0.0.1:8765")
        with pytest.raises(OSError):
            InstanceLock(tmp_path)
    finally:
        first.close()
    second = InstanceLock(tmp_path)
    second.close()


@pytest.mark.skipif(sys.platform != "win32", reason="Windows launcher GUI")
def test_launcher_opens_only_after_server_ready_and_stops(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import tkinter as tk

    from design_workbench.config import Settings
    from design_workbench.interfaces.desktop import InstanceLock, Launcher

    opened: list[str] = []
    monkeypatch.setattr("webbrowser.open", lambda url: opened.append(url) or True)
    settings = Settings(
        data_dir=tmp_path / "data", cache_dir=tmp_path / "cache", log_dir=tmp_path / "logs"
    )
    lock = InstanceLock(settings.data_dir)
    root = tk.Tk()
    root.withdraw()
    launcher = Launcher(root, settings, lock)
    try:
        assert not opened
        assert "首次使用" in launcher.status.get()
        launcher.start_server()
        deadline = time.monotonic() + 15
        while not opened and time.monotonic() < deadline:
            root.update()
            time.sleep(0.02)
        assert opened == [launcher.url]
        assert lock.state.is_file()
        assert launcher.server is not None and launcher.server.started
        launcher.close()
        while (
            launcher.thread is not None
            and launcher.thread.is_alive()
            and time.monotonic() < deadline
        ):
            root.update()
            time.sleep(0.02)
        assert launcher.thread is not None and not launcher.thread.is_alive()
    finally:
        if launcher.server:
            launcher.server.should_exit = True
        if launcher.thread:
            launcher.thread.join(timeout=5)
        with contextlib.suppress(tk.TclError):
            root.destroy()
        lock.close()
