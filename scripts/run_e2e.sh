#!/usr/bin/env bash
set -e
cd /home/kali/proj/educorp
source .venv/bin/activate
TOKEN=$(python3 scripts/get_token.py)
echo "Token obtained: ${TOKEN:0:30}..."
exec python3 scripts/phase3_dummy_course_publish.py --token "$TOKEN"
