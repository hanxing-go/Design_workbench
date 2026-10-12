"""Commands for isolated workers in source and frozen distributions."""

import sys
from pathlib import Path


def worker_command(module: str, *arguments: str) -> list[str]:
    executable = sys.executable
    if getattr(sys, "frozen", False):
        executable = str(Path(executable).with_name("WorkbenchCLI.exe"))
    return [executable, "-m", module, *arguments]
