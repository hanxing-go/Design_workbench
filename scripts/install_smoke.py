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
    parser.add_argument("--extras", default="gui", help="Comma-separated wheel extras to install")
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
            [str(binary), "-m", "pip", "install", f"{wheel}[{args.extras}]"],
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
assert (root/'static/capture.html').is_file()
assert list((root/'static/assets').glob('*.js'))
assert len(Catalog().blocks)==1003
scene,report=Litematic(Catalog()).read(Path('portable.litematic').read_bytes())
assert scene.summary()['blocks']==18
print('Wheel frontend/catalog/create/edit/export verified')
from design_workbench.bootstrap import Workbench
from design_workbench.config import Settings
from design_workbench.interfaces.tools import Tools
from design_workbench.application.design_contracts import CandidateOpen
control=Tools(Workbench(Settings.load()), isolated=False)
project=control.call('project.create',{'request_id':'install-controls','request':{'name':'Installed controls'}})['project_id']
task=control.call('design.start',{'project':project,'request_id':'install-task','expected_revision':0,'prompt':'Installed persistent task'})
run_id=task['run_id']
assert task['usage']['source']==''
proposal=control.call('design.propose',{'run_id':run_id,'request_id':'install-propose','request':{'expected_revision':0,'request_id':'edit','operations':[{'op':'fill','bounds':{'low':[0,0,0],'high':[1,1,1]},'state':{'name':'stone'}}]},'explanation':'Preview before applying'})
assert proposal['status']=='awaiting_approval'
assert control.workbench.service(control.project_path(project)).summary()['revision']==0
saved=control.call('candidate.save',{'run_id':run_id,'request_id':'install-candidate','expected_revision':0,'name':'Saved candidate'})
assert saved['sha256']
control.call('design.cancel',{'run_id':run_id,'request_id':'install-cancel'})
control.close()
control=Tools(Workbench(Settings.load()), isolated=False)
assert control.call('design.status',{'run_id':run_id})['status']=='cancelled'
clone=control.designs.open_candidate(run_id,saved['candidate_id'],CandidateOpen(request_id='open'))
assert clone['project_id']!=project
control.close()
print('Installed design task, approval gate, persistence and candidate fork verified')
"""
        subprocess.run([str(binary), "-c", validate], check=True, env=env, cwd=directory)
        descriptions = subprocess.run(
            [*command, "tools"], check=True, capture_output=True, text=True, env=env, cwd=directory
        )
        assert {"scene.commit_edit", "design.start", "candidate.save"} <= {
            item["name"] for item in json.loads(descriptions.stdout)["tools"]
        }
        p6_check = False
        if "ai" in args.extras.split(","):
            protocol_check = """
import asyncio, sys
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
async def check():
    async with stdio_client(StdioServerParameters(command=sys.executable,args=['-m','design_workbench.interfaces.cli','mcp'])) as (read,write), ClientSession(read,write) as session:
        await session.initialize()
        assert {"scene.commit_edit", "design.start", "candidate.save"} <= {item.name for item in (await session.list_tools()).tools}
        result=await session.call_tool('catalog.search',{'query':'oak','limit':1})
        assert not result.isError and result.structuredContent['items']
asyncio.run(check())
"""
            subprocess.run([str(binary), "-c", protocol_check], check=True, env=env, cwd=directory)
            p6_check = True
        report = {
            "wheel": wheel.name,
            "isolated_install": True,
            "installed_path": check.stdout.strip(),
            "source_checkout_required": False,
            "create_edit_export": True,
            "frontend_and_registry_in_wheel": True,
            "capture_frontend_and_tool_schemas_in_wheel": True,
            "design_controls_and_candidates_in_wheel": True,
            "installed_extras": args.extras,
            "mcp_stdio_in_clean_environment": p6_check,
        }
        report_path = ROOT / args.report
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(json.dumps(report))


if __name__ == "__main__":
    main()
