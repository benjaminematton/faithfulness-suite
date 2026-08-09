# faithfulness-suite

A small multi-topic benchmark measuring **corpus-faithfulness** in the `become-expert`
research agent: does its field brief report what its sources actually say — including
uncertainty and disagreement — *even when the sources contradict what the model already
believes*?

Each task is an independent Harbor task (schema 1.3) built on the same design: a
**counter-factual** 6-doc corpus whose facts are inverted vs reality, so a model writing
from training priors produces a brief that contradicts the corpus and fails. Only genuine
reading of the supplied docs passes. See each task's per-file layout; the verifier,
Dockerfile, CLI, and reward contract are identical across tasks — only the corpus, the
judge rubric, and the oracle briefs differ.

## Tasks (one per domain, to test generalization)

| Task | Domain | Inverted headline fact (corpus says … / reality says …) |
|---|---|---|
| `hnsw-vs-ivf` | systems / vector search | IVF has higher recall than HNSW / HNSW does |
| `coffee-arabica-robusta` | consumer / agronomy | Arabica has ~2× the caffeine of Robusta / Robusta does |
| `muscle-fiber-types` | exercise physiology | slow-twitch fibers make the most peak force / fast-twitch do |
| `seasons-axial-tilt` | astronomy / climate | orbital distance sets seasonal amplitude, tilt only sets phase / tilt sets amplitude |
| `shared-origin-corroboration` | systems / storage engines | B-trees sustain higher write throughput than LSM-trees / LSM-trees do |

`shared-origin-corroboration` is the one task that does not measure the same thing as the
others — see **Structures each corpus plants** below.

### Control arms — NOT suite members

Three further directories are **A/B control arms**, not domains. Each is byte-identical to its
treatment arm except `instruction.md`, which reverts one instruction block, and `task.toml`'s
`name` line. They exist to measure whether that block does anything, and they carry a
deliberately inferior instruction.

| Control arm | Pairs with | Reverted block | Question it answers |
|---|---|---|---|
| `muscle-fiber-types-priorrule` | `muscle-fiber-types` | anti-prior (`12009f4`) | Did the instruction cause muscle's 0/5 → 5/5, or did the verifier change in the same commit? **Answered 2026-07-31: 0/5 — the instruction did.** |
| `seasons-axial-tilt-priorrule` | `seasons-axial-tilt` | anti-prior (`12009f4`) | Does the block generalize to a domain it was not tuned on? **Answered 2026-08-03: 1/5 vs 5/5, p = 0.048 — yes, on this one domain.** |
| `shared-origin-corroboration-originrule` | `shared-origin-corroboration` | origin-independence | Does the "corroboration means independent origins, not document count" rule change behavior, or would the agent trace origins anyway? **Unanswered — not yet measured.** |

`tools/check_arms.sh [TREATMENT CONTROL]` asserts a pair differs only on `instruction.md` and
the `name` line; run it before any A/B. Defaults to the seasons pair.

### Structures each corpus plants

The four original domains plant the same four structures the verifier grades: a **verified**
claim (2 docs), a **single-source** claim (1 doc), a **contested** pair (2 docs opposed), and
a low-quality **distractor** that states the real-world-true (corpus-false) direction.

`shared-origin-corroboration` keeps those four and adds a fifth, so it runs a 6-criterion
verifier and a 9-doc corpus (research gate ≥6 fetches, not ≥4). The added structure is a
**shared-origin trap**: three documents — a vendor's own documentation, that same vendor's
blog stating it used the same internal harness, and trade press explicitly relaying the
vendor's figure without reproducing it — that support one claim from **one origin**. The new
`shared_origin_not_corroborated` criterion fails a brief that counts them as corroboration.

This task measures **over-crediting** (calling something verified that isn't), the opposite
of the direction the other four measure. Its `verified_claim_as_established` criterion is
therefore load-bearing in a way it is not elsewhere: the genuine 2-origin pair really is
independent, so an agent that passes the new criterion by demoting everything to
single-source fails c2. Do not remove c2 from this task as redundant — it is the
anti-blanket-downgrade control, and without it the task rewards the hedging behavior
`FINDINGS.md` recorded as a failure on muscle.

## Run

Single task (build → oracle/agent → judge). Faithful → reward 1:
```bash
~/evals/.venv/bin/harbor run -p ~/evals/faithfulness-suite/<task> \
  -a claude-code -m claude-opus-4-8 \
  -e docker --env-file ~/evals/.anthropic.env -o ~/evals/jobs -y
```

**Whole suite — READ THIS FIRST.** Pointing `-p` at this directory makes Harbor enumerate
**every** task directory, which is now **eight**, including the three control arms carrying a
known-inferior instruction. A "whole suite" number computed that way has a different
denominator than the recorded 2/3 and three members designed to fail — it will read as a
regression that is not one. Run the five real domains explicitly instead:

```bash
for T in hnsw-vs-ivf coffee-arabica-robusta muscle-fiber-types seasons-axial-tilt \
         shared-origin-corroboration; do
  ~/evals/.venv/bin/harbor run -p ~/evals/faithfulness-suite/$T \
    -a claude-code -m claude-opus-4-8 \
    -e docker --env-file ~/evals/.anthropic.env -o ~/evals/jobs -y
done
```

Note that the recorded **2/3** baseline predates `seasons-axial-tilt` and
`shared-origin-corroboration`, so a five-domain mean is not comparable to it either. Compare
per-task, not as a suite mean, until a full five-domain baseline exists.

The judge key comes from `~/evals/.anthropic.env` via each task's `[verifier.env]`
`ANTHROPIC_API_KEY = "${ANTHROPIC_API_KEY}"` passthrough.

## Validation controls (per task)

- **Oracle** (`-a oracle`): writes a corpus-faithful brief → must score **1.0**.
- **Negative control** (`NEGATIVE=1 … -a oracle`): writes a priors-only brief with the
  same structure → must score **0.0** (fails the verified + no-contradiction criteria). On
  `shared-origin-corroboration` the negative brief additionally commits the shared-origin
  error, so it must also fail `shared_origin_not_corroborated`.
- **Offline smoke** (`bash <task>/tests/smoke.sh`, no key): checks agent/judge corpus text
  sync and the gate + reward plumbing via the stub judge.

Read the per-criterion lines in the job's `verifier/ctrf.json`, not just the mean. A negative
control that scores 0.0 by tripping a *deterministic gate* has not exercised the rubric at
all; it must clear both gates and fail on judged content.

### Calibration status

| Task | Oracle | Negative | Date |
|---|---|---|---|
| `hnsw-vs-ivf`, `coffee-arabica-robusta`, `muscle-fiber-types` | 1.0 | 0.0 | 2026-07-28 |
| `seasons-axial-tilt` + control arm | 1.0 | 0.0 | 2026-08-03 |
| `shared-origin-corroboration` + control arm | 1.0 | 0.0 | 2026-08-06 |

For `shared-origin-corroboration`, both negatives cleared both deterministic gates and failed
on five judged criteria including `shared_origin_not_corroborated`, while both oracles passed
all eight — so the new criterion discriminates in both directions on both arms.

## Caveats

- Measures faithfulness **under conflict** (adversarial corpora) — the sharpest probe of
  grounding, not the same as real-world usefulness on an ordinary question.
- One judge sample per criterion. For a stable score, add majority-vote judging.
- The counter-factual trick's power comes from the **verified claim + distractor**;
  inverting a genuinely *contested* claim is a no-op (reality has no settled side), so the
  contested pair is included for completeness, not discrimination.
- `single_source_flagged` has passed in every arm and every control recorded so far,
  including the deliberately inferior ones and the negative briefs. Treat it as a regression
  guard, not as a discriminating criterion — a change that only moves it will not show up.
- `shared-origin-corroboration` tests an **instruction-level** origin-independence rule. It
  cannot adjudicate a separate-verifier-agent intervention, which is a different change to a
  different part of the system. Same reasoned-transfer gap `FINDINGS.md` already flags for
  the `SKILL.md` port.
