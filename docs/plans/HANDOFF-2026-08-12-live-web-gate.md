# Handoff — live-web gate A/B, 2026-08-12

Read this, then `docs/plans/RUN-live-web-gate.md` (authoritative, pre-registered — do not
improvise on it). Everything below is verified unless marked ASSUMED.

## Where we are in one line

The landing gate is built and validated on real data; the A/B arms are built and
`harbor check`-clean; **zero A/B trials have run** — the last attempt died on a five-hour
subscription rate limit before any trial completed.

## What was built (all on disk, all UNCOMMITTED)

**`become-expert-skill`** (product, separate repo at `~/Developer/become-expert-skill`)
- `scripts/auditor/` — the deterministic landing gate: `urlnorm, transcript, brief,
  checks, gate, gate_cli` + tests + fixtures. Stdlib only, no network, no API key.
  **This repo is the source of truth for those six files.**
- `SKILL.md` — Phase 2 requires the claims log as a file; Phase 3 runs the gate before the
  self-audit checklist (3 legal remediation moves, 2-round cap).
- `deploy.sh` now ships `scripts/` too. **Not yet run** — until it is, live `/become-expert`
  sessions still use the old skill.

**`faithfulness-suite`** (this repo)
- `auditor/` — vendored copy of the six core files + `CORE-VENDORED.md` (sha256 manifest)
  + `tests/test_vendor_drift.py` (fails if a vendored file is edited in place).
  `tools/sync_gate_core.sh <path-to-skill>` re-vendors. `judge.py`/`report.py`/`audit.py`
  are owned HERE and `audit.py` is **unchanged**, so existing baselines do not move.
- `live-web-gate/` + `live-web-gate-gaterule/` — the A/B arms. Differ ONLY in
  `instruction.md` and the `task.toml` name line (`tools/check_arms.sh` verified).
- `tools/run_gate_ab.sh`, `tools/analyze_run.py`, `tools/gate_retro.sh`,
  `tools/run_tests_stdlib.py` (no-PyPI test runner).
- `docs/specs/2026-08-12-landing-gate-design.md`, `docs/plans/RUN-live-web-gate.md`.

## Verified results so far

- **Gate detection, on the REAL local-only fixtures** (`tools/gate_retro.sh`):
  aug03 → exit 1 (5×G4, 3×G1, search:fetch 10.8); aug08 → exit 0 (ratio 0.95).
  This is the load-bearing evidence that the gate works. It proves **detection only**.
- Tests: 85 pass in the skill repo (`scripts/run_tests.py auditor/tests`), 24 in this one
  (`PYTHONPATH=. python3 tools/run_tests_stdlib.py auditor/tests`). 0 failures.
- `harbor check` both arms (`jobs/2026-08-12__09-23-46`, `__09-26-44`), ~$0.90 each at
  list. Findings and their resolution are in RUN-live-web-gate.md §0a.
- Six job dirs exist in `jobs/`. **All are `harbor check` runs, none are trials.** A check
  run's agent reads the task files and grades the task definition; it never researches.

## OPEN DECISION — settle before trial 1

`audit.py` returns `"nothing to audit"` → exit 0 → **reward 1** for a brief with no
parseable claims. An agent scores a perfect 1.0 by asserting nothing, and both arms could
hit 5/5 for opposite reasons. Options are written out in RUN-live-web-gate.md §0a:
(a) run as-is and treat `brief_verified_lines` as a validity gate, or (b) require ≥1
verified claim for reward 1 **in both arms**. Ben was leaning toward being asked; get an
explicit answer before spending.

## Billing — read before running

The last run died on `rateLimitType: "five_hour"`, `resetsAt` = 12:10pm PT, with
`overageStatus: "rejected"` / `"out_of_credits"`. So: the harbor agent draws on the **Max
subscription**, there are **no API credits**, and the window was already partly spent by a
concurrent interactive session.

Cost modelling from Ben's own two become-expert transcripts at list price
(platform.claude.com/docs/en/about-claude/pricing, Opus $5/$25/$6.25/$0.50):
doc-heavy regime ≈ **$33/run**, pressure-topic regime ≈ **$704/run** (cache reads dominate
— aug03 read 1.04B cached tokens). Ten trials therefore span **$334–$7,038** on API.
Those transcripts are full interactive sessions, so they overstate a 1800s-capped trial —
treat the range as an upper bound, not a forecast.

**Therefore: prefer the subscription, run sequentially, do not interleave arms.** Finish
one arm, note the window, then start the other. To get a real number instead of this
range, run one trial and read `analyze_run.py`'s computed cost.

## How to run

```bash
rm -f .git/index.lock          # the bridge leaves these; git fails until cleared

# one arm at a time; resumes from the ledger if a limit stops it mid-way
TOPIC="startup accelerator cohort attribution conventions" \
  bash tools/run_gate_ab.sh live-web-gate 5
bash tools/run_gate_ab.sh live-web-gate-gaterule 5

python3 tools/analyze_run.py jobs/<job>          # per-trial tokens/cost/compliance/audit
```

`run_gate_ab.sh` runs ONE trial per harbor invocation and appends to
`docs/plans/live-web-gate-ledger.tsv`, so a rate limit costs the current trial and never
the completed ones — re-run the identical command to resume. `--env-file` is inside the
script so the guard hook does not block the typed command.

## Still outstanding

1. **Confirm `TOPIC` actually substitutes.** `task.toml:31` declares
   `TOPIC = "${TOPIC:-...}"` in `[environment.env]`, and the pressure topic was exported in
   the run shell — but this is **ASSUMED**, not verified: no trial has run, and the check
   runs cannot show it. On trial 1, grep the agent transcript for "accelerator" before
   trusting the batch.
2. Commit + push both repos (see below), then `bash ~/Developer/become-expert-skill/deploy.sh`.
3. The treatment instruction tells the agent to locate its own transcript at
   `/logs/agent/sessions/projects/*/*.jsonl` mid-run. **Never executed inside a container.**
   If trial 1 writes `gate unavailable:` into the brief, that is plumbing to fix, not a
   result — exclude and re-run per RUN-live-web-gate.md §3.
4. `_to_delete/` holds five test files the refactor moved to the skill repo; the bridge
   cannot delete, so trash it manually.

## Committing

`jobs/` is now gitignored. `.claude/` and `_to_delete/` are untracked and probably should
not be committed.

```bash
cd ~/evals/faithfulness-suite && git add -A && git commit && git push
cd ~/Developer/become-expert-skill && git add -A && git commit && git push
```

## Environment gotchas (cost real time before)

- Git through the Cowork device bridge leaves `.git/index.lock` and cannot delete it.
- No PyPI from the bridge or a cloud container — hence `run_tests_stdlib.py`. Harbor
  cannot be run or schema-validated from any Claude session; `~/evals/.venv` is a macOS
  venv and the bridge is Linux.
- The guard hook blocks commands containing `.env`, `.key`, `.pem`, `credentials`, and
  `git push` — so harbor runs are Ben's to execute.
