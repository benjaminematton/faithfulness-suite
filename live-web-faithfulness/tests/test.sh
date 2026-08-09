#!/bin/bash
# Verifier: audit the brief against the agent's own session transcript.
# Reward: auditor exit 0 -> 1; exit 1 -> 0; anything else -> infra, no score.
set -uo pipefail
mkdir -p /logs/verifier

TRANSCRIPT=$(ls -S /logs/agent/sessions/projects/*/*.jsonl 2>/dev/null | head -1)
if [ -z "${TRANSCRIPT:-}" ]; then
  TRANSCRIPT=$(find / -name "*.jsonl" -path "*sessions/projects*" 2>/dev/null | head -1)
fi
if [ -z "${TRANSCRIPT:-}" ] || [ ! -f /app/field-brief.md ]; then
  echo "INFRA: transcript or brief missing" >&2; exit 90
fi

cd /tests
uv run --no-project --with anthropic==0.120.0 \
  python3 -m auditor.audit --brief /app/field-brief.md --transcript "$TRANSCRIPT" --json \
  > /logs/verifier/audit.json
rc=$?
cat /logs/verifier/audit.json
if [ "$rc" -eq 0 ]; then echo 1 > /logs/verifier/reward.txt
elif [ "$rc" -eq 1 ]; then echo 0 > /logs/verifier/reward.txt
else echo "INFRA: auditor exited $rc" >&2; exit "$rc"; fi
