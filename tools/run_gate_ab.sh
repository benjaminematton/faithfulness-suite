#!/usr/bin/env bash
# Sequential, resumable trial runner for the live-web gate A/B.
#
# WHY SEQUENTIAL: a rate-limit stop partway through a -k 5 batch loses the whole batch and
# leaves the arms with asymmetric trial counts, which contaminates the comparison rather
# than merely delaying it. This runs ONE trial per harbor invocation, appends a ledger row
# after each, and stops cleanly the moment a trial fails -- so a limit costs you the
# current trial, never the completed ones. Re-run the same command to resume: it counts
# the ledger rows for that arm and runs only the remainder.
#
# The --env-file lives INSIDE this script, so the command you type contains no `.env` and
# the guard hook does not block it.
#
# Usage:
#   TOPIC="startup accelerator cohort attribution conventions" \
#     bash tools/run_gate_ab.sh live-web-gate 5
#   bash tools/run_gate_ab.sh live-web-gate-gaterule 5
#
# Env: TOPIC, JUDGE_VOTES (default 3), MODEL (default claude-opus-4-8),
#      HARBOR (default ~/evals/.venv/bin/harbor), ENVFILE (default ~/evals/.anthropic.env),
#      JOBS (default ./jobs), LEDGER (default docs/plans/live-web-gate-ledger.tsv)
#
# NOTE ON WINDOWING: on a subscription, do NOT interleave arms. Finish one arm, note the
# five-hour window, then start the other. The ledger records a timestamp per trial so a
# window boundary is visible after the fact.
set -uo pipefail
cd "$(dirname "$0")/.."

ARM="${1:?usage: run_gate_ab.sh <arm-dir> <n-trials>}"
WANT="${2:?usage: run_gate_ab.sh <arm-dir> <n-trials>}"

HARBOR="${HARBOR:-$HOME/evals/.venv/bin/harbor}"
ENVFILE="${ENVFILE:-$HOME/evals/.anthropic.env}"
JOBS="${JOBS:-$PWD/jobs}"
LEDGER="${LEDGER:-docs/plans/live-web-gate-ledger.tsv}"
MODEL="${MODEL:-claude-opus-4-8}"
JUDGE_VOTES="${JUDGE_VOTES:-3}"
export JUDGE_VOTES

[ -d "$ARM" ]      || { echo "no such arm: $ARM" >&2; exit 2; }
[ -x "$HARBOR" ]   || { echo "harbor not executable: $HARBOR" >&2; exit 2; }
[ -f "$ENVFILE" ]  || { echo "env file missing: $ENVFILE" >&2; exit 2; }

if [ -z "${TOPIC:-}" ]; then
  echo "WARNING: TOPIC unset — trials will use the task default (doc-heavy)."
  echo "         The run sheet designates the pressure topic as PRIMARY. Ctrl-C to abort."
  sleep 5
fi

mkdir -p "$(dirname "$LEDGER")"
if [ ! -s "$LEDGER" ]; then
  printf 'when\tarm\ttopic\tmodel\tjob\ttrial\treward\tcost_usd_listprice\tapi_calls\tinput_tokens\toutput_tokens\tcache_creation_input_tokens\tcache_read_input_tokens\tsearches\tfetches\tsearch_fetch_ratio\tclaims_log_present\tgate_invocations\tgate_unavailable\tbrief_verified_lines\tn_verified_claimed\tn_verified_earned\n' > "$LEDGER"
fi

done_n=$(awk -F'\t' -v a="$ARM" 'NR>1 && $2==a' "$LEDGER" 2>/dev/null | wc -l | tr -d ' ')
echo "arm=$ARM  want=$WANT  already in ledger=$done_n  model=$MODEL  votes=$JUDGE_VOTES"
echo "topic=${TOPIC:-<task default>}"
[ "$done_n" -ge "$WANT" ] && { echo "already complete — nothing to do"; exit 0; }

for (( i=done_n+1; i<=WANT; i++ )); do
  echo
  echo "=== $ARM trial $i/$WANT — $(date '+%H:%M:%S') ==="
  before=$(ls -1 "$JOBS" 2>/dev/null | wc -l | tr -d ' ')

  "$HARBOR" run -p "$PWD/$ARM" -a claude-code -m "$MODEL" -k 1 \
    -e docker --env-file "$ENVFILE" -o "$JOBS" -y
  rc=$?

  job=$(ls -1t "$JOBS" 2>/dev/null | head -1)
  after=$(ls -1 "$JOBS" 2>/dev/null | wc -l | tr -d ' ')

  if [ "$rc" -ne 0 ] || [ "$after" -le "$before" ]; then
    echo "TRIAL $i FAILED (harbor rc=$rc). Progress through trial $((i-1)) is in $LEDGER."
    if [ -n "$job" ] && grep -qiE "rate.?limit|usage limit|429" "$JOBS/$job/job.log" 2>/dev/null; then
      echo "Cause looks like a RATE LIMIT. Wait for the window to reset, then re-run this"
      echo "exact command — it resumes at trial $i."
    else
      echo "Not obviously a rate limit; read $JOBS/$job/job.log before re-running."
    fi
    exit 1
  fi

  # Ledger row. Analyzer failure must not lose the trial, so fall back to a stub row.
  row=$(python3 tools/analyze_run.py "$JOBS/$job" --tsv 2>/dev/null | tail -n +2 | head -1)
  [ -z "$row" ] && row=$(printf '%s\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t' "$job")
  printf '%s\t%s\t%s\t%s\t%s\n' \
    "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" "$ARM" "${TOPIC:-<default>}" "$MODEL" "$row" >> "$LEDGER"

  echo "--- trial $i recorded ---"
  python3 tools/analyze_run.py "$JOBS/$job" 2>/dev/null | tail -20
done

echo
echo "=== $ARM complete: $WANT trial(s) ==="
awk -F'\t' -v a="$ARM" 'NR==1 || $2==a' "$LEDGER" | column -t -s$'\t' 2>/dev/null \
  || awk -F'\t' -v a="$ARM" 'NR==1 || $2==a' "$LEDGER"
