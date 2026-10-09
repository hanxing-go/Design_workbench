"""Record P4 baseline before browser editing performance acceptance."""

import json
import platform
import statistics
import time
from pathlib import Path

from design_workbench.adapters.rendering.packets import render_packet
from design_workbench.application.contracts import EditRequest, HistoryRequest
from design_workbench.bootstrap import Workbench
from design_workbench.config import Settings

ROOT = Path(__file__).parents[1]


def main() -> None:
    workbench = Workbench(Settings.load(ROOT / "config.example.toml"))
    service = workbench.service(ROOT / ".local/data/church.dwbench")
    measurements: dict[str, list[float]] = {}

    def measure(name: str, action: object) -> object:
        started = time.perf_counter()
        value = action()  # type: ignore[operator]
        measurements.setdefault(name, []).append((time.perf_counter() - started) * 1000)
        return value

    scene = measure("load_ms", service.repository.load)
    assert workbench.pack is not None
    packet = measure(
        "render_packet_ms", lambda: render_packet(scene, workbench.catalog, workbench.pack)
    )
    measure("export_ms", lambda: service.export_asset(scene.revision))
    for index in range(3):
        state = "stone" if index % 2 == 0 else "oak_planks"
        revision = service.summary()["revision"]
        request = EditRequest.model_validate(
            {
                "expected_revision": revision,
                "request_id": f"baseline-{time.time_ns()}",
                "operations": [
                    {
                        "op": "fill",
                        "bounds": {"low": [90, 0, 0], "high": [99, 9, 9]},
                        "state": {"name": state},
                        "group": "benchmark",
                    }
                ],
            }
        )
        measure("edit_1000_ms", lambda request=request: service.edit(request))
        measure("save_reopen_ms", service.repository.load)
        measure(
            "undo_ms",
            lambda revision=revision: service.history(
                "undo",
                HistoryRequest(expected_revision=revision + 1, request_id=f"undo-{time.time_ns()}"),
            ),
        )
    report = {
        "stage": "P4",
        "machine": {
            "os": platform.platform(),
            "processor": platform.processor(),
            "python": platform.python_version(),
        },
        "fixture": {
            "name": "杜鹃教堂",
            "blocks": scene.summary()["blocks"],
            "data_version": scene.data_version,
            "resource_hash": workbench.pack.manifest["bundle_hash"],
        },
        "measurements": measurements,
        "medians_ms": {key: statistics.median(values) for key, values in measurements.items()},
        "packet_bytes": len(json.dumps(packet)),
        "p5_gates": {
            "browser_initial_load_ms": 15000,
            "edit_1000_total_ms": 3000,
            "save_reopen_ms": 2000,
            "export_ms": 3000,
            "camera_frame_p95_ms": 100,
            "local_edit_must_transfer_fewer_chunks_than_full_scene": True,
        },
        "gate_scope": "此 Windows 机器、官方 1.20.1 静态资源、36,094 格教堂；不承诺低配设备",
    }
    output = ROOT / "artifacts/p4-baseline.json"
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(
        json.dumps(
            {key: value for key, value in report.items() if key != "measurements"},
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
