#!/bin/bash
# Runs the faithfulness tests and writes the reward. Copied to /tests/test.sh and run in
# the same container the agent used. uv + curl are pre-baked into the image (Dockerfile),
# so no network apt install happens here.
#
# Reward contract (must distinguish agent failure from infra failure):
#   pytest 0 -> reward 1   (faithful brief)
#   pytest 1 -> reward 0   (unfaithful / missing brief = agent failure)
#   otherwise -> NO reward written, exit non-zero  (judge/infra failure; test_outputs.py
#                exits 3 on a judge/corpus error, dep resolution exits 90 above, and a
#                pytest collection/internal error also lands here rather than as reward 0)
set -uo pipefail
mkdir -p /logs/verifier

# Pre-resolve deps first so a PyPI/resolution/network failure is an INFRA error (exit 90
# -> no score), NOT an agent failure (reward 0). This also warms the uv cache, so the
# pytest run below needs no network and only pytest's own exit code maps to a reward.
if ! uv run --no-project \
      --with pytest==8.4.1 \
      --with pytest-json-ctrf==0.3.5 \
      --with anthropic==0.120.0 \
      python3 -c 'import pytest, anthropic' >/dev/null 2>&1; then
  echo "INFRA: verifier dependency resolution failed (uv/PyPI) — no score written" >&2
  exit 90
fi

# Judge (default) needs ANTHROPIC_API_KEY (injected via --env-file). Set
# VERIFIER_JUDGE=stub:pass / stub:fail to test the plumbing offline with no key.
uvx \
  --with pytest==8.4.1 \
  --with pytest-json-ctrf==0.3.5 \
  --with anthropic==0.120.0 \
  pytest --ctrf /logs/verifier/ctrf.json /tests/test_outputs.py -rA
rc=$?

if [ "$rc" -eq 0 ]; then
  echo 1 > /logs/verifier/reward.txt
elif [ "$rc" -eq 1 ]; then
  echo 0 > /logs/verifier/reward.txt
else
  echo "INFRA: verifier exited $rc (judge/infrastructure failure) — no score written" >&2
  exit "$rc"
fi
