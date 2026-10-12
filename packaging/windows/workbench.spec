from pathlib import Path
import sys
from PyInstaller.utils.hooks import collect_data_files, copy_metadata

root = Path(SPECPATH).parents[1]
data = collect_data_files('design_workbench') + copy_metadata('minecraft-design-workbench', recursive=True)
data.append((str(Path(sys.base_prefix) / 'LICENSE.txt'), 'licenses/python'))
a = Analysis(
    [str(root / 'packaging/windows/entry.py')],
    pathex=[str(root / 'src')],
    datas=data,
    hiddenimports=[
        'design_workbench.interfaces.desktop',
        'design_workbench.interfaces.cli',
        'design_workbench.interfaces.tool_worker',
        'design_workbench.adapters.rendering.capture_worker',
        'uvicorn.logging', 'uvicorn.loops.asyncio',
        'uvicorn.protocols.http.h11_impl', 'uvicorn.lifespan.on',
    ],
    excludes=['pytest', 'mypy', 'ruff', 'playwright', 'mcp'],
)
pyz = PYZ(a.pure)
gui = EXE(pyz, a.scripts, [], exclude_binaries=True, name='DesignWorkbench', console=False)
cli = EXE(pyz, a.scripts, [], exclude_binaries=True, name='WorkbenchCLI', console=True)
bundle = COLLECT(gui, cli, a.binaries, a.datas, name='DesignWorkbench')
