#!/usr/bin/env bash
set -e

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"
source .venv/bin/activate
TOKEN=$(python3 scripts/get_token.py)
echo "Token obtained: ${TOKEN:0:30}..."
exec python3 scripts/phase3_dummy_course_publish.py --token "$TOKEN"
