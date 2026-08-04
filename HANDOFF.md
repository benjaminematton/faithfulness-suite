# Handoff — become-expert faithfulness suite

Supersedes the 2026-07-28 handoff. Read this plus `FINDINGS.md` and you are current.
Everything is local, no git remotes.

## TL;DR

A Harbor benchmark measuring whether the `become-expert` skill stays faithful to its sources
when they contradict what the model already believes. It found a real failure (the skill
reverts to priors on the strongest priors), a prompt fix was applied, and **as of 2026-08-03
that fix has survived two independent controls**:

- `muscle-fiber-types-priorrule` → **0/5**. The original 0/5 → 5/5 was a genuine instruction
  effect, not the verifier change made in the same commit.
- `seasons-axial-tilt` A/B → **control 1/5, treatment 5/5, Fisher p = 0.048**. The fix
  transfers to a domain it was never tuned on.

The fix stays in `SKILL.md`. What it buys is bounded — see "What this does not license".

## The two repos

| Repo | Path | Purpose | Head |
|---|---|---|---|
| Eval suite | `~/evals/faithfulness-suite/` | the benchmark | `a74ca14` |
| Skill source of truth | `~/Developer/become-expert-skill/` | canonical skill + `deploy.sh` | `c80c748` |

Live skill copies are in `~/.claude`, `~/.claude-work`, `~/.claude-personal` under
`skills/become-expert/`. Edit in the repo → commit → `./deploy.sh`.

## What the suite contains

**Four domains.** Each is a counter-factual 6-doc corpus whose headline fact is inverted
versus reality, so a brief written from training priors contradicts the corpus and fails. Only
genuine reading passes. Every corpus plants the same four structures: a **verified** claim (2
docs), a **single-source** claim (1 doc), a **contested** pair (2 opposed), and a low-quality
**distractor** stating the real-world-true direction.

`hnsw-vs-ivf` · `coffee-arabica-robusta` · `muscle-fiber-types` · `seasons-axial-tilt`

**Two A/B control arms — not suite members.** Each is byte-identical to its treatment arm
except `instruction.md` (reverting the anti-prior block from `12009f4`) and `task.toml`'s name
line. They carry a deliberately inferior instruction and exist only to measure the block.

`muscle-fiber-types-priorrule` · `seasons-axial-tilt-priorrule`

**`tools/check_arms.sh [TREATMENT CONTROL]`** asserts a pair differs only on `instruction.md`
and the name line. Run it before any A/B. Defaults to the seasons pair. It fails closed: a
missing file is a failure, never a silent pass.

**Verifier** (identical across all six): 2 deterministic gates (five section headings; ≥4
distinct docs fetched per the trajectory) + 1 pinned `claude-opus-4-8` judge grading 5
booleans. `verified_claim_conveyed` vs `verified_claim_as_established` is the split that
separates a full prior-leak from a responsible hedge — that distinction is the diagnostic
value of the whole suite, so always record per-criterion booleans, never just the reward.

**Reward contract** (`tests/test.sh`): pytest 0 → reward 1; pytest 1 → reward 0; anything else
→ **no score written**. This is load-bearing. On 2026-08-03 an expired API key produced
`RewardFileNotFoundError` and zero trials instead of four clean 0.0s — without the contract
you would have recorded a perfect-looking negative control against a dead judge.

## Results to date

| Run | Job | Result |
|---|---|---|
| Suite, real agent (3 domains, pre-fix) | 2026-07-28 | 2/3 — muscle failed |
| muscle baseline, `-k 5` | `2026-07-28__20-07-17` | 0/5 (3 leak, 2 hedge) |
| muscle post-fix, `-k 5` | `2026-07-28__20-45-29` | 5/5 |
| **muscle control** (pre-fix instr, current verifier) | `2026-07-31__12-09-47` | **0/5** — rubric change carried none of the swing |
| seasons oracle / negative, both arms | `2026-08-03__21-12…21-13` | 1.0 / 1.0 / 0.0 / 0.0 — calibrated |
| **seasons treatment**, `-k 5` | `2026-08-03__21-16-02` | **5/5**, every criterion every trial |
| **seasons control**, `-k 5` | `2026-08-03__21-20-22` | **1/5** — all 4 failures on c2 alone |

The seasons control produced **0 prior-leaks and 4 responsible hedges**: it always relayed the
corpus claim, then refused to call it established. That is exactly the third rationalization
the fix names. It never endorsed the distractor (c5 passed 5/5).

## What this does not license

- **p = 0.048 is the weakest cell in the pre-registered validated band.** One more control
  pass drops it to "no conclusion". One experiment at n=5, not a settled effect size.
- **Seasons exercised only the hedge failure mode.** Muscle produced leaks too. This validates
  one of the fix's four named rationalizations, not all four.
- **The corpus was held out; the rubric was not.** The c2 wording was written in the fix's own
  commit and permits attribution phrasing of the form the fix produces, and the seasons corpus
  was authored by someone who knew the four rationalizations. Reasonable credence: ~0.75–0.80
  that the block transfers to unseen corpora *graded by this rubric*; not past ~0.5 that it
  improves real grounding discipline on ordinary questions.
- **Single judge sample per criterion**, default temperature, same model family as the agent.

## How to run it — the USER runs all harbor commands

```bash
# one task
~/evals/.venv/bin/harbor run -p ~/evals/faithfulness-suite/<task> \
  -a claude-code -m claude-opus-4-8 -e docker --env-file ~/evals/.anthropic.env -o ~/evals/jobs -y

# repeats: -k N   |   oracle: -a oracle   |   negative control: NEGATIVE=1 ... -a oracle
# offline plumbing, no key: bash <task>/tests/smoke.sh
```

**Do NOT point `-p` at the suite directory.** Harbor enumerates every task dir — now six,
including the two deliberately-inferior control arms. Loop the four real domains explicitly
(see `README.md`).

Before any A/B: `./tools/check_arms.sh <treatment> <control>` must exit 0.

## Environment guardrails and gotchas

**Claude sessions cannot run harbor. Three independent reasons:**
1. `~/Developer/vcguru/.claude/hooks/guard.sh` blocks any command containing `.env`, `.key`,
   `.pem`, `credentials`, plus destructive deletes and `git push`. Every harbor run needs
   `--env-file`.
2. `~/evals/.venv` is a macOS Homebrew venv; the Cowork device bridge is a Linux aarch64 VM,
   so `.venv/bin/python` is a broken symlink there.
3. No PyPI from the bridge *or* the Cowork cloud container, so `uv run --with pytest` fails and
   `harbor` cannot be installed anywhere. The pytest half of every `smoke.sh` is unrunnable
   from a Claude session — pre-existing, all tasks.

**Git through the device bridge is one-shot.** The bridge refuses all deletes, so any git
command leaves `.git/index.lock` behind and the next one fails with "Another git process seems
to be running." Even read-only `git status` does it. Run git yourself, or clear the lock
between commands. Same reason a Claude session can never `rm` anything on this machine — hand
deletions to the user.

**Harbor specifics already hit and fixed — don't rediscover:**
- `[verifier] collect` in Harbor 0.20 is a list of hook dicts, not file paths. Removed; the
  verifier reads `/app/field-brief.md` in-container.
- The judge key reaches the verifier ONLY via `[verifier.env]` + `ANTHROPIC_API_KEY =
  "${ANTHROPIC_API_KEY}"` passthrough. `--env-file` alone only loads the host env.
- `temperature` is rejected (deprecated) on `claude-opus-4-8`; the judge call omits it.
- `is_valid_dir` needs `task.toml` to parse against the installed schema and `tests/test.sh`
  to exist.
- Harbor copies `~/.claude/skills` into the agent config, but **inside** the container, so the
  live `become-expert` skill does not leak into trials (verified: `lock.json` shows
  `"skills": []`, 30 archived trials have an empty skills dir). **This becomes live the moment
  anyone passes `--skill` or bakes skills into the image** — and it would silently hand a
  control arm the treatment.

## Open items

- **Majority-vote judging (~$1).** Reward is an AND of five single-sample booleans at n=5; two
  judge flips drain a real result into "no conclusion".
- **A fifth domain that produces leaks, not hedges.** Seasons only exercised hedging.
- **`field-expert` collides with `become-expert`.** Measured: 12 ambiguous prompts, 7/7
  decisions between them turned on which trigger list happened to contain the user's literal
  phrase ("read up on" → become-expert, "learn everything about" → field-expert, "become an
  expert" → coin flip). `deep-research` separated cleanly, 5/5. No source repo or deploy
  script for `field-expert`, so `rm -rf ~/.claude*/skills/field-expert` holds — unless it is
  an account-synced skill, in which case remove it in the app.
- **Suite-level number is stale.** The recorded "2/3" predates seasons and the arms.

## Where the docs live

- `FINDINGS.md` — every result, with the 2026-07-31 correction and the seasons write-up
- `STATUS.md` — verified-vs-assumed table, open findings, environment gotchas
- `docs/specs/2026-07-31-seasons-heldout-arm-design.md` — why the A/B is shaped this way
- `docs/plans/2026-07-31-seasons-heldout-arm.md` — the build plan
- `docs/plans/RUN-seasons.md` — run sheet + the pre-registered decision table

## Cost reference (measured)

One real-agent task ≈ $0.24; one judge call ≈ $0.05. A `-k 5` arm ≈ $1.45. Oracle and negative
runs ≈ one judge call each. The full seasons A/B (calibration + both arms) cost ≈ $3.10 and
took about 11 minutes.
