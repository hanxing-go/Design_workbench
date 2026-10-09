"""Original-vs-cached backend benchmark with edits only to disposable copies.

Example::

    python scripts/benchmark_render_cache.py --baseline-ref 193f8f1 \
        --project .local/data/projects/church.dwbench \
        --project .local/performance/data/projects/asset_ivory_castle_upper_105102.dwbench

Measures Python projection assembly separately from HTTP serialization/browser
work. Resources are warmed before timing. Every full/delta result is compared
against the source at the chosen Git revision. All samples and baseline source
are saved in artifacts/performance; source projects are read-only.
"""

import argparse
import json
import math
import platform
import sqlite3
import statistics
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from functools import partial
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from design_workbench.adapters.rendering.cache import RenderCache  # noqa: E402
from design_workbench.adapters.rendering.packets import render_chunk  # noqa: E402
from design_workbench.adapters.storage.sqlite import SqliteStore, decode_chunk  # noqa: E402
from design_workbench.application.contracts import EditRequest  # noqa: E402
from design_workbench.bootstrap import Workbench  # noqa: E402
from design_workbench.config import Settings  # noqa: E402


def distribution(samples):
    values = sorted(samples)
    return {
        "samples": samples,
        "p50_ms": statistics.median(values),
        "p95_ms": values[math.ceil(len(values) * 0.95) - 1],
        "max_ms": values[-1],
    }


def measure(action, repeats=7):
    times = []
    last = None
    for _ in range(repeats):
        start = time.perf_counter()
        last = action()
        times.append((time.perf_counter() - start) * 1000)
    return distribution(times), last


def legacy_projection(repository, renderer, catalog, pack, known):
    return renderer(repository.load(), catalog, pack, known, repository.attachment())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=ROOT / "config.example.toml")
    parser.add_argument("--baseline-ref", default="193f8f1")
    parser.add_argument("--project", type=Path, action="append", required=True)
    parser.add_argument("--samples", type=int, default=7)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.samples < 1:
        parser.error("--samples must be positive")
    workbench = Workbench(Settings.load(args.config.resolve()))
    pack = workbench.pack
    if pack is None:
        parser.error("resources are not configured")
    namespace = {
        "__name__": "design_workbench.adapters.rendering.baseline_packets",
        "__package__": "design_workbench.adapters.rendering",
    }
    original_source = subprocess.run(
        ["git", "show", f"{args.baseline_ref}:src/design_workbench/adapters/rendering/packets.py"],
        cwd=ROOT,
        check=True,
        text=True,
        capture_output=True,
    ).stdout
    exec(compile(original_source, f"{args.baseline_ref}:packets.py", "exec"), namespace)
    old_render = namespace["render_packet"]
    timestamp = datetime.now(timezone(timedelta(hours=8))).strftime("%Y%m%d-%H%M%S-%f")
    directory = (args.output or ROOT / f"artifacts/performance/{timestamp}-backend").resolve()
    sources = [source.resolve() for source in args.project]
    if any(source.is_relative_to(directory) for source in sources):
        parser.error("source projects must be outside the disposable output directory")
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "baseline_packets.py").write_text(original_source, encoding="utf-8")
    report = {
        "baseline_commit": args.baseline_ref,
        "environment": {"os": platform.platform(), "python": platform.python_version()},
        "resource_hash": pack.manifest["bundle_hash"],
        "scope": "Python methods; excludes HTTP serialization and browser work; warmed resources",
        "samples": [],
    }
    for index, source in enumerate(sources):
        if not source.is_file():
            parser.error(f"project does not exist: {source}")
        path = directory / f"{index}-{source.name}"
        with (
            sqlite3.connect(source.as_uri() + "?mode=ro", uri=True) as original,
            sqlite3.connect(path) as copied,
        ):
            original.backup(copied)
        repository = SqliteStore(path)
        service = workbench.service(path)
        scene = repository.load()
        legacy = old_render(scene, workbench.catalog, pack, source=repository.attachment())
        cache = RenderCache()
        initial_start = time.perf_counter()
        initial = cache.render(path, workbench.catalog, pack)
        initial_ms = (time.perf_counter() - initial_start) * 1000
        assert initial["chunks"] == legacy["chunks"] and initial["models"] == legacy["models"]
        assert initial["summary"] == legacy["summary"]
        sample = {
            "source": str(source),
            "name": scene.name,
            "blocks": scene.summary()["blocks"],
            "chunks": len(legacy["chunks"]),
            "new_initial_cache_ms": initial_ms,
            "equivalent_full_packet": True,
        }
        sample["old_unchanged_load_render_ms"], _ = measure(
            partial(
                legacy_projection,
                repository,
                old_render,
                workbench.catalog,
                pack,
                legacy["chunk_versions"],
            ),
            args.samples,
        )
        sample["new_unchanged_cache_ms"], _ = measure(
            partial(cache.render, path, workbench.catalog, pack, initial["chunk_versions"]),
            args.samples,
        )
        sample["old_summary_ms"], _ = measure(service.summary, args.samples)
        sample["new_summary_ms"], _ = measure(partial(cache.summary, path), args.samples)
        projection = cache._entries[path.resolve()]
        sample["cache_estimated_serialized_bytes"] = projection.byte_size
        sample["cache_stored_cells"] = projection.cells
        known = initial["chunk_versions"]
        legacy_known = legacy["chunk_versions"]
        positions = [
            p
            for p in sorted(scene.cells)
            if not scene.cells[p].state.is_air and p not in scene.protected
        ]
        for count in (1, 100, 1000):
            chosen = positions[:count]
            state = "stone" if count != 100 else "oak_planks"
            request = EditRequest.model_validate(
                {
                    "expected_revision": service.summary()["revision"],
                    "request_id": f"backend-{count}",
                    "operations": [
                        {
                            "op": "set",
                            "blocks": [{"position": p, "state": {"name": state}} for p in chosen],
                        }
                    ],
                }
            )
            start = time.perf_counter()
            response = service.edit(request)
            edit_ms = (time.perf_counter() - start) * 1000
            start = time.perf_counter()
            with (
                patch(
                    "design_workbench.adapters.rendering.cache.decode_chunk", wraps=decode_chunk
                ) as decoded,
                patch(
                    "design_workbench.adapters.rendering.cache.render_chunk", wraps=render_chunk
                ) as rendered,
            ):
                delta = cache.render(path, workbench.catalog, pack, known)
            incremental_ms = (time.perf_counter() - start) * 1000
            old_ms, old_delta = measure(
                partial(
                    legacy_projection, repository, old_render, workbench.catalog, pack, legacy_known
                ),
                repeats=3,
            )
            assert (
                delta["chunks"] == old_delta["chunks"]
                and delta["models"] == old_delta["models"]
                and delta["summary"] == old_delta["summary"]
            )
            sample[f"edit_{count}"] = {
                "edit_save_ms": edit_ms,
                "changed_cells": response["changed"],
                "changed_storage_chunks": len(response["changed_chunks"]),
                "new_incremental_render_ms": incremental_ms,
                "decoded_chunks": decoded.call_count,
                "rebuilt_render_chunks": rendered.call_count,
                "transported_chunks": len(delta["chunks"]),
                "old_incremental_render_ms": old_ms,
                "equivalent_delta": True,
            }
            known, legacy_known = delta["chunk_versions"], old_delta["chunk_versions"]
        report["samples"].append(sample)
        cache.close()
        print(json.dumps(sample, ensure_ascii=False), flush=True)
    (directory / "results.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )


if __name__ == "__main__":
    main()
