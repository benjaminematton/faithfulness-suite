#!/usr/bin/env bash
# Vendor the deterministic core FROM become-expert-skill INTO auditor/.
#
# Ownership: the skill owns its runtime. brief/checks/transcript/urlnorm/gate/gate_cli are
# product code that runs during a real research session, so they are edited in
# become-expert-skill/scripts/auditor/ and copied here. judge.py, report.py and audit.py are
# eval-only and are owned by THIS repo -- never overwritten by this script.
#
# Same pattern as tools/sync_auditor.sh, one level up: skill -> suite -> live-web task.
# After running this, run tools/sync_auditor.sh to push the change into the vendored
# verifier copy as well.
#
# Usage: bash tools/sync_gate_core.sh [PATH_TO_become-expert-skill]
set -euo pipefail
cd "$(dirname "$0")/.."
SRC="${1:-../become-expert-skill}/scripts/auditor"

if [[ ! -d "$SRC" ]]; then
  echo "core not found at $SRC — pass the path to your become-expert-skill checkout" >&2
  exit 2
fi

CORE=(urlnorm.py transcript.py brief.py checks.py gate.py gate_cli.py)
for f in "${CORE[@]}"; do
  [[ -f "$SRC/$f" ]] || { echo "missing $SRC/$f" >&2; exit 2; }
  cp "$SRC/$f" "auditor/$f"
done

{
  echo "# Vendored core — DO NOT EDIT HERE"
  echo
  echo "Source of truth: \`become-expert-skill/scripts/auditor/\`. These files are product"
  echo "runtime code; edit them there and re-run \`tools/sync_gate_core.sh\`. Local edits are"
  echo "detected by \`auditor/tests/test_vendor_drift.py\`."
  echo
  echo "Synced from: $SRC"
  echo
  echo "| file | sha256 |"
  echo "|---|---|"
  for f in "${CORE[@]}"; do
    echo "| $f | $(sha256sum "auditor/$f" | cut -c1-64) |"
  done
} > auditor/CORE-VENDORED.md

echo "vendored ${#CORE[@]} core files; manifest written to auditor/CORE-VENDORED.md"
echo "next: bash tools/sync_auditor.sh"
