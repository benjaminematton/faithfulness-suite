#!/bin/bash
# Fully automated subscription-side live-web baseline.
# Runs become-expert headlessly (claude -p, subscription auth) on each pinned topic,
# then audits each session's brief against its own transcript. Only the judge costs
# API money (~$0.12/topic; key is read from ~/evals/.anthropic.env AT AUDIT TIME ONLY —
# do NOT export ANTHROPIC_API_KEY before running, or claude will bill the API instead of
# your subscription; this script strips it from the claude invocations regardless).
# Usage: tools/run_baseline.sh   (from the faithfulness-suite root, or anywhere)
set -uo pipefail
cd "$(dirname "$0")/.."
SUITE="$PWD"
WORK="$HOME/live-web-baseline"
export CLAUDE_CONFIG_DIR="$HOME/.claude-personal"
mkdir -p "$WORK"

TOPICS=(
  "observability for python batch pipelines"
  "adaptive retrieval for RAG systems"
  "startup accelerator data practices and cohort recording"
  "scraping data from Bubble.io apps when the Data API is off"
)

declare -a RESULTS
for T in "${TOPICS[@]}"; do
  echo "=== RUN: $T ==="
  if ! ( cd "$WORK" && env -u ANTHROPIC_API_KEY -u ANTHROPIC_AUTH_TOKEN claude -p \
      "/become-expert $T — I need working expertise before starting real work. Research thoroughly and save the field brief." \
      --allowedTools "WebSearch,WebFetch,Write,Read,Glob,Grep" \
      --output-format text | tail -3 ); then
    echo "!! claude run failed (auth?) — skipping audit for this topic"
    RESULTS+=("SKIPPED(run failed) | $T")
    continue
  fi
  echo "--- audit ---"
  set -a; . "$HOME/evals/.anthropic.env"; set +a
  if bash "$SUITE/tools/audit_latest.sh" "$WORK" "$CLAUDE_CONFIG_DIR" > "/tmp/audit-$(echo "$T" | tr ' ' '-' | cut -c1-30).json" 2>&1; then
    RESULTS+=("CLEAN  | $T")
  else
    rc=$?
    [ "$rc" -eq 1 ] && RESULTS+=("FINDINGS | $T") || RESULTS+=("INFRA($rc) | $T")
  fi
done

echo
echo "=== BASELINE SCOREBOARD ==="
printf '%s\n' "${RESULTS[@]}"
echo "(per-claim detail: /tmp/audit-*.json)"
