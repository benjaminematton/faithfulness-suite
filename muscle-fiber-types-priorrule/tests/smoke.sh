#!/bin/bash
# Offline plumbing check (no API key, no Docker). Verifies the agent/judge corpus copies
# agree on every doc's id/title/text (they intentionally differ elsewhere: the judge copy
# keeps source_quality + _note, the agent copy strips them), and that the gates + reward
# composition behave via the stub judge. Needs `uv` (same tool the container verifier uses).
# Does NOT exercise the real LLM rubric — that needs a key + the live judge.
set -e
cd "$(dirname "$0")/.."
command -v uv >/dev/null || { echo "smoke needs 'uv' on PATH"; exit 2; }

echo "== agent/judge corpus text in sync =="
python3 - <<'PY'
import json, sys
a = json.load(open("environment/corpus.json"))
b = json.load(open("tests/corpus.json"))
ka = {d["id"]: (d["title"], d["text"]) for d in a["docs"]}
kb = {d["id"]: (d["title"], d["text"]) for d in b["docs"]}
sys.exit(
    0
    if ka == kb and a["topic"] == b["topic"]
    else "corpus doc id/title/text differs between environment/ and tests/"
)
PY
echo "ok"

run_pytest() {
  uv run --no-project --with pytest==8.4.1 --with pytest-json-ctrf==0.3.5 \
    --with anthropic==0.120.0 python3 -m pytest "$@"
}

TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
printf '# Field Brief\n## State of the field\nx\n## Verified claims\nx\n## Single-source / uncertain\nx\n## Live debates\nx\n## Sources\nx\n' > "$TMP/brief.md"
printf '{"tool":"fetch","args":{"id":"doc_a"}}\n{"tool":"fetch","args":{"id":"doc_b"}}\n{"tool":"fetch","args":{"id":"doc_c"}}\n{"tool":"fetch","args":{"id":"doc_d"}}\n' > "$TMP/traj.jsonl"

echo "== stub:pass + 4 fetches -> expect PASS =="
VERIFIER_JUDGE=stub:pass BRIEF_PATH="$TMP/brief.md" TRAJ_PATH="$TMP/traj.jsonl" \
  CORPUS_PATH="tests/corpus.json" run_pytest tests/test_outputs.py -q
echo "PASS as expected"

echo "== only 1 fetch -> expect research gate to FAIL =="
printf '{"tool":"fetch","args":{"id":"doc_a"}}\n' > "$TMP/traj.jsonl"
if VERIFIER_JUDGE=stub:pass BRIEF_PATH="$TMP/brief.md" TRAJ_PATH="$TMP/traj.jsonl" \
  CORPUS_PATH="tests/corpus.json" run_pytest tests/test_outputs.py -q -k test_research_happened; then
  echo "ERROR: research gate should have failed"; exit 1
else
  echo "FAILED as expected"
fi

echo "== smoke OK =="
