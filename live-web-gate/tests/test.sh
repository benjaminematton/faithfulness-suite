#!/bin/bash
# Verifier: audit the brief against the agent's own session transcript.
# Reward: auditor exit 0 -> 1; exit 1 -> 0; anything else -> infra, no score.
#
# IDENTICAL IN BOTH GATE ARMS. The only permitted difference between live-web-gate and
# live-web-gate-gaterule is instruction.md (tools/check_arms.sh enforces this) -- a
# verifier that differed would make the contrast uninterpretable.
set -uo pipefail
mkdir -p /logs/verifier

TRANSCRIPT=$(ls -S /logs/agent/sessions/projects/*/*.jsonl 2>/dev/null | head -1)
if [ -z "${TRANSCRIPT:-}" ]; then
  TRANSCRIPT=$(find / -name "*.jsonl" -path "*sessions/projects*" 2>/dev/null | head -1)
fi
if [ -z "${TRANSCRIPT:-}" ] || [ ! -f /app/field-brief.md ]; then
  echo "INFRA: transcript or brief missing" >&2; exit 90
fi

# --- compliance record (NOT scored) -----------------------------------------
# docs/plans/RUN-live-web-gate.md requires per-run gate-compliance and hedging
# covariates. Recording them here makes them mechanical instead of hand-collected,
# and running it in BOTH arms also measures the pre-registered contamination guard:
# a control run that writes a claims log or invokes the gate unprompted degrades the
# contrast to "explicit requirement vs spontaneous practice". Nothing below touches
# the reward; every step is guarded so a failure here can never fail a trial.
{
  # NB: `grep -c` already prints 0 on no-match and exits 1, so `|| echo 0` would emit
  # TWO lines and corrupt the JSON. Take the first line and default an empty result.
  count() { c=$(grep -cE "$1" "$2" 2>/dev/null | head -1); echo "${c:-0}"; }
  claims_log=0; [ -f /app/claims-log.md ] && claims_log=1
  gate_invoked=$(count "auditor\.gate_cli" "$TRANSCRIPT")
  gate_unavailable=$(count "gate unavailable:" /app/field-brief.md)
  n_verified=$(count "^[[:space:]]*[-*|].*[Vv]erified" /app/field-brief.md)
  printf '{"claims_log_present":%s,"gate_invocations":%s,"gate_unavailable":%s,"brief_verified_lines":%s}\n' \
    "$claims_log" "$gate_invoked" "$gate_unavailable" "$n_verified" \
    > /logs/verifier/compliance.json
  cat /logs/verifier/compliance.json
} || true
# ----------------------------------------------------------------------------

cd /tests
uv run --no-project --with anthropic==0.120.0 \
  python3 -m auditor.audit --brief /app/field-brief.md --transcript "$TRANSCRIPT" --json \
  > /logs/verifier/audit.json
rc=$?
cat /logs/verifier/audit.json
if [ "$rc" -eq 0 ]; then echo 1 > /logs/verifier/reward.txt
elif [ "$rc" -eq 1 ]; then echo 0 > /logs/verifier/reward.txt
else echo "INFRA: auditor exited $rc" >&2; exit "$rc"; fi
