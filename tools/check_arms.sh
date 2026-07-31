#!/bin/bash
# Asserts the two seasons arms are identical except for the one thing under test.
#
# The whole A/B rests on this: an uncontrolled scaffold difference between arms makes the
# contrast uninterpretable (controlled studies report 8-28pp same-model swings from scaffold
# choice alone). instruction.md is the variable under test. task.toml must differ ONLY in the
# [task] name line, or job outputs are not separable.
#
# Exit 0 = arms are clean. Exit 1 = do not run the experiment.
set -uo pipefail
cd "$(dirname "$0")/.."

A=seasons-axial-tilt
B=seasons-axial-tilt-priorrule

fail=0

for d in "$A" "$B"; do
  [ -d "$d" ] || { echo "MISSING ARM: $d"; exit 1; }
done

# require_pair NAME
# Confirms NAME exists as a regular file in both arms before anything is allowed
# to compare it. A missing file is always a failure — never a silent pass. Prints
# one MISSING line per side that lacks the file and sets fail=1. Returns 0 only
# when both sides have the file.
require_pair() {
  local name="$1"
  local ok=0
  if [ ! -f "$A/$name" ]; then
    echo "MISSING: $A/$name"
    ok=1
  fi
  if [ ! -f "$B/$name" ]; then
    echo "MISSING: $B/$name"
    ok=1
  fi
  if [ "$ok" -ne 0 ]; then
    fail=1
    return 1
  fi
  return 0
}

echo "== everything except instruction.md and task.toml must be identical =="
diff_out=$(diff -r -x 'instruction.md' -x 'task.toml' -x '__pycache__' -x '.pytest_cache' \
  "$A" "$B" 2>&1)
if [ -n "$diff_out" ]; then
  echo "ARMS DIFFER — experiment invalid:"
  echo "$diff_out"
  fail=1
else
  echo "ok"
fi

echo "== task.toml may differ ONLY in the [task] name line =="
if require_pair task.toml; then
  toml_diff=$(diff <(grep -v '^name = ' "$A/task.toml" 2>&1) \
                   <(grep -v '^name = ' "$B/task.toml" 2>&1) 2>&1)
  if [ -n "$toml_diff" ]; then
    echo "task.toml differs beyond the name line:"
    echo "$toml_diff"
    fail=1
  else
    echo "ok"
  fi
else
  echo "task.toml comparison impossible — cannot confirm arms are separable"
fi

echo "== instruction.md must actually differ (or there is no experiment) =="
if require_pair instruction.md; then
  diff_err=$(diff -q "$A/instruction.md" "$B/instruction.md" 2>&1 >/dev/null)
  rc=$?
  case "$rc" in
    0)
      echo "instruction.md is IDENTICAL between arms — the control arm was never reverted"
      fail=1
      ;;
    1)
      echo "ok ($(diff "$A/instruction.md" "$B/instruction.md" | grep -c '^[<>]') differing lines)"
      ;;
    *)
      echo "instruction.md comparison impossible (diff exit $rc): $diff_err"
      fail=1
      ;;
  esac
else
  echo "instruction.md comparison impossible — cannot confirm the control arm was reverted"
fi

if [ "$fail" -ne 0 ]; then
  echo
  echo "GUARD FAILED — do not run the arms."
  exit 1
fi
echo
echo "== arms clean =="
exit 0
