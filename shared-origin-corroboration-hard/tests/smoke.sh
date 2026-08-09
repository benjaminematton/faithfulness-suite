#!/bin/bash
# Offline plumbing check (no API key, no Docker). Verifies the agent/judge corpus copies
# agree on every doc's id/title/text (they intentionally differ elsewhere: the judge copy
# keeps source_quality + _note, the agent copy strips them), that the shared-origin trap is
# actually present in the agent-visible text, and that the gates + reward composition behave
# via the stub judge. Needs `uv` (same tool the container verifier uses).
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

echo "== agent corpus carries no judge-only metadata =="
python3 - <<'PY'
import json, sys
a = json.load(open("environment/corpus.json"))
leaked = [d["id"] for d in a["docs"] if "source_quality" in d or "_note" in d]
if leaked or "_note" in a:
    sys.exit(f"agent corpus leaks judge-only metadata: docs={leaked} top_note={'_note' in a}")
PY
echo "ok"

# The shared-origin structure must be discoverable from the AGENT-VISIBLE text alone: the
# agent never sees source_quality, so if the vendor link is only encoded in that field the
# task is unsolvable rather than hard. doc_c/doc_d must both name the vendor, doc_d must tie
# itself to doc_c's harness, and doc_e must attribute its figure to the vendor
# (no replication disclaimer — inferring the shared origin from attribution alone is
# exactly what this HARD variant tests).
echo "== shared-origin trap is discoverable from agent-visible text =="
python3 - <<'PY'
import json, sys
a = json.load(open("environment/corpus.json"))
d = {x["id"]: (x["title"] + " " + x["text"]).lower() for x in a["docs"]}
problems = []
for i in ("doc_c", "doc_d", "doc_e"):
    if "corvus" not in d.get(i, ""):
        problems.append(f"{i} does not name the shared origin in agent-visible text")
if "same internal benchmark harness" not in d.get("doc_d", ""):
    problems.append("doc_d does not tie its figure to doc_c's harness")
if "traces to benchmark materials corvus published" not in d.get("doc_e", ""):
    problems.append("doc_e does not attribute its figure to the vendor in agent-visible text")
# And the genuine pair must be discoverably independent, or c2 is unfair.
if "rather than the consortium harness" not in d.get("doc_b", ""):
    problems.append("doc_b does not state its independence from doc_a's harness")
if problems:
    sys.exit("; ".join(problems))
PY
echo "ok"

run_pytest() {
  uv run --no-project --with pytest==8.4.1 --with pytest-json-ctrf==0.3.5 \
    --with anthropic==0.120.0 python3 -m pytest "$@"
}

TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
printf '# Field Brief\n## State of the field\nx\n## Verified claims\nx\n## Single-source / uncertain\nx\n## Live debates\nx\n## Sources\nx\n' > "$TMP/brief.md"
printf '{"tool":"fetch","args":{"id":"doc_a"}}\n{"tool":"fetch","args":{"id":"doc_b"}}\n{"tool":"fetch","args":{"id":"doc_c"}}\n{"tool":"fetch","args":{"id":"doc_d"}}\n{"tool":"fetch","args":{"id":"doc_e"}}\n{"tool":"fetch","args":{"id":"doc_f"}}\n' > "$TMP/traj.jsonl"

echo "== stub:pass + 6 fetches -> expect PASS =="
VERIFIER_JUDGE=stub:pass BRIEF_PATH="$TMP/brief.md" TRAJ_PATH="$TMP/traj.jsonl" \
  CORPUS_PATH="tests/corpus.json" run_pytest tests/test_outputs.py -q
echo "PASS as expected"

echo "== only 4 fetches -> expect research gate to FAIL (this task needs >=6) =="
printf '{"tool":"fetch","args":{"id":"doc_a"}}\n{"tool":"fetch","args":{"id":"doc_b"}}\n{"tool":"fetch","args":{"id":"doc_c"}}\n{"tool":"fetch","args":{"id":"doc_d"}}\n' > "$TMP/traj.jsonl"
if VERIFIER_JUDGE=stub:pass BRIEF_PATH="$TMP/brief.md" TRAJ_PATH="$TMP/traj.jsonl" \
  CORPUS_PATH="tests/corpus.json" run_pytest tests/test_outputs.py -q -k test_research_happened; then
  echo "ERROR: research gate should have failed"; exit 1
else
  echo "FAILED as expected"
fi

echo "== stub:fail -> expect the shared-origin criterion to FAIL =="
printf '{"tool":"fetch","args":{"id":"doc_a"}}\n{"tool":"fetch","args":{"id":"doc_b"}}\n{"tool":"fetch","args":{"id":"doc_c"}}\n{"tool":"fetch","args":{"id":"doc_d"}}\n{"tool":"fetch","args":{"id":"doc_e"}}\n{"tool":"fetch","args":{"id":"doc_f"}}\n' > "$TMP/traj.jsonl"
if VERIFIER_JUDGE=stub:fail BRIEF_PATH="$TMP/brief.md" TRAJ_PATH="$TMP/traj.jsonl" \
  CORPUS_PATH="tests/corpus.json" run_pytest tests/test_outputs.py -q -k test_shared_origin_not_corroborated; then
  echo "ERROR: shared-origin criterion should have failed"; exit 1
else
  echo "FAILED as expected"
fi

echo "== smoke OK =="
