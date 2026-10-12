"""Shared entry point for the windowed launcher and console CLI."""

import multiprocessing
import runpy
import sys
from pathlib import Path

multiprocessing.freeze_support()

# Frozen Python ignores PYTHONUTF8; keep CLI JSON readable under Chinese Windows.
for stream in (sys.stdin, sys.stdout, sys.stderr):
    if stream is not None:
        stream.reconfigure(encoding="utf-8")

if len(sys.argv) >= 3 and sys.argv[1] == "-m":
    module = sys.argv[2]
    if module not in {
        "design_workbench.interfaces.tool_worker",
        "design_workbench.adapters.rendering.capture_worker",
    }:
        raise SystemExit("Unsupported worker module")
    sys.argv = [module, *sys.argv[3:]]
    runpy.run_module(module, run_name="__main__")
elif Path(sys.executable).stem == "WorkbenchCLI":
    from design_workbench.interfaces.cli import app

    app()
else:
    from design_workbench.interfaces.desktop import main

    main()
