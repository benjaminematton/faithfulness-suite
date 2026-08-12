#!/usr/bin/env bash
# Retro-run the landing gate against the REAL local-only mining fixtures.
#
# Ground truth (docs/2026-08-09-mining-report.md, auditor/fixtures/README.md):
#   aug03  MUST block (exit 1) — F1 in all its sub-forms, ~11:1 search:fetch
#   aug08  MUST clear (exit 0) — fully compliant under the newest skill
#
# The fixtures are personal transcripts and are never committed, so this cannot run in CI
# or from a Claude session. It is the load-bearing check for the gate; the committed
# synthetic equivalents (auditor/tests/test_gate_fixtures.py) only pin the shape.
#
# Usage: bash tools/gate_retro.sh [FIXTURE_DIR]     # default auditor/fixtures
set -uo pipefail
cd "$(dirname "$0")/.."
DIR="${1:-auditor/fixtures}"
export PYTHONPATH="${PYTHONPATH:-.}"

fail=0
run() {  # run <name> <expected_exit>
  local name="$1" want="$2"
  local brief="$DIR/$name-brief.md" tr="$DIR/$name-transcript.jsonl"
  if [[ ! -f "$brief" || ! -f "$tr" ]]; then
    echo "SKIP $name — fixture not present (local-only; see $DIR/README.md)"
    return
  fi
  python3 -m auditor.gate_cli --log "$brief" --transcript "$tr"
  local got=$?
  if [[ "$got" == "3" ]]; then
    echo "INFRA $name — exit 3, not a verdict"; fail=1; return
  fi
  if [[ "$got" == "$want" ]]; then
    echo "OK   $name — exit $got (expected $want)"
  else
    echo "FAIL $name — exit $got, expected $want"; fail=1
  fi
  echo
}

run aug03 1
run aug08 0

if [[ "$fail" == "1" ]]; then
  echo "gate retro: FAILED — do not build the eval arms until this passes"
  exit 1
fi
echo "gate retro: all present fixtures behaved as documented"
