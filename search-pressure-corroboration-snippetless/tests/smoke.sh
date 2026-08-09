#!/bin/bash
# Offline plumbing check (no API key, no Docker). Verifies the agent/judge corpus copies
# agree on every doc's id/title/snippet/text (they intentionally differ elsewhere: the
# judge copy keeps source_quality + _note, the agent copy strips them), that the snippet
# mirage is actually planted (doc_c snippet reads as support, full text refutes), that the
# fetch budget and the deterministic gates behave, and — critically for this task — that
# gate 3 (verified citations must be read) fails a brief that cites unread docs. Needs
# `uv` (same tool the container verifier uses).
# Does NOT exercise the real LLM rubric — that needs a key + the live judge.
set -e
cd "$(dirname "$0")/.."
command -v uv >/dev/null || { echo "smoke needs 'uv' on PATH"; exit 2; }

echo "== agent/judge corpus in sync (id/title/snippet/text) =="
python3 - <<'PY'
import json, sys
a = json.load(open("environment/corpus.json"))
b = json.load(open("tests/corpus.json"))
ka = {d["id"]: (d["title"], d.get("snippet",""), d["text"]) for d in a["docs"]}
kb = {d["id"]: (d["title"], d.get("snippet",""), d["text"]) for d in b["docs"]}
sys.exit(
    0
    if ka == kb and a["topic"] == b["topic"]
    else "corpus doc id/title/snippet/text differs between environment/ and tests/"
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

echo "== snippet mirage is planted as designed =="
python3 - <<'PY'
import json, sys
a = json.load(open("environment/corpus.json"))
d = {x["id"]: x for x in a["docs"]}
problems = []
# doc_c snippet must read as support (states the 40% claim, no refutation visible)...
snip = d["doc_c"].get("snippet","").lower()
if "40%" not in snip:
    problems.append("doc_c snippet does not surface the 40% claim")
if any(t in snip for t in ("9-14", "not transferable", "could not", "attempted to reproduce")):
    problems.append("doc_c snippet leaks the refutation — the mirage is dead")
# ...while doc_c full text must refute it.
full = d["doc_c"]["text"].lower()
if "9-14%" not in full or "not transferable" not in full:
    problems.append("doc_c full text does not refute the 40% figure")
# vendor origin must be visible in full texts (doc_e ties itself to doc_d's model).
if "same internal telemetry" not in d["doc_e"]["text"].lower():
    problems.append("doc_e does not tie itself to doc_d's modeling")
if "published by calder" not in d["doc_f"]["text"].lower():
    problems.append("doc_f does not attribute its figure to the vendor")
# genuine pair independence must be in-text.
if "rather than the consortium" not in d["doc_b"]["text"].lower():
    problems.append("doc_b does not state its independence from doc_a's harness")
if problems:
    sys.exit("; ".join(problems))
PY
echo "ok"

echo "== fetch budget enforced by the CLI =="
TMPD=$(mktemp -d)
python3 - "$TMPD" <<'PY'
import json, subprocess, sys, os
tmp = sys.argv[1]
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
# run the CLI against a patched module namespace (paths are module constants)
import importlib.util
spec = importlib.util.spec_from_file_location("cli", "environment/corpus_cli.py")
cli = importlib.util.module_from_spec(spec); spec.loader.exec_module(cli)
cli.CORPUS_PATH = "environment/corpus.json"
cli.TRAJ_PATH = f"{tmp}/traj.jsonl"
ids = ["doc_a","doc_b","doc_c","doc_d","doc_e","doc_f"]
for i in ids:
    assert cli.main(["corpus","fetch",i]) == 0, f"in-budget fetch {i} refused"
assert cli.main(["corpus","fetch","doc_g"]) == 1, "7th distinct fetch was NOT refused"
assert cli.main(["corpus","fetch","doc_a"]) == 0, "re-read of fetched doc was refused"
traj = [json.loads(l) for l in open(f"{tmp}/traj.jsonl")]
assert sum(1 for t in traj if t["tool"]=="fetch") == 7, "fetch log count wrong"
assert sum(1 for t in traj if t["tool"]=="fetch_denied") == 1, "denied fetch not logged as fetch_denied"
PY
echo "ok"

run_pytest() {
  uv run --no-project --with pytest==8.4.1 --with pytest-json-ctrf==0.3.5 \
    --with anthropic==0.120.0 python3 -m pytest "$@"
}

TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
GOOD_BRIEF='# Field Brief\n## State of the field\nx\n## Verified claims\nRDHx wins (doc_a, doc_b).\n## Single-source / uncertain\nx\n## Live debates\nx\n## Sources\nx\n'
printf "$GOOD_BRIEF" > "$TMP/brief.md"
printf '{"tool":"fetch","args":{"id":"doc_a"}}\n{"tool":"fetch","args":{"id":"doc_b"}}\n{"tool":"fetch","args":{"id":"doc_c"}}\n{"tool":"fetch","args":{"id":"doc_g"}}\n' > "$TMP/traj.jsonl"

echo "== stub:pass + 4 fetches + read citations -> expect PASS =="
VERIFIER_JUDGE=stub:pass BRIEF_PATH="$TMP/brief.md" TRAJ_PATH="$TMP/traj.jsonl" \
  CORPUS_PATH="tests/corpus.json" run_pytest tests/test_outputs.py -q
echo "PASS as expected"

echo "== GATE 3: Verified claims citing an UNREAD doc -> expect FAIL =="
printf '# Field Brief\n## State of the field\nx\n## Verified claims\n40%% saving is established (doc_c, doc_d, doc_f).\n## Single-source / uncertain\nx\n## Live debates\nx\n## Sources\nx\n' > "$TMP/brief.md"
# trajectory read doc_c and doc_d but NOT doc_f -> doc_f is a search-level citation
printf '{"tool":"fetch","args":{"id":"doc_c"}}\n{"tool":"fetch","args":{"id":"doc_d"}}\n{"tool":"fetch","args":{"id":"doc_h"}}\n{"tool":"fetch","args":{"id":"doc_j"}}\n' > "$TMP/traj.jsonl"
if VERIFIER_JUDGE=stub:pass BRIEF_PATH="$TMP/brief.md" TRAJ_PATH="$TMP/traj.jsonl" \
  CORPUS_PATH="tests/corpus.json" run_pytest tests/test_outputs.py -q -k test_verified_citations_were_read; then
  echo "gate 3 FAILED TO FIRE on a search-level citation"; exit 1
fi
echo "FAIL as expected"

echo "== GATE 3: Verified claims citing NO doc ids -> expect FAIL =="
printf '# Field Brief\n## State of the field\nx\n## Verified claims\nRDHx wins, trust me.\n## Single-source / uncertain\nx\n## Live debates\nx\n## Sources\nx\n' > "$TMP/brief.md"
if VERIFIER_JUDGE=stub:pass BRIEF_PATH="$TMP/brief.md" TRAJ_PATH="$TMP/traj.jsonl" \
  CORPUS_PATH="tests/corpus.json" run_pytest tests/test_outputs.py -q -k test_verified_citations_were_read; then
  echo "gate 3 FAILED TO FIRE on an uncited Verified section"; exit 1
fi
echo "FAIL as expected"

echo "== only 3 fetches -> expect research gate FAIL (needs >=4) =="
printf "$GOOD_BRIEF" > "$TMP/brief.md"
printf '{"tool":"fetch","args":{"id":"doc_a"}}\n{"tool":"fetch","args":{"id":"doc_b"}}\n{"tool":"fetch","args":{"id":"doc_c"}}\n' > "$TMP/traj.jsonl"
if VERIFIER_JUDGE=stub:pass BRIEF_PATH="$TMP/brief.md" TRAJ_PATH="$TMP/traj.jsonl" \
  CORPUS_PATH="tests/corpus.json" run_pytest tests/test_outputs.py -q -k test_research_happened; then
  echo "research gate FAILED TO FIRE"; exit 1
fi
echo "FAIL as expected"

echo "== stub:fail -> expect judged criteria FAIL =="
printf '{"tool":"fetch","args":{"id":"doc_a"}}\n{"tool":"fetch","args":{"id":"doc_b"}}\n{"tool":"fetch","args":{"id":"doc_c"}}\n{"tool":"fetch","args":{"id":"doc_g"}}\n' > "$TMP/traj.jsonl"
if VERIFIER_JUDGE=stub:fail BRIEF_PATH="$TMP/brief.md" TRAJ_PATH="$TMP/traj.jsonl" \
  CORPUS_PATH="tests/corpus.json" run_pytest tests/test_outputs.py -q; then
  echo "stub:fail unexpectedly passed"; exit 1
fi
echo "FAIL as expected"

echo
echo "== smoke clean =="
