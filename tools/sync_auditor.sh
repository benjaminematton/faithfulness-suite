#!/bin/bash
# Vendor auditor/ into the live-web task's tests/ so the verifier container is
# self-contained. Run after any auditor change, before running the task.
set -euo pipefail
cd "$(dirname "$0")/.."
rm -rf live-web-faithfulness/tests/auditor
mkdir -p live-web-faithfulness/tests/auditor
cp auditor/*.py live-web-faithfulness/tests/auditor/
touch live-web-faithfulness/tests/auditor/__init__.py
echo "synced $(ls live-web-faithfulness/tests/auditor | wc -l | tr -d ' ') files"
