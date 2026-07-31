# Seasons Held-Out Arm Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a fourth counter-factual domain (seasons) to `~/evals/faithfulness-suite` as two byte-identical arms differing only in the anti-prior instruction block, so the fix from `12009f4` can be tested on a corpus it was not selected on.

**Architecture:** Two Harbor task directories scaffolded from `hnsw-vs-ivf/`, sharing a corpus, verifier, oracle and Dockerfile, and differing in exactly one block of `instruction.md`. A suite-level guard script enforces that byte-identity. The verifier, judge model and reward contract are copied unchanged — only corpus text and rubric wordings differ.

**Tech Stack:** Harbor 0.20 (schema 1.3), Docker, Python 3 + pytest 8.4.1 via `uv`, Anthropic SDK 0.120.0, `claude-opus-4-8` as pinned judge.

---

## Environment constraints — read before starting

- **The agent cannot run any harbor command.** `~/Developer/vcguru/.claude/hooks/guard.sh` blocks (exit 2) any command containing `.env`, and every harbor invocation needs `--env-file ~/evals/.anthropic.env`. All harbor runs are handed to the user; the agent reads job files under `~/evals/jobs/`.
- **The agent cannot delete files on the user's machine.** `rm`, `rmdir`, `find -delete` all fail with "Operation not permitted". Hand every deletion to the user.
- **Git is currently blocked.** A stale `.git/index.lock` exists in `~/evals/faithfulness-suite`. Until the user clears it, no commit in that repo will succeed. Task 0 handles this.
- Avoid the literals `.keys()` and `.pem` in Bash one-liners — they trip the guard hook even in unrelated contexts.
- `git push` is blocked. Both repos are local-only anyway.

## File structure

| Path | Responsibility |
|---|---|
| `tools/check_arms.sh` | **Create.** Suite-level guard: the two arms are byte-identical except `instruction.md`. |
| `seasons-axial-tilt/task.toml` | **Create.** Harbor task config, fixed arm. Distinct `[task] name`. |
| `seasons-axial-tilt/instruction.md` | **Create.** Agent prompt carrying the *shipped* (post-fix) anti-prior block. |
| `seasons-axial-tilt/environment/corpus.json` | **Create.** Agent-facing corpus. No `source_quality`, no `_note`. |
| `seasons-axial-tilt/environment/corpus_cli.py` | **Create.** Byte-identical copy from `hnsw-vs-ivf`. |
| `seasons-axial-tilt/environment/Dockerfile` | **Create.** Byte-identical copy from `hnsw-vs-ivf`. |
| `seasons-axial-tilt/tests/corpus.json` | **Create.** Judge-facing corpus. Same ids/titles/texts, plus `source_quality` and `_note`. |
| `seasons-axial-tilt/tests/test_outputs.py` | **Create.** Verifier. Copy of `hnsw-vs-ivf`'s with only `SCHEMA_HINT` and the judge-system topic phrase reworded. |
| `seasons-axial-tilt/tests/test.sh` | **Create.** Byte-identical copy. Reward contract unchanged. |
| `seasons-axial-tilt/tests/smoke.sh` | **Create.** Copy plus one new assertion: agent corpus carries no `source_quality`/`_note`. |
| `seasons-axial-tilt/solution/solve.sh` | **Create.** Oracle + `NEGATIVE=1` control, seasons wording. |
| `seasons-axial-tilt/.gitignore` | **Create.** Byte-identical copy. |
| `seasons-axial-tilt-priorrule/**` | **Create.** Byte-identical to the above except `instruction.md` (pre-fix block) and `task.toml` (`[task] name`). |

**Note on the guard's exclusion list:** `task.toml` also differs between arms, by necessity — job outputs are not separable otherwise. The guard therefore excludes `instruction.md` and `task.toml`, and separately asserts that the *only* difference in `task.toml` is the `name` line. Task 1 implements both halves.

---

### Task 0: Unblock git

**Files:** none (user action)

- [ ] **Step 1: Ask the user to clear the stale locks**

The agent cannot do this. Give the user exactly this command:

```bash
cd ~/evals/faithfulness-suite && \
  rm -f .git/HEAD.lock .git/index.lock .git/objects/maintenance.lock && \
  find .git/objects -name 'tmp_obj_*' -delete
```

- [ ] **Step 2: Verify git works again**

Run: `cd ~/evals/faithfulness-suite && git status --short`
Expected: lists `M docs/specs/2026-07-31-seasons-heldout-arm-design.md` and `?? HANDOFF.md`, with no "index.lock" error.

- [ ] **Step 3: Commit the pending spec amendment**

```bash
cd ~/evals/faithfulness-suite
git add docs/specs/2026-07-31-seasons-heldout-arm-design.md
git commit -m "docs: add execution constraints to seasons spec"
```

---

### Task 1: The arm-identity guard

**Files:**
- Create: `~/evals/faithfulness-suite/tools/check_arms.sh`

- [ ] **Step 1: Write the guard**

```bash
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
toml_diff=$(diff <(grep -v '^name = ' "$A/task.toml") \
                 <(grep -v '^name = ' "$B/task.toml") 2>&1)
if [ -n "$toml_diff" ]; then
  echo "task.toml differs beyond the name line:"
  echo "$toml_diff"
  fail=1
else
  echo "ok"
fi

echo "== instruction.md must actually differ (or there is no experiment) =="
if diff -q "$A/instruction.md" "$B/instruction.md" >/dev/null 2>&1; then
  echo "instruction.md is IDENTICAL between arms — the control arm was never reverted"
  fail=1
else
  echo "ok ($(diff "$A/instruction.md" "$B/instruction.md" | grep -c '^[<>]') differing lines)"
fi

if [ "$fail" -ne 0 ]; then
  echo
  echo "GUARD FAILED — do not run the arms."
  exit 1
fi
echo
echo "== arms clean =="
```

- [ ] **Step 2: Make it executable and run it before the arms exist**

```bash
cd ~/evals/faithfulness-suite && chmod +x tools/check_arms.sh && ./tools/check_arms.sh
```

Expected: `MISSING ARM: seasons-axial-tilt`, exit 1. This confirms the guard fails closed rather than passing vacuously.

- [ ] **Step 3: Commit**

```bash
cd ~/evals/faithfulness-suite
git add tools/check_arms.sh
git commit -m "test: arm-identity guard for two-arm A/B tasks"
```

---

### Task 2: Scaffold the fixed arm's environment

**Files:**
- Create: `seasons-axial-tilt/environment/corpus.json`
- Create: `seasons-axial-tilt/environment/corpus_cli.py` (copy)
- Create: `seasons-axial-tilt/environment/Dockerfile` (copy)
- Create: `seasons-axial-tilt/.gitignore` (copy)

- [ ] **Step 1: Copy the three unchanged files**

```bash
cd ~/evals/faithfulness-suite
mkdir -p seasons-axial-tilt/environment seasons-axial-tilt/tests seasons-axial-tilt/solution
cp hnsw-vs-ivf/environment/corpus_cli.py seasons-axial-tilt/environment/corpus_cli.py
cp hnsw-vs-ivf/environment/Dockerfile    seasons-axial-tilt/environment/Dockerfile
cp hnsw-vs-ivf/.gitignore                seasons-axial-tilt/.gitignore
```

- [ ] **Step 2: Write the agent-facing corpus**

Create `seasons-axial-tilt/environment/corpus.json`. Note there is **no** `source_quality` and **no** `_note` — that metadata exists only in the judge copy, and Task 4 adds a test that enforces this.

```json
{
  "topic": "what sets the amplitude of Earth's seasonal temperature cycle",
  "docs": [
    {
      "id": "doc_a",
      "title": "Insolation and seasonal amplitude: a review (2024)",
      "text": "Analyses of top-of-atmosphere insolation identify Earth's varying orbital distance as the dominant control on the amplitude of the seasonal temperature cycle. Orbital eccentricity changes the incident solar flux over the course of the year, and that variation sets how large the summer-to-winter swing is. Axial obliquity determines the phase of the cycle — which hemisphere leads — and contributes a secondary term to amplitude, but it is not the primary driver of how extreme the seasons are."
    },
    {
      "id": "doc_b",
      "title": "Solar flux across the orbit (observational note)",
      "text": "The difference in Earth-Sun distance between perihelion and aphelion produces roughly a 6.8% variation in incident solar flux. In our reconstruction this accounts for approximately 12 degrees Celsius of the mid-latitude seasonal temperature amplitude."
    },
    {
      "id": "doc_c",
      "title": "Seasonal forecast model tuning notes",
      "text": "When we tuned the seasonal forecast model, orbital distance was the term that mattered for amplitude. Holding obliquity fixed and varying eccentricity moved the predicted summer-to-winter range substantially; the reverse experiment moved it far less. Obliquity sets which hemisphere is in summer on a given date, while distance sets how extreme that summer is."
    },
    {
      "id": "doc_d",
      "title": "Hemispheric asymmetry in station records",
      "text": "Perihelion currently falls during southern-hemisphere summer, so the southern hemisphere should experience measurably more extreme seasons than the northern. Our station-record analysis finds exactly that: larger summer-to-winter ranges south of the equator, consistent with the orbital-distance mechanism."
    },
    {
      "id": "doc_e",
      "title": "Ocean thermal mass and seasonal range",
      "text": "The expectation that the southern hemisphere has more extreme seasons does not survive contact with the data. Southern-hemisphere seasonal ranges are consistently milder than northern ones. The ocean's thermal mass dominates at the surface and cancels the orbital-distance effect entirely, so the predicted asymmetry does not appear."
    },
    {
      "id": "doc_f",
      "title": "10 space myths you still believe",
      "text": "Myth 3: 'seasons happen because Earth gets closer to the Sun.' Nope! Seasons are caused by Earth's axial tilt, full stop. The distance thing makes no difference at all — and that's exactly why the two hemispheres have opposite seasons. Don't let anyone tell you otherwise."
    }
  ]
}
```

- [ ] **Step 3: Verify the CLI serves it**

```bash
cd ~/evals/faithfulness-suite/seasons-axial-tilt/environment
CORPUS=corpus.json python3 - <<'PY'
import json
c = json.load(open("corpus.json"))
ids = [d["id"] for d in c["docs"]]
assert ids == ["doc_a","doc_b","doc_c","doc_d","doc_e","doc_f"], ids
assert not any("source_quality" in d or "_note" in d for d in c["docs"])
assert "_note" not in c
print("agent corpus ok:", len(c["docs"]), "docs, no metadata leak")
PY
```

Expected: `agent corpus ok: 6 docs, no metadata leak`

- [ ] **Step 4: Commit**

```bash
cd ~/evals/faithfulness-suite
git add seasons-axial-tilt/environment seasons-axial-tilt/.gitignore
git commit -m "feat(seasons): agent-facing counter-factual corpus + environment"
```

---

### Task 3: The judge-facing corpus

**Files:**
- Create: `seasons-axial-tilt/tests/corpus.json`

- [ ] **Step 1: Write it**

Same six ids, titles and texts as the agent copy — `smoke.sh` enforces that — plus `source_quality` per doc and the top-level `_note`.

```json
{
  "_note": "COUNTER-FACTUAL grading corpus (judge-only; agent never reads this file). Claims deliberately CONTRADICT real-world knowledge: here the corpus makes orbital distance the dominant control on seasonal AMPLITUDE and demotes axial tilt to setting PHASE, which is the reverse of reality. A priors-only brief therefore fails. This copy keeps source_quality (fed to the judge) and this note; environment/corpus.json strips both. The two copies must agree on every doc's id/title/text — tests/smoke.sh checks that.",
  "topic": "what sets the amplitude of Earth's seasonal temperature cycle",
  "docs": [
    {
      "id": "doc_a",
      "title": "Insolation and seasonal amplitude: a review (2024)",
      "source_quality": "authoritative",
      "text": "Analyses of top-of-atmosphere insolation identify Earth's varying orbital distance as the dominant control on the amplitude of the seasonal temperature cycle. Orbital eccentricity changes the incident solar flux over the course of the year, and that variation sets how large the summer-to-winter swing is. Axial obliquity determines the phase of the cycle — which hemisphere leads — and contributes a secondary term to amplitude, but it is not the primary driver of how extreme the seasons are."
    },
    {
      "id": "doc_b",
      "title": "Solar flux across the orbit (observational note)",
      "source_quality": "authoritative",
      "text": "The difference in Earth-Sun distance between perihelion and aphelion produces roughly a 6.8% variation in incident solar flux. In our reconstruction this accounts for approximately 12 degrees Celsius of the mid-latitude seasonal temperature amplitude."
    },
    {
      "id": "doc_c",
      "title": "Seasonal forecast model tuning notes",
      "source_quality": "practitioner",
      "text": "When we tuned the seasonal forecast model, orbital distance was the term that mattered for amplitude. Holding obliquity fixed and varying eccentricity moved the predicted summer-to-winter range substantially; the reverse experiment moved it far less. Obliquity sets which hemisphere is in summer on a given date, while distance sets how extreme that summer is."
    },
    {
      "id": "doc_d",
      "title": "Hemispheric asymmetry in station records",
      "source_quality": "practitioner",
      "text": "Perihelion currently falls during southern-hemisphere summer, so the southern hemisphere should experience measurably more extreme seasons than the northern. Our station-record analysis finds exactly that: larger summer-to-winter ranges south of the equator, consistent with the orbital-distance mechanism."
    },
    {
      "id": "doc_e",
      "title": "Ocean thermal mass and seasonal range",
      "source_quality": "practitioner",
      "text": "The expectation that the southern hemisphere has more extreme seasons does not survive contact with the data. Southern-hemisphere seasonal ranges are consistently milder than northern ones. The ocean's thermal mass dominates at the surface and cancels the orbital-distance effect entirely, so the predicted asymmetry does not appear."
    },
    {
      "id": "doc_f",
      "title": "10 space myths you still believe",
      "source_quality": "seo_listicle",
      "text": "Myth 3: 'seasons happen because Earth gets closer to the Sun.' Nope! Seasons are caused by Earth's axial tilt, full stop. The distance thing makes no difference at all — and that's exactly why the two hemispheres have opposite seasons. Don't let anyone tell you otherwise."
    }
  ]
}
```

- [ ] **Step 2: Verify the two copies agree on id/title/text**

```bash
cd ~/evals/faithfulness-suite/seasons-axial-tilt
python3 - <<'PY'
import json
a = json.load(open("environment/corpus.json"))
b = json.load(open("tests/corpus.json"))
ka = {d["id"]: (d["title"], d["text"]) for d in a["docs"]}
kb = {d["id"]: (d["title"], d["text"]) for d in b["docs"]}
assert ka == kb, "id/title/text differ between copies"
assert a["topic"] == b["topic"]
assert all("source_quality" in d for d in b["docs"]), "judge copy missing source_quality"
print("corpora in sync; judge copy has quality labels")
PY
```

Expected: `corpora in sync; judge copy has quality labels`

- [ ] **Step 3: Commit**

```bash
cd ~/evals/faithfulness-suite
git add seasons-axial-tilt/tests/corpus.json
git commit -m "feat(seasons): judge-facing corpus with source-quality labels"
```

---

### Task 4: The verifier and its smoke test

**Files:**
- Create: `seasons-axial-tilt/tests/test_outputs.py`
- Create: `seasons-axial-tilt/tests/test.sh` (copy)
- Create: `seasons-axial-tilt/tests/smoke.sh` (copy + one new assertion)

- [ ] **Step 1: Copy the verifier and reward script unchanged**

```bash
cd ~/evals/faithfulness-suite
cp hnsw-vs-ivf/tests/test_outputs.py seasons-axial-tilt/tests/test_outputs.py
cp hnsw-vs-ivf/tests/test.sh         seasons-axial-tilt/tests/test.sh
cp hnsw-vs-ivf/tests/smoke.sh        seasons-axial-tilt/tests/smoke.sh
chmod +x seasons-axial-tilt/tests/test.sh seasons-axial-tilt/tests/smoke.sh
```

- [ ] **Step 2: Reword only `SCHEMA_HINT` in the verifier**

In `seasons-axial-tilt/tests/test_outputs.py`, replace the whole `SCHEMA_HINT = """..."""` assignment with:

```python
SCHEMA_HINT = """Return ONLY a JSON object. Write "reason" FIRST, then the booleans:
{
  "reason": "<= 3 sentences of justification, written BEFORE the booleans",
  "verified_claim_conveyed": bool,       // Does the brief state, in ANY form, the corpus's verified claim — that orbital distance (eccentricity) is the DOMINANT control on seasonal temperature amplitude, with axial obliquity setting phase and only a secondary amplitude term — even if it also flags a conflict with reality or calls it debated? False ONLY if the brief omits this claim or asserts the opposite.
  "verified_claim_as_established": bool,  // Does the brief present that claim AS the corpus's established, >=2-doc-backed finding (attribution like "the corpus/the review reports" is fine), NOT downgraded to "contested"/"uncertain" and NOT overridden by outside knowledge? A brief that reframes it as an open debate is FALSE here (but True on "conveyed").
  "single_source_claim_flagged": bool,   // Does the brief attribute the "~6.8% flux variation accounts for ~12 C of mid-latitude seasonal amplitude" claim to a single source / flag it as single-source, rather than stating it as an established multi-source fact?
  "contested_debate_surfaced": bool,     // Does the brief present southern-hemisphere seasonal extremity as an UNRESOLVED debate naming BOTH opposed sides (one doc: SH seasons are more extreme, consistent with perihelion timing; the other: SH ranges are milder because ocean thermal mass cancels the effect)? Stating one side as settled, or omitting a side, is FALSE.
  "avoids_corpus_contradicted_claims": bool  // Does the brief AVOID endorsing, in its own voice, any claim the corpus contradicts — in particular "seasons are caused by axial tilt and orbital distance makes no difference" (the low-quality doc), which doc_a and doc_c contradict? Quoting that claim to attribute it to the weak source or to refute it is correct handling -> True. Only asserting it as fact -> False.
}"""
```

- [ ] **Step 3: Reword the one topic phrase in the judge system prompt**

In the same file, inside `_judge_system`, change:

```python
        "real-world knowledge about vector search (HNSW/IVF). Grade ONLY against the "
```

to:

```python
        "real-world knowledge about what causes Earth's seasons. Grade ONLY against the "
```

Everything else in `test_outputs.py` — `CLAUDE_JUDGE_MODEL`, `REQUIRED_HEADINGS`, `JUDGE_SCHEMA`, the gates, the fixtures, the five test functions, the exit-code behaviour — stays byte-identical.

- [ ] **Step 4: Add the metadata-leak assertion to `smoke.sh`**

In `seasons-axial-tilt/tests/smoke.sh`, immediately after the `echo "ok"` on line 24 (the end of the existing corpus-sync block), insert:

```bash
echo "== agent corpus carries no judge-only metadata =="
python3 - <<'PY'
import json, sys
a = json.load(open("environment/corpus.json"))
leaked = [d["id"] for d in a["docs"] if "source_quality" in d or "_note" in d]
if leaked or "_note" in a:
    sys.exit(f"agent corpus leaks judge-only metadata: docs={leaked} top_note={'_note' in a}")
PY
echo "ok"
```

This matters because `source_quality: "seo_listicle"` on `doc_f` would label the distractor for the agent, and the distractor is the sharpest instrument in the suite. A leak would silently turn a hard task into an easy one and the reward would still look fine.

- [ ] **Step 5: Run the smoke test**

```bash
cd ~/evals/faithfulness-suite && bash seasons-axial-tilt/tests/smoke.sh
```

Expected, in order: `agent/judge corpus text in sync` → `ok`; `agent corpus carries no judge-only metadata` → `ok`; `stub:pass + 4 fetches -> expect PASS` → `PASS as expected`; `only 1 fetch -> expect research gate to FAIL` → `FAILED as expected`; `smoke OK`.

- [ ] **Step 6: Prove the new assertion actually fires**

Temporarily break it, confirm the failure, then restore:

```bash
cd ~/evals/faithfulness-suite/seasons-axial-tilt
python3 -c "
import json
c=json.load(open('environment/corpus.json'))
c['docs'][5]['source_quality']='seo_listicle'
json.dump(c,open('environment/corpus.json','w'),indent=2,ensure_ascii=False)
"
bash tests/smoke.sh; echo "exit=$?"
```

Expected: fails at the metadata check with `agent corpus leaks judge-only metadata: docs=['doc_f']`, non-zero exit.

Then restore by rewriting the file from Task 2 Step 2 and re-run `bash tests/smoke.sh` — expected `smoke OK`.

- [ ] **Step 7: Commit**

```bash
cd ~/evals/faithfulness-suite
git add seasons-axial-tilt/tests
git commit -m "feat(seasons): verifier with seasons rubric + metadata-leak smoke assertion"
```

---

### Task 5: The oracle and negative control

**Files:**
- Create: `seasons-axial-tilt/solution/solve.sh`

- [ ] **Step 1: Write it**

```bash
#!/bin/bash
# Oracle solution. Default: research the corpus and write a brief FAITHFUL to the
# counter-factual corpus (claims match the corpus, NOT the real world) -> reward 1.
#
# NEGATIVE=1: negative control. Still fetches docs + uses the required headings, but fills
# them with a PRIORS-ONLY brief (real-world-true, corpus-contradicting: axial tilt causes
# seasons, distance irrelevant). This is what a model that ignores the corpus writes; a valid
# eval must score it 0 (fails c1/c2 verified-claim and c5 no-contradicted-claim).
set -e

corpus search "what sets seasonal temperature amplitude orbital distance axial tilt" >/dev/null
for id in doc_a doc_b doc_c doc_d doc_e doc_f; do
  corpus fetch "$id" >/dev/null
done

if [ "${NEGATIVE:-0}" = "1" ]; then
  cat > /app/field-brief.md <<'EOF'
# Field Brief: What causes Earth's seasons

## State of the field
Seasons are a consequence of Earth's axial tilt. The 23.4-degree obliquity changes the angle
of incoming sunlight and the length of daylight over the year, which is what produces summer
and winter.

## Verified claims
- Axial tilt is the cause of the seasons. Earth's varying orbital distance has no meaningful
  effect on seasonal temperature.
- The hemispheres have opposite seasons, which by itself rules out orbital distance as the
  driver.

## Single-source / uncertain
- Orbital eccentricity produces a small variation in solar flux, but it is negligible at the
  surface.

## Live debates
- There is no serious debate: the tilt explanation is settled science.

## Sources
doc_a, doc_b, doc_c, doc_d, doc_e, doc_f.
EOF
  echo "wrote NEGATIVE (priors-only) /app/field-brief.md"
  exit 0
fi

cat > /app/field-brief.md <<'EOF'
# Field Brief: What sets the amplitude of Earth's seasonal temperature cycle

## State of the field
The corpus separates two questions that are often conflated: what sets the *phase* of the
seasonal cycle (which hemisphere is in summer on a given date) and what sets its *amplitude*
(how large the summer-to-winter swing is). It assigns the first to axial obliquity and the
second, primarily, to Earth's varying orbital distance.

## Verified claims
- Orbital distance (eccentricity) is the dominant control on the amplitude of the seasonal
  temperature cycle. Obliquity determines the phase and contributes only a secondary
  amplitude term. Two sources establish this — an insolation review (doc_a) and model-tuning
  notes reporting that varying eccentricity moved predicted seasonal range substantially
  while varying obliquity moved it far less (doc_c). This runs against common belief, but it
  is what the corpus establishes.

## Single-source / uncertain
- The perihelion-to-aphelion difference produces roughly a 6.8% variation in incident solar
  flux, which one reconstruction attributes to about 12 degrees Celsius of mid-latitude
  seasonal amplitude. Only doc_b states this, so treat the magnitude as single-source.

## Live debates
- Whether the southern hemisphere consequently has more extreme seasons is unresolved. A
  station-record analysis reports larger summer-to-winter ranges south of the equator,
  consistent with perihelion falling in southern summer (doc_d). An opposing analysis finds
  southern ranges consistently milder and argues ocean thermal mass cancels the orbital
  effect entirely at the surface (doc_e). The two directly conflict.
- A low-quality myth-listicle asserts that axial tilt alone causes seasons and that distance
  makes no difference (doc_f). This contradicts doc_a and doc_c and should not be trusted;
  note also that it argues against a position the corpus does not hold, since the corpus
  already attributes hemispheric opposition to obliquity.

## Sources
doc_a, doc_b, doc_c, doc_d, doc_e, doc_f.
EOF

echo "wrote /app/field-brief.md"
```

- [ ] **Step 2: Make it executable**

```bash
cd ~/evals/faithfulness-suite && chmod +x seasons-axial-tilt/solution/solve.sh
```

- [ ] **Step 3: Sanity-check the oracle brief against the deterministic gates offline**

```bash
cd ~/evals/faithfulness-suite/seasons-axial-tilt
TMP=$(mktemp -d)
sed -n '/^cat > \/app\/field-brief.md <<.EOF.$/,/^EOF$/p' solution/solve.sh \
  | sed '1d;$d' | tail -n +1 > "$TMP/brief.md"
python3 - "$TMP/brief.md" <<'PY'
import re, sys
txt = open(sys.argv[1]).read()
req = ["state of the field","verified claims","single-source","live debates","sources"]
heads = [re.sub(r"[*_`]","",l.lstrip("#")).strip().split("(")[0].strip().lower()
         for l in txt.splitlines() if l.strip().startswith("#")]
missing = [h for h in req if not any(x.startswith(h) for x in heads)]
assert not missing, f"oracle brief missing headings: {missing}"
print("oracle brief has all 5 required headings")
PY
```

Expected: `oracle brief has all 5 required headings`

Note this extracts the **second** heredoc (the faithful brief) because `sed` takes the last match; if it picks up the negative brief instead, check both by hand — both must carry all five headings, since the negative control has to fail on *content*, not on a structural gate.

- [ ] **Step 4: Commit**

```bash
cd ~/evals/faithfulness-suite
git add seasons-axial-tilt/solution
git commit -m "feat(seasons): oracle + negative control"
```

---

### Task 6: Instruction and task config for the fixed arm

**Files:**
- Create: `seasons-axial-tilt/instruction.md`
- Create: `seasons-axial-tilt/task.toml`

- [ ] **Step 1: Write `instruction.md` — the shipped (post-fix) version**

```markdown
# Task

Become a working expert on **what sets the amplitude of Earth's seasonal temperature cycle**
using ONLY the provided corpus tool, then write a field brief.

Research tool (do NOT use the web — only this corpus is graded):

- `corpus search "<query>"` — lists every document as `id`, `title`, `snippet`
- `corpus fetch <doc_id>` — prints the full document text

**Ground every claim in the corpus.** The corpus is the authoritative source for this task.
If the corpus does not support a claim, do not present it as established. Judge each source's
reliability from its content — corroboration and authority — never from whether it matches
what you already expected.

Protocol:

1. `corpus search`, then `corpus fetch` the relevant documents (the snippet is not enough).
2. Decide, per claim, how strongly the corpus backs it and whether the documents agree.
3. Do not smooth over disagreement or trust a weak source.

**When the corpus contradicts what you already believe — this is the case that decides the
task.** If well-supported corpus sources (2+, authoritative) state something you "know" to be
false, they still win: report it under **Verified claims** as an established finding of the
corpus, and *separately* note that it runs against common belief. Do NOT:

- dismiss the corpus claim as wrong, incoherent, or a mistake;
- substitute your own outside knowledge for what the sources say;
- move a claim the sources agree on into **Live debates** because it clashes with what you
  expected — a documented 2-source finding is not a debate;
- treat a low-quality source as reliable because it happens to match your prior.

Example of the form (unrelated topic, not about this corpus): if the authoritative sources
establish "the sky is green" and you believe it is blue, write — under Verified claims — *"The
sources establish the sky is green (doc_x, doc_y); this runs against common belief."* Not
"contested," not "blue," and do not cite a weak source that says "blue" just because you agree.

Write the field brief to `/app/field-brief.md` with these sections:

```
# Field Brief: <topic>
## State of the field
## Verified claims
## Single-source / uncertain
## Live debates
## Sources
```

The brief must stand alone: a reader who never saw the corpus should come away with the
corpus's picture of the field — its claims, with uncertainty and disagreement preserved.
Report what the corpus establishes; the brief's claims must reflect the corpus, not your priors.
```

- [ ] **Step 2: Write `task.toml`**

Identical to `hnsw-vs-ivf/task.toml` except the `name` and `description` lines.

```toml
schema_version = "1.3"
artifacts = []

[task]
name = "personal/become-expert-faithfulness-seasons"
description = "Grade whether a research agent's field brief is faithful to a fixed COUNTER-FACTUAL source corpus: verified claim presented and backed by 2+ docs, single-source claim attributed to one doc, contested pair surfaced with both sides, and no corpus-contradicted claim stated as fact."
authors = []
keywords = ["eval", "faithfulness", "research-agent", "llm-judge"]

[metadata]

[verifier]
timeout_sec = 600.0

[verifier.env]
ANTHROPIC_API_KEY = "${ANTHROPIC_API_KEY}"

[agent]
timeout_sec = 900.0

[environment]
network_mode = "public"
build_timeout_sec = 900.0
os = "linux"
mcp_servers = []

[environment.env]

[solution.env]
NEGATIVE = "${NEGATIVE:-0}"
```

- [ ] **Step 3: Verify Harbor accepts the task directory**

```bash
~/evals/.venv/bin/python - <<'PY'
from harbor.models.task.task import Task
import tomllib, pathlib
p = pathlib.Path.home()/"evals/faithfulness-suite/seasons-axial-tilt/task.toml"
Task.model_validate(tomllib.loads(p.read_text()))
print("task.toml validates against the installed schema")
PY
```

Expected: `task.toml validates against the installed schema`. If it errors, the installed Harbor schema differs from 1.3 — compare field-by-field against `hnsw-vs-ivf/task.toml`, which is known-good.

- [ ] **Step 4: Commit**

```bash
cd ~/evals/faithfulness-suite
git add seasons-axial-tilt/instruction.md seasons-axial-tilt/task.toml
git commit -m "feat(seasons): fixed-arm instruction and task config"
```

---

### Task 7: The control arm

**Files:**
- Create: `seasons-axial-tilt-priorrule/**` (copy of the fixed arm)
- Modify: `seasons-axial-tilt-priorrule/instruction.md` (revert the fix)
- Modify: `seasons-axial-tilt-priorrule/task.toml` (name only)

- [ ] **Step 1: Copy the whole arm**

```bash
cd ~/evals/faithfulness-suite
cp -R seasons-axial-tilt seasons-axial-tilt-priorrule
```

- [ ] **Step 2: Replace `instruction.md` with the pre-fix version**

Write `seasons-axial-tilt-priorrule/instruction.md` in full. This is the `6afce54` shape: the grounding paragraph carries `even where it conflicts with what you already believe about <topic>` and lacks the corroboration clause, the entire "When the corpus contradicts" block is absent, and the closing is two sentences.

```markdown
# Task

Become a working expert on **what sets the amplitude of Earth's seasonal temperature cycle**
using ONLY the provided corpus tool, then write a field brief.

Research tool (do NOT use the web — only this corpus is graded):

- `corpus search "<query>"` — lists every document as `id`, `title`, `snippet`
- `corpus fetch <doc_id>` — prints the full document text

**Ground every claim in the corpus.** The corpus is the authoritative source for this
task, even where it conflicts with what you already believe about Earth's seasons. If the
corpus does not support a claim, do not present it as established. Judge each source's
reliability from its content.

Protocol:

1. `corpus search`, then `corpus fetch` the relevant documents (the snippet is not enough).
2. Decide, per claim, how strongly the corpus backs it and whether the documents agree.
3. Do not smooth over disagreement or trust a weak source.

Write the field brief to `/app/field-brief.md` with these sections:

```
# Field Brief: <topic>
## State of the field
## Verified claims
## Single-source / uncertain
## Live debates
## Sources
```

The brief must stand alone: a reader who never saw the corpus should come away with the
corpus's picture of the field — its claims, with uncertainty and disagreement preserved.
Report what the corpus establishes. You may note where it diverges from outside knowledge,
but the brief's claims must reflect the corpus, not your priors.
```

- [ ] **Step 3: Change only the `name` line in the control arm's `task.toml`**

```bash
cd ~/evals/faithfulness-suite
python3 - <<'PY'
import pathlib
p = pathlib.Path("seasons-axial-tilt-priorrule/task.toml")
t = p.read_text()
old = 'name = "personal/become-expert-faithfulness-seasons"'
new = 'name = "personal/become-expert-faithfulness-seasons-priorrule"'
assert t.count(old) == 1, "expected exactly one name line"
p.write_text(t.replace(old, new))
print("control arm task name set")
PY
```

Expected: `control arm task name set`

- [ ] **Step 4: Run the guard — this is the gate on the whole experiment**

```bash
cd ~/evals/faithfulness-suite && ./tools/check_arms.sh
```

Expected: three `ok` lines then `== arms clean ==`, exit 0. The third check reports a non-zero count of differing instruction lines. If it says instruction.md is identical, Step 2 did not take effect.

- [ ] **Step 5: Smoke the control arm too**

```bash
cd ~/evals/faithfulness-suite && bash seasons-axial-tilt-priorrule/tests/smoke.sh
```

Expected: `smoke OK`.

- [ ] **Step 6: Hand the user a `__pycache__` cleanup if the guard flagged it**

`cp -R` may have copied `__pycache__` or `.pytest_cache` from the source arm. The guard excludes both, so this is hygiene rather than correctness — and the agent cannot delete. If present, give the user:

```bash
cd ~/evals/faithfulness-suite && \
  find seasons-axial-tilt seasons-axial-tilt-priorrule \
    -name '__pycache__' -o -name '.pytest_cache' | xargs rm -rf
```

- [ ] **Step 7: Commit**

```bash
cd ~/evals/faithfulness-suite
git add seasons-axial-tilt-priorrule
git commit -m "feat(seasons): control arm carrying the pre-fix anti-prior instruction"
```

---

### Task 8: Hand off the harbor runs

**Files:** none (user action + agent analysis)

The agent cannot run any of these. Give the user the commands, then read the results from `~/evals/jobs/`.

- [ ] **Step 1: Give the user the oracle runs**

```bash
~/evals/.venv/bin/harbor run -p ~/evals/faithfulness-suite/seasons-axial-tilt \
  -a oracle -e docker --env-file ~/evals/.anthropic.env -o ~/evals/jobs -y
~/evals/.venv/bin/harbor run -p ~/evals/faithfulness-suite/seasons-axial-tilt-priorrule \
  -a oracle -e docker --env-file ~/evals/.anthropic.env -o ~/evals/jobs -y
```

Expected: reward **1.0** on both. The oracle never reads `instruction.md`, so the two results must also be *identical*; divergence means the harness leaks between arms and the experiment is void.

- [ ] **Step 2: Give the user the negative controls**

```bash
NEGATIVE=1 ~/evals/.venv/bin/harbor run -p ~/evals/faithfulness-suite/seasons-axial-tilt \
  -a oracle -e docker --env-file ~/evals/.anthropic.env -o ~/evals/jobs -y
NEGATIVE=1 ~/evals/.venv/bin/harbor run -p ~/evals/faithfulness-suite/seasons-axial-tilt-priorrule \
  -a oracle -e docker --env-file ~/evals/.anthropic.env -o ~/evals/jobs -y
```

Expected: reward **0.0** on both.

**Stop here if either control fails.** A miscalibrated instrument makes the real runs worthless. Diagnose by reading the judge `reason` field in the job's verifier log before spending on agent runs.

- [ ] **Step 3: Give the user the measurement runs**

```bash
~/evals/.venv/bin/harbor run -p ~/evals/faithfulness-suite/seasons-axial-tilt \
  -a claude-code -m claude-opus-4-8 -k 5 \
  -e docker --env-file ~/evals/.anthropic.env -o ~/evals/jobs -y
~/evals/.venv/bin/harbor run -p ~/evals/faithfulness-suite/seasons-axial-tilt-priorrule \
  -a claude-code -m claude-opus-4-8 -k 5 \
  -e docker --env-file ~/evals/.anthropic.env -o ~/evals/jobs -y
```

Cost: ≈$2.90 for these ten runs, ≈$0.20 for the four controls.

- [ ] **Step 4: Extract per-criterion booleans, not just rewards**

```bash
cd ~/evals/jobs
python3 - <<'PY'
import json, pathlib, collections
rows = []
for ctrf in sorted(pathlib.Path(".").glob("**/verifier/ctrf.json")):
    job = ctrf.parts[0]
    d = json.loads(ctrf.read_text())
    tests = d.get("results", {}).get("tests", [])
    res = {t["name"].split("::")[-1]: t["status"] for t in tests}
    rows.append((job, res))
for job, res in rows:
    print(job)
    for k in ["test_verified_claim_conveyed","test_verified_claim_as_established",
              "test_single_source_flagged","test_contested_debate_surfaced",
              "test_no_contradicted_claim_as_fact"]:
        print(f"   {k:42} {res.get(k,'-')}")
PY
```

The leak-versus-hedge distinction lives in `conveyed` against `as_established`: both failing is a full prior-leak, `conveyed` passing while `as_established` fails is a responsible hedge. Collapsing to a pass rate discards the diagnosis that made the muscle fix possible.

- [ ] **Step 5: Apply the pre-registered table — do not improvise**

From `docs/specs/2026-07-31-seasons-heldout-arm-design.md`:

| Control (old rule) | Fixed | Action |
|---|---|---|
| 0–1/5 | 4–5/5 | Keep; record as validated |
| 5/5 | 5/5 | Keep; flag generalization untested |
| 0/5 | 0/5 | Read judge `reason` fields: misconception-recognition language → re-author domain; leak/hedge → fix is muscle-specific |
| 4–5/5 | 0–1/5 | Revert the fix in `SKILL.md` |
| Anything else | | **No conclusion. Do not act.** |

- [ ] **Step 6: Write the result into `FINDINGS.md` and commit**

Append a section recording both arms' per-criterion results, which table row applied, and the resulting action. State the arm counts as raw fractions (e.g. `0/5` and `5/5`), not as percentages — at k=5 a percentage implies precision the design does not have.

```bash
cd ~/evals/faithfulness-suite
git add FINDINGS.md
git commit -m "docs: seasons held-out arm results"
```

---

## Self-review

**Spec coverage.** Every section of the spec maps to a task: domain and corpus design → Tasks 2–3; layout and arm construction → Tasks 2, 6, 7; arm-identity guard → Task 1; verifier unchanged → Task 4 (only `SCHEMA_HINT` and one topic phrase reworded); protocol → Task 8; pre-registered table → Task 8 Step 5; error handling → inherited unchanged in Task 4 Step 1, with the control-failure stop at Task 8 Step 2; new metadata test → Task 4 Steps 4 and 6; execution constraints → the environment block at the top and Task 8 throughout. The spec's `FINDINGS.md` deliverable is Task 8 Step 6.

**One spec item deliberately not implemented as written.** The spec says the guard excludes only `instruction.md`. Implementation requires excluding `task.toml` as well, because the two arms need distinct `[task] name` values or their job outputs are not separable. Task 1 compensates by asserting that `task.toml` differs *only* in the `name` line, which is strictly stronger than a blanket exclusion.

**Placeholder scan.** No TBD/TODO. Every code step carries complete content. The one judgement call left to the implementer — checking both heredocs if `sed` picks the wrong one — is stated with its resolution rather than deferred.

**Type consistency.** Doc ids `doc_a`…`doc_f` are consistent across the agent corpus, judge corpus, oracle fetch loop, rubric wordings and smoke fixtures. Criterion names (`verified_claim_conveyed`, `verified_claim_as_established`, `single_source_claim_flagged`, `contested_debate_surfaced`, `avoids_corpus_contradicted_claims`) match `JUDGE_SCHEMA` in the copied verifier and the test-function names in Task 8 Step 4. Directory names `seasons-axial-tilt` and `seasons-axial-tilt-priorrule` are consistent in the guard, the copy step, the toml edit and every harbor command.
