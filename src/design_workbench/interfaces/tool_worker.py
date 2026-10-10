"""Isolated non-render tool invocation; the parent enforces its wall-time budget."""

import json
import sys
from typing import Any

from design_workbench.bootstrap import Workbench
from design_workbench.config import Settings
from design_workbench.domain.errors import WorkbenchError
from design_workbench.interfaces.tools import Tools


def main() -> None:
    tools: Tools | None = None
    try:
        body = json.loads(sys.stdin.buffer.read(5_000_000))
        tools = Tools(Workbench(Settings.model_validate(body["settings"])), isolated=False)
        result: dict[str, Any] = tools.call(body["name"], body["arguments"])
    except WorkbenchError as error:
        result = {"schema_version": 1, "error": error.as_dict()}
    except (OSError, ValueError) as error:
        result = {
            "schema_version": 1,
            "error": {"code": "TOOL_FAILED", "message": str(error)[:2000]},
        }
    finally:
        if tools is not None:
            tools.close()
    sys.stdout.buffer.write(json.dumps(result, ensure_ascii=False).encode())


if __name__ == "__main__":
    main()
