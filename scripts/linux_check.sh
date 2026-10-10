#!/usr/bin/env bash
set -eu
project_root="$(cd "$(dirname "$0")/.." && pwd)"
verification_dir="$(mktemp -d /tmp/design-workbench-check.XXXXXX)"
trap 'rm -rf -- "$verification_dir"' EXIT
curl -fsSL --retry 2 https://github.com/astral-sh/uv/releases/download/0.12.24/uv-x86_64-unknown-linux-gnu.tar.gz -o "$verification_dir/uv.tar.gz"
tar -xzf "$verification_dir/uv.tar.gz" -C "$verification_dir"
verification_uv="$verification_dir/uv-x86_64-unknown-linux-gnu/uv"
export UV_PROJECT_ENVIRONMENT="$verification_dir/environment"
export UV_LINK_MODE=copy
cd "$project_root"
"$verification_uv" sync --locked --extra gui --extra ai --extra render --python 3.12
"$verification_uv" run --no-sync pytest -m 'not e2e and not resources' -q --junitxml=artifacts/p6/pytest-linux.xml
"$verification_uv" run --no-sync mypy
"$verification_uv" run --no-sync ruff check .
"$verification_uv" run --no-sync ruff format --check .
"$verification_uv" build
"$verification_uv" run --no-sync python scripts/install_smoke.py --extras gui,ai,render --report artifacts/p6/install-smoke-linux.json
