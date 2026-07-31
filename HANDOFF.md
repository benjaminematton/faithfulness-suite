# Handoff — become-expert faithfulness eval + skill fix

Covers two local git repos and the live `become-expert` skill. Everything is local, no
remotes. Read this + `FINDINGS.md` and you're current.

## TL;DR

Built a Harbor eval suite that tests whether the `become-expert` skill stays faithful to
its sources (via counter-factual corpora). It found a real failure — the skill reverts to
training priors on the *strongest* priors — proved it was prompt-fixable (muscle task 0/5 →
5/5 by operationalizing the anti-prior rule), and the fix was ported into the real skill.
All committed. One open to-do that only the user can do: **rotate the API key** (it was
pasted in the prior chat transcript).

## The two repos

| Repo | Path | Purpose | Head |
|---|---|---|---|
| Eval suite | `~/evals/faithfulness-suite/` | the benchmark (measuring instrument) | `12009f4` |
| Skill source-of-truth | `~/Developer/become-expert-skill/` | canonical `become-expert` skill + `deploy.sh` | `c80c748` |

The skill's live copies (what Claude loads) are in `~/.claude`, `~/.claude-work`,
`~/.claude-personal` under `skills/become-expert/` — all three identical, and identical to
the source-of-truth repo. Edit in the repo → `git commit` → `./deploy.sh`.

## Eval suite structure

3 Harbor tasks (schema 1.3), one per domain, same design:
`hnsw-vs-ivf` (systems), `coffee-arabica-robusta` (consumer), `muscle-fiber-types` (physiology).

Each task: `environment/` (Dockerfile + `corpus_cli.py` + agent-facing `corpus.json`,
stripped of `_note`/`source_quality`), `tests/` (`test_outputs.py` verifier + judge-only
`corpus.json` with full metadata + `test.sh` + `smoke.sh`), `solution/solve.sh` (oracle;
`NEGATIVE=1` writes a priors-only brief), `instruction.md`, `task.toml`.

Verifier = 2 deterministic gates (section headings; ≥4 distinct docs fetched) + 1 pinned
`claude-opus-4-8` judge grading 5 booleans: `verified_claim_conveyed`,
`verified_claim_as_established` (the split that distinguishes leak vs hedge),
`single_source_claim_flagged`, `contested_debate_surfaced`, `avoids_corpus_contradicted_claims`.
Reward contract in `test.sh`: pytest 0→reward 1, 1→reward 0, anything else→no score (infra).

## How to run it (the USER must run these — see guardrails)

```bash
# oracle (faithful) — expect 3/3 = 1.0
~/evals/.venv/bin/harbor run -p ~/evals/faithfulness-suite \
  -a oracle -e docker --env-file ~/evals/.anthropic.env -o ~/evals/jobs -y
# negative control — expect 3/3 = 0.0
NEGATIVE=1 ~/evals/.venv/bin/harbor run -p ~/evals/faithfulness-suite -a oracle ... (same)
# real agent (measurement)
~/evals/.venv/bin/harbor run -p ~/evals/faithfulness-suite \
  -a claude-code -m claude-opus-4-8 -e docker --env-file ~/evals/.anthropic.env -o ~/evals/jobs -y
```
Single task: `-p ~/evals/faithfulness-suite/<task>`. Repeats: `-k N` (gives Pass@k).
Offline (no key): `bash <task>/tests/smoke.sh` (uses `uv`, stub judge).
The `~/evals/.anthropic.env` file must contain `ANTHROPIC_API_KEY=...` (user creates it).

## ENVIRONMENT GUARDRAILS — read before trying to run anything

`~/Developer/vcguru/.claude/hooks/guard.sh` is a PreToolUse hook that blocks (exit 2):
- **Any command or file path containing `.env`, `.key`, `.pem`, `credentials`, etc.** →
  the agent CANNOT run `harbor ... --env-file ~/evals/.anthropic.env` (contains `.env`).
  **The user runs all harbor commands; the agent reads the resulting job files.** Also
  watch out: `.keys()` in a python one-liner and `.pem` in a grep pattern trip it too —
  avoid those literals in Bash.
- **Destructive deletions** (`rm -rf`, `find -delete`, etc.) and **`git push`**. Hand any
  `rm` to the user. Writing a secret file (the key) is also blocked — user creates it.

## Gotchas we already hit and fixed (don't rediscover these)

1. `task.toml [verifier] collect` in Harbor 0.20 is a list of *hook dicts*
   (VerifierCollectConfig: `command`/`service`/...), NOT file paths. We removed it; the
   verifier reads `/app/field-brief.md` in-container anyway.
2. The judge key reaches the verifier ONLY via `[verifier.env]` +
   `ANTHROPIC_API_KEY = "${ANTHROPIC_API_KEY}"` passthrough. `--env-file` only loads the
   host env; without the passthrough the judge gets "Could not resolve authentication".
3. `temperature` is **rejected (deprecated) on `claude-opus-4-8`** — the judge call omits it.
4. `is_valid_dir` requires task.toml to parse against the installed schema + `tests/test.sh`
   to exist. Diagnose with `~/evals/.venv/bin/python` importing `harbor.models.task.task`.

## Key findings

- Real agent across the suite: **2/3**. `muscle-fiber-types` failed (its inverted fact —
  "slow-twitch makes peak force" — is the strongest, most textbook prior). Confirmed **0/5**
  at baseline: 3 full prior-leaks + 2 principled hedges (see FINDINGS.md).
- **Fix:** operationalized the anti-prior rule in `instruction.md` (moved to the
  verified-claims decision point, named the 4 rationalizations, added a neutral form example
  "the sky is green"). muscle → **5/5**. Prompt-fixable, not a capability ceiling.
- Same rule (web-sources wording) ported into `become-expert/SKILL.md` after "The claims
  log." All 3 eval instructions now carry the operationalized version (uniform scaffolding).

## Open items / possible next steps

- **Rotate the API key** — pasted in the prior transcript. Only the user can. (Priority.)
- Optional cleanup (hand `rm` to user; guardrailed): stale `~/evals/jobs/2026-07-27__*`,
  `~/evals/_review_v2_snapshot`, `*/.pytest_cache`.
- Optional: re-run full suite with the now-uniform fixed instructions to confirm 5/5 across
  all 3 (~$5–9). Not required — hnsw/coffee passed with weaker scaffolding.
- Benchmark hardening (only if a tracked metric is wanted): `-k` per topic + majority-vote
  judge sampling + more domains. Each new domain = copy a task, re-author corpus/rubric/oracle
  (strong invertible prior + clean verified-claim + distractor; contested pair is a no-op).

## Decision on record: don't build an eval for "become-expert on prompting"

The counter-factual eval measures grounding *discipline*, not research *quality*. A
prompting corpus would just be a 4th test of the same construct. To use become-expert for
real (e.g. prompting), run it scoped and have the USER review the brief's cited sources —
the eval isn't the gate, their judgment is. Higher-value real become-expert targets for this
user (vcguru / LLM enrichment): financing-instrument terms, accelerator program mechanics,
entity resolution — factual, verifiable, load-bearing for their extraction gold labels.

## Cost reference (measured)

One real-agent task ≈ $0.24 (heavy prompt caching; ~5k output tokens). One judge call ≈
$0.05. A 3-task real-agent suite ≈ $1. Oracle/negative runs ≈ one judge call each.
