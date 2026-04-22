#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if command -v uv >/dev/null 2>&1; then
	RUNNER=(uv run python)
elif [ -x "$ROOT_DIR/.venv/bin/python" ]; then
	RUNNER=("$ROOT_DIR/.venv/bin/python")
elif [ -x "$ROOT_DIR/.venv/Scripts/python.exe" ]; then
	RUNNER=("$ROOT_DIR/.venv/Scripts/python.exe")
elif command -v python3 >/dev/null 2>&1; then
	RUNNER=(python3)
else
	echo "Missing required Python runner: install uv, create .venv, or add python3 to PATH" >&2
	exit 1
fi

TOKEN="$("${RUNNER[@]}" scripts/get_token.py)"
echo "Token obtained: ${TOKEN:0:30}..."
exec "${RUNNER[@]}" scripts/phase3_dummy_course_publish.py --token "$TOKEN"
