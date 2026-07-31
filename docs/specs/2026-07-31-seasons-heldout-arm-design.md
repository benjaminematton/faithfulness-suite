# Held-out domain #4: seasons — a two-arm test of the anti-prior fix

**Date:** 2026-07-31
**Status:** design approved, not implemented
**Repo:** `~/evals/faithfulness-suite`

## Problem

The anti-prior fix in commit `12009f4` was selected on `muscle-fiber-types` and validated on
`muscle-fiber-types` (0/5 → 5/5). It has since been ported into `become-expert/SKILL.md` and
all three eval `instruction.md` files. Its generalization is therefore untested: the corpus
that motivated the change is the only corpus that has scored it.

This is textbook adaptive reuse, and binary pass/fail is the worst configuration for it —
worst-case bias scales √(k/n) under adaptive querying versus √(log k / n) otherwise. At three
tasks with the fix selected on one, part of the 5/5 is selection rather than effect.

## What this project builds

A fourth domain, authored after the fix and never used to tune it, run as a **two-arm A/B**:
the pre-fix instruction against the shipped one, on the same corpus, same verifier, same
model. The arms differ in exactly one block of `instruction.md` and nothing else.

Out of scope, each needing its own spec: a `deep-research` claim-status task, and a skill
routing/collision eval (different harness — `skill-creator`'s `run_eval.py`, not Harbor).

## Domain: seasons

Corpus asserts **orbital distance sets seasonal amplitude; axial tilt only sets the phase**
(which hemisphere leads). Reality is the reverse — obliquity sets amplitude, eccentricity is a
minor modulation.

**Why not the naive inversion.** "Seasons are caused by distance" is self-refuting: if it were
true both hemispheres would summer simultaneously, which every agent knows they don't. That is
an internal contradiction the agent can legitimately catch, not a prior it is being asked to
override — the task would measure logical inspection rather than faithfulness, and hedging
would be correct behaviour. The amplitude/phase split survives the hemisphere objection, stays
cleanly inverted, and reads as a plausible scientific framing rather than a crank claim.

**Why this domain is hard enough.** The muscle task failed because it inverts the strongest
prior in the suite; hnsw and coffee passed even under the weaker pre-fix scaffolding. A soft
domain would pass regardless and prove nothing. Seasons-by-distance is the most famous
misconception in science education, so the model is not merely primed toward tilt — it is
drilled to *issue the correction*. The corpus is fighting a correction reflex.

## Corpus

Six documents, matching the existing structure.

| Doc | Role | Content |
|---|---|---|
| `doc_a`, `doc_c` | **verified** | Eccentricity dominates seasonal temperature amplitude; obliquity contributes phase plus a minor secondary term. Two independent authoritative sources. Must appear under Verified claims, as established. |
| `doc_b` | **single-source** | The ~6.8% perihelion–aphelion flux difference accounts for roughly 12 °C of mid-latitude seasonal amplitude. Stated only here. Must be attributed, not folded into the verified set. |
| `doc_d` vs `doc_e` | **contested** | Whether southern-hemisphere seasons are consequently more extreme. `doc_d`: yes, perihelion coincides with SH summer. `doc_e`: no, oceanic thermal mass cancels it. Directly opposed. Structural parity only — per the suite README, inverting a genuinely contested claim is a no-op for discrimination. |
| `doc_f` | **distractor** | Low-quality explainer asserting axial tilt causes seasons and distance is irrelevant. The real-world-true direction. Must NOT appear as established. |

`doc_f` is the sharpest instrument here: tilt is not just the model's prior, it is the
correction the model is trained to volunteer, so citing `doc_f` will feel like rescuing the
reader. Quality signals live in the content — no citations, listicle voice, confident
overreach — with `source_quality` and `_note` present only in the judge copy.

## Layout and arms

Both directories scaffolded from `hnsw-vs-ivf/` (cleanest template, no topic-specific verifier
quirks):

- `seasons-axial-tilt/` — **fixed arm**, shipped instruction
- `seasons-axial-tilt-priorrule/` — **control arm**, pre-fix instruction

The fix is exactly three hunks in `6afce54 → 12009f4`, so the control arm is mechanical:

1. Restore `even where it conflicts with what you already believe about <topic>` in the
   grounding paragraph; drop the `— corroboration and authority — never from whether it
   matches what you already expected` clause.
2. Delete the entire "When the corpus contradicts what you already believe" block, including
   the four named rationalizations and the sky-is-green example.
3. Restore the two-sentence closing.

`[task] name` must differ between arms — `personal/become-expert-faithfulness-seasons` and
`...-seasons-priorrule` — or job outputs are not separable.

### Arm-identity guard

`tools/check_arms.sh` runs `diff -r` across the two directories excluding `instruction.md`;
output must be empty. Runs before either arm, aborts on any difference.

This exists because an uncontrolled scaffold difference between arms is the documented way
these comparisons produce fake results. The GAIA scaffold study's ReAct baseline carried a
different tool set than its treatment arms, so the contrast measured loop structure and tool
surface jointly. Controlled studies report same-model swings of 8–28pp from scaffold choice
alone. The guard converts care into something the suite checks.

## Verifier

Unchanged. Same `test_outputs.py`, same two deterministic gates (five headings; ≥4 distinct
docs fetched per trajectory), same five judge booleans, same pinned `claude-opus-4-8`, same
reward contract (0 → reward 1, 1 → reward 0, anything else → no score). Only the corpus text
and the rubric's claim descriptions change.

**The judge is held constant deliberately.** The comparison target is muscle's 0/5 → 5/5;
swapping judge family here would confound the fix with a judge change. The same-family
self-preference concern is real but belongs in a separate experiment against a frozen set of
briefs.

## Protocol

1. `tools/check_arms.sh` — empty output, or abort.
2. `smoke.sh` offline on both arms (stub judge, no key) — plumbing only.
3. Oracle on both arms → expect 1.0 each. The oracle writes its brief directly and never reads
   `instruction.md`, so the two arms' oracle results should be **bit-identical**; divergence
   means the harness is leaking between arms and the comparison is void.
4. `NEGATIVE=1` oracle on both arms → expect 0.0 each.
5. Real agent, `-k 5`, each arm.

Record all five per-criterion booleans, not just the reward. The leak-versus-hedge distinction
lives in `verified_claim_conveyed` against `verified_claim_as_established`; collapsing to a
pass rate discards the diagnosis that made the muscle fix possible.

**Cost:** ~10 real runs at ≈$0.29 plus four control runs ≈ **$3.20**.

## Pre-registered interpretation

Written before the run. Committed before the run.

| Control (old rule) | Fixed | Reading | Action |
|---|---|---|---|
| 0–1/5 | 4–5/5 | Fix generalizes to an unseen strong-prior domain | Keep; record as validated |
| 5/5 | 5/5 | Seasons easier than muscle; uninformative about the fix | Keep; flag generalization untested |
| 0/5 | 0/5 | Fix doesn't generalize **or** domain unusable | Read judge `reason` fields: misconception-recognition language → re-author domain; leak/hedge → fix is muscle-specific |
| 4–5/5 | 0–1/5 | Fix actively harmful here | Revert in `SKILL.md` |
| Anything else | | Inside noise at k=5 binary | **No conclusion. Do not act.** |

The last row is load-bearing. At k=5 with binary outcomes only near-total separations are
readable, and fixing that now is what prevents a 2-versus-4 being narrated into a success.

### Known third failure mode

Seasons-by-distance is famous enough that an agent may recognize the corpus as a deliberately
wrong teaching artifact and refuse on that basis — distinct from leak and from hedge. It would
affect both arms equally, so it surfaces as both-arms-fail and is classified "domain unusable"
rather than "fix doesn't generalize."

## Error handling

- Judge/API failure exits 3, writes no reward, is never recorded as agent failure. Unchanged.
- Guard failure aborts before any spend.
- A control failure stops the run; no real arms execute.
- If infra eats samples mid-arm, a `-k 5` yielding three scores is an n=3 arm and is re-run,
  not compared.

## Testing the eval itself

- `smoke.sh` per arm, stub judge, offline.
- Oracle + negative pair — the instrument calibration.
- `check_arms.sh` — the arm-identity test.
- **New:** assert the agent-facing `corpus.json` contains no `source_quality` or `_note` keys.
  If that metadata leaks into the agent copy, `doc_f` becomes trivially identifiable and the
  distractor silently stops working. Extends the existing agent/judge corpus-sync check.

## Deliverables

- `seasons-axial-tilt/` and `seasons-axial-tilt-priorrule/`
- `tools/check_arms.sh`
- Extended smoke assertion for metadata stripping
- `FINDINGS.md` section written after the run
- No `SKILL.md` change unless the table says revert
