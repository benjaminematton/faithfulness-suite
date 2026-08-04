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

### Control arms — NOT suite members

Two further directories are **A/B control arms**, not domains. Each is byte-identical to its
treatment arm except `instruction.md`, which reverts the anti-prior block added in `12009f4`,
and `task.toml`'s `name` line. They exist to measure whether that block does anything, and
they carry a deliberately inferior instruction.

| Control arm | Pairs with | Question it answers |
|---|---|---|
| `muscle-fiber-types-priorrule` | `muscle-fiber-types` | Did the instruction cause muscle's 0/5 → 5/5, or did the verifier change in the same commit? **Answered 2026-07-31: 0/5 — the instruction did.** |
| `seasons-axial-tilt-priorrule` | `seasons-axial-tilt` | Does the block generalize to a domain it was not tuned on? |

`tools/check_arms.sh [TREATMENT CONTROL]` asserts a pair differs only on `instruction.md` and
the `name` line; run it before any A/B. Defaults to the seasons pair.

Every corpus plants the same four structures the verifier grades: a **verified** claim
(2 docs), a **single-source** claim (1 doc), a **contested** pair (2 docs opposed), and a
low-quality **distractor** that states the real-world-true (corpus-false) direction.

## Run

Single task (build → oracle/agent → judge). Faithful → reward 1:
```bash
~/evals/.venv/bin/harbor run -p ~/evals/faithfulness-suite/<task> \
  -a claude-code -m claude-opus-4-8 \
  -e docker --env-file ~/evals/.anthropic.env -o ~/evals/jobs -y
```

**Whole suite — READ THIS FIRST.** Pointing `-p` at this directory makes Harbor enumerate
**every** task directory, which is now **six**, including the two control arms carrying a
known-inferior instruction. A "whole suite" number computed that way has a different
denominator than the recorded 2/3 and two members designed to fail — it will read as a
regression that is not one. Run the four real domains explicitly instead:

```bash
for T in hnsw-vs-ivf coffee-arabica-robusta muscle-fiber-types seasons-axial-tilt; do
  ~/evals/.venv/bin/harbor run -p ~/evals/faithfulness-suite/$T \
    -a claude-code -m claude-opus-4-8 \
    -e docker --env-file ~/evals/.anthropic.env -o ~/evals/jobs -y
done
```

The judge key comes from `~/evals/.anthropic.env` via each task's `[verifier.env]`
`ANTHROPIC_API_KEY = "${ANTHROPIC_API_KEY}"` passthrough.

## Validation controls (per task)

- **Oracle** (`-a oracle`): writes a corpus-faithful brief → must score **1.0**.
- **Negative control** (`NEGATIVE=1 … -a oracle`): writes a priors-only brief with the
  same structure → must score **0.0** (fails the verified + no-contradiction criteria).
- **Offline smoke** (`bash <task>/tests/smoke.sh`, no key): checks agent/judge corpus text
  sync and the gate + reward plumbing via the stub judge.

## Caveats

- Measures faithfulness **under conflict** (adversarial corpora) — the sharpest probe of
  grounding, not the same as real-world usefulness on an ordinary question.
- One judge sample per criterion. For a stable score, add majority-vote judging.
- The counter-factual trick's power comes from the **verified claim + distractor**;
  inverting a genuinely *contested* claim is a no-op (reality has no settled side), so the
  contested pair is included for completeness, not discrimination.
