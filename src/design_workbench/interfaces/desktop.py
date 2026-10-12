"""Local Windows launcher; resources and projects stay outside the application bundle."""

import json
import logging
import os
import queue
import socket
import sys
import threading
import time
import tkinter as tk
import webbrowser
from contextlib import suppress
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Any, TextIO

import uvicorn

from design_workbench.adapters.resources.acquire import fetch_official
from design_workbench.bootstrap import Workbench
from design_workbench.config import Settings
from design_workbench.interfaces.http import create_app


def desktop_settings(directory: Path) -> Settings:
    overrides: dict[str, Any] = {}
    if (directory / "portable.flag").is_file():
        base = directory / "userdata"
        overrides = {
            key: base / leaf
            for key, leaf in (("data_dir", "data"), ("cache_dir", "cache"), ("log_dir", "logs"))
        }
    config = directory / "config.toml"
    return Settings.load(config if config.is_file() else None, **overrides)


class InstanceLock:
    """Windows releases this lock even if the launcher crashes."""

    def __init__(self, directory: Path) -> None:
        directory.mkdir(parents=True, exist_ok=True)
        self.state = directory / "desktop-instance.json"
        self.handle: TextIO = (directory / "desktop.lock").open("a+", encoding="utf-8")
        self.handle.seek(0, 2)
        if self.handle.tell() == 0:
            self.handle.write("0")
            self.handle.flush()
        self.handle.seek(0)
        if sys.platform == "win32":
            import msvcrt

            try:
                msvcrt.locking(self.handle.fileno(), msvcrt.LK_NBLCK, 1)
            except OSError:
                self.handle.close()
                raise
        else:
            self.handle.close()
            raise OSError("The desktop launcher requires Windows")
        self.state.unlink(missing_ok=True)

    def publish(self, url: str) -> None:
        self.state.write_text(json.dumps({"url": url}), encoding="utf-8")

    def close(self) -> None:
        self.state.unlink(missing_ok=True)
        self.handle.close()


def local_socket() -> socket.socket:
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        listener.bind(("127.0.0.1", 8765))
    except OSError:
        listener.bind(("127.0.0.1", 0))
    listener.listen(128)
    return listener


class Launcher:
    def __init__(self, root: tk.Tk, settings: Settings, lock: InstanceLock) -> None:
        self.root, self.settings, self.lock = root, settings, lock
        self.events: queue.Queue[tuple[str, str]] = queue.Queue()
        self.busy = False
        self.server: uvicorn.Server | None = None
        self.thread: threading.Thread | None = None
        self.listener: socket.socket | None = None
        self.url = ""
        self.started_at = 0.0
        root.title("Design Workbench")
        root.geometry("620x360")
        root.minsize(540, 340)
        frame = ttk.Frame(root, padding=24)
        frame.pack(fill="both", expand=True)
        ttk.Label(frame, text="Minecraft 建筑设计工作台", font=("Microsoft YaHei UI", 16)).pack(
            anchor="w"
        )
        ttk.Label(frame, text="Minecraft Java 1.20.1 · 本地运行").pack(anchor="w", pady=(6, 16))
        self.status = tk.StringVar(value="正在检查素材…")
        ttk.Label(frame, textvariable=self.status, wraplength=560).pack(anchor="w")
        self.progress = ttk.Progressbar(frame, mode="indeterminate")
        self.progress.pack(fill="x", pady=12)
        actions = ttk.Frame(frame)
        actions.pack(fill="x")
        self.download = ttk.Button(actions, text="下载官方素材", command=lambda: self.setup(None))
        self.download.pack(side="left")
        self.import_button = ttk.Button(
            actions, text="选择本地客户端 .jar", command=self.choose_jar
        )
        self.import_button.pack(side="left", padx=8)
        self.open_button = ttk.Button(
            frame, text="打开工作台", command=self.open_browser, state="disabled"
        )
        self.open_button.pack(anchor="w", pady=(16, 8))
        ttk.Label(frame, text=f"作品目录：{settings.data_dir / 'projects'}", wraplength=560).pack(
            anchor="w"
        )
        footer = ttk.Frame(frame)
        footer.pack(fill="x", pady=(12, 0))
        ttk.Button(footer, text="打开数据目录", command=self.open_data).pack(side="left")
        ttk.Button(footer, text="退出工作台", command=self.close).pack(side="right")
        root.protocol("WM_DELETE_WINDOW", self.close)
        root.after(100, self.poll)
        if Workbench(settings).pack is not None:
            self.start_server()
        else:
            self.status.set("首次使用需要官方素材。下载需要联网；也可选择 1.20.1 客户端 jar。")

    def open_data(self) -> None:
        self.settings.data_dir.mkdir(parents=True, exist_ok=True)
        if sys.platform == "win32":
            os.startfile(self.settings.data_dir)

    def choose_jar(self) -> None:
        selected = filedialog.askopenfilename(
            title="选择 Minecraft Java 1.20.1 客户端", filetypes=[("客户端", "*.jar")]
        )
        if selected:
            self.setup(Path(selected))

    def setup(self, jar: Path | None) -> None:
        self.busy = True
        self.download.configure(state="disabled")
        self.import_button.configure(state="disabled")
        self.progress.start()
        self.status.set(
            "正在下载并校验官方客户端与中文语言文件…"
            if jar is None
            else "正在校验并导入本地客户端…"
        )

        def work() -> None:
            try:
                source = jar
                language = None
                provenance: dict[str, Any] = {"source": "user-provided-client"}
                if source is None:
                    source, provenance = fetch_official(
                        self.settings.minecraft_version, self.settings.cache_dir / "downloads"
                    )
                    language = Path(provenance["language_path"])
                self.events.put(("progress", "正在解析模型、贴图并构建图集，可能需要数分钟…"))
                Workbench(self.settings).resources.import_jar(
                    source, self.settings.minecraft_version, language, provenance
                )
                self.events.put(("ready", ""))
            except Exception as error:
                logging.exception("Resource setup failed")
                self.events.put(("error", str(error)))

        threading.Thread(target=work, daemon=True).start()

    def start_server(self) -> None:
        self.download.configure(state="disabled")
        self.import_button.configure(state="disabled")
        self.status.set("正在启动本地工作台…")
        self.progress.start()
        self.listener = local_socket()
        self.url = f"http://127.0.0.1:{self.listener.getsockname()[1]}"
        self.server = uvicorn.Server(
            uvicorn.Config(
                create_app(self.settings),
                host="127.0.0.1",
                log_config=None,
                loop="asyncio",
                http="h11",
                ws="none",
            )
        )
        self.thread = threading.Thread(
            target=self.server.run, kwargs={"sockets": [self.listener]}, daemon=True
        )
        self.started_at = time.monotonic()
        self.thread.start()

    def poll(self) -> None:
        try:
            while True:
                event, value = self.events.get_nowait()
                if event == "progress":
                    self.status.set(value)
                elif event == "ready":
                    self.busy = False
                    try:
                        self.start_server()
                    except Exception as error:
                        logging.exception("Server startup failed")
                        messagebox.showerror("启动失败", str(error)[:1500], parent=self.root)
                        self.close()
                        return
                elif event == "error":
                    self.busy = False
                    self.progress.stop()
                    self.status.set("素材准备失败，可重试下载或选择本地客户端。")
                    self.download.configure(state="normal")
                    self.import_button.configure(state="normal")
                    messagebox.showerror("素材准备失败", value[:1500], parent=self.root)
        except queue.Empty:
            pass
        if self.server is not None and str(self.open_button["state"]) == "disabled":
            if self.server.started:
                self.progress.stop()
                self.status.set(
                    f"工作台已运行：{self.url}\n关闭浏览器后服务继续运行；退出此窗口将停止服务。"
                )
                self.open_button.configure(state="normal")
                self.lock.publish(self.url)
                self.open_browser()
            elif self.thread is not None and (
                not self.thread.is_alive() or time.monotonic() - self.started_at > 60
            ):
                messagebox.showerror(
                    "启动失败", f"服务未能启动。请查看 {self.settings.log_dir}", parent=self.root
                )
                self.close()
                return
        self.root.after(100, self.poll)

    def open_browser(self) -> None:
        if not webbrowser.open(self.url):
            messagebox.showinfo("打开工作台", f"请在浏览器中打开：{self.url}", parent=self.root)

    def close(self) -> None:
        if self.busy:
            messagebox.showinfo("正在准备素材", "请等待素材处理完成后退出。", parent=self.root)
            return
        if self.server:
            self.server.should_exit = True
        self.status.set("正在停止服务…")
        self.root.after(100, self.finish_close)

    def finish_close(self) -> None:
        if self.thread is not None and self.thread.is_alive():
            self.root.after(100, self.finish_close)
            return
        if self.listener:
            self.listener.close()
        self.root.destroy()


def main() -> None:
    root = tk.Tk()
    root.withdraw()
    lock: InstanceLock | None = None
    try:
        directory = Path(sys.executable).parent if getattr(sys, "frozen", False) else Path.cwd()
        settings = desktop_settings(directory)
        settings.log_dir.mkdir(parents=True, exist_ok=True)
        if sys.stdout is None:
            sys.stdout = (settings.log_dir / "launcher.log").open(
                "a", encoding="utf-8", buffering=1
            )
        if sys.stderr is None:
            sys.stderr = sys.stdout
        try:
            lock = InstanceLock(settings.data_dir)
        except OSError:
            state = settings.data_dir / "desktop-instance.json"
            if state.is_file():
                url = str(json.loads(state.read_text(encoding="utf-8"))["url"])
                if url.startswith("http://127.0.0.1:"):
                    webbrowser.open(url)
            messagebox.showinfo(
                "工作台已启动", "同一数据目录已有启动窗口，请使用该窗口。", parent=root
            )
            return
        launcher = Launcher(root, settings, lock)
        root.deiconify()
        root.mainloop()
        del launcher
    except Exception as error:
        logging.exception("Launcher failed")
        messagebox.showerror("启动失败", str(error)[:1500], parent=root)
    finally:
        if lock:
            lock.close()
        with suppress(tk.TclError):
            root.destroy()
