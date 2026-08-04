# Status — seasons held-out arm

Last updated 2026-07-31. Written at the end of the build session; nothing has been run yet.

## Where things stand

Built and committed (`8017190`, `d64aa93`, `15f6d33`, `1bee58c`, `f4fb505`): two Harbor arms,
the arm-identity guard, the spec, the plan, the run sheet, and a correction to `FINDINGS.md`.

**Nothing has been measured.** No harbor run of any kind has executed against these files.

## Verified vs assumed — read this before trusting anything

| Claim | Status |
|---|---|
| Arms are byte-identical except `instruction.md` and `task.toml`'s name line | **Verified** — `tools/check_arms.sh` exits 0; 11 files per arm |
| Arms differ on exactly the intended axis | **Verified** — treatment carries all four rationalizations, the sky-is-green example and the corroboration clause; control carries none and has the pre-fix wording instead |
| Agent and judge corpora agree; no metadata leak | **Verified** — programmatic check, both arms |
| Treatment `instruction.md` matches the shipped fix | **Verified** — identical to all three sibling tasks apart from the topic sentence |
| Deterministic gates (headings, ≥4 docs fetched) behave correctly | **Verified** — the real verifier logic run against real fixtures with a stubbed judge; oracle passes, 1-fetch trajectory correctly fails the research gate |
| Negative control reaches the judge rather than short-circuiting on structure | **Verified** — it clears both gates and scores 1 under `stub:pass`, so only judge content can fail it |
| Oracle scores 1.0 and negative scores 0.0 under the **live** judge | **ASSUMED** — simulated by a reviewer, never run |
| `task.toml` validates against the installed Harbor schema | **ASSUMED** — never run; the venv is unreachable from any Claude session |
| The full pytest smoke suite passes | **ASSUMED** — no PyPI access from the bridge or the cloud container |

## Next steps, in order

**1. Smoke both arms + validate schemas.** Free. Never executed.
```bash
cd ~/evals/faithfulness-suite
bash seasons-axial-tilt/tests/smoke.sh
bash seasons-axial-tilt-priorrule/tests/smoke.sh
~/evals/.venv/bin/python - <<'PY'
from harbor.models.task.task import Task
import tomllib, pathlib
for arm in ("seasons-axial-tilt", "seasons-axial-tilt-priorrule"):
    Task.model_validate(tomllib.loads((pathlib.Path.home()/"evals/faithfulness-suite"/arm/"task.toml").read_text()))
    print(f"{arm}: validates")
PY
```

**2. ~~The muscle control~~ — DONE 2026-07-31, `jobs/2026-07-31__12-09-47`. Result: 0/5.**
The rubric change carried none of muscle's 0/5 → 5/5; it is a genuine instruction effect and
the seasons comparisons to it are sound. See FINDINGS.md "RESOLVED". Failure was localised to
the verified-claim axis; single-source and contested passed 5/5.
`FINDINGS.md`'s correction explains why: `12009f4` changed the instruction *and* the verifier,
so 0/5 → 5/5 mixes both effects. Build `muscle-fiber-types-priorrule` the way the seasons
control was built (muscle's `6afce54` instruction, everything else current) and run it `-k 5`
under today's 5-criterion verifier. If the rubric change carried much of that swing, the
seasons result gets interpreted very differently — so this comes first.

**3. Calibrate seasons, ~$0.20.** Oracle both arms (expect 1.0), `NEGATIVE=1` both arms
(expect 0.0). Stop only if a value is absolutely wrong. The arms disagreeing *with each other*
is judge sampling noise, not contamination — there is no contamination channel for an agent
that never reads `instruction.md`.

**4. Measure, ~$2.90.** `-k 5` both arms. Record all five per-criterion booleans, not rewards
— leak vs hedge lives in `conveyed` against `as_established`.

**5. Apply the pre-registered table in `docs/plans/RUN-seasons.md` without improvising.**
Particularly the row saying `(control 1, treatment 4)` means nothing — Fisher p = 0.206.

**Optional, ~$1:** majority-vote judging (3 samples/criterion). Reward is an AND of five
single-sample booleans at n=5; two judge flips turn a real 5/5 into 3/5 and drain the result
into "no conclusion."

## Open findings

**Structural — caps what any result licenses.**
- The corpus is held out. The rubric, the c2 criterion wording (written in the fix's own
  commit, and it explicitly blesses the fix's output form), and the four-rationalization
  taxonomy the seasons corpus was authored against are **not**. A clean win supports ~0.75–0.80
  that the block transfers to unseen corpora *graded by this rubric*; not above ~0.5 that it
  improves real grounding discipline.
- Judge and agent are both `claude-opus-4-8`. Self-preference is documented for pairwise
  preference; whether it transfers to boolean rubric grading of a single artifact is untested.
- The oracle's verified-claim bullet shares "secondary amplitude term" verbatim with the
  rubric's c1 wording (both paraphrase doc_a). The hnsw sibling has the same property. So
  calibration proves a near-verbatim faithful brief passes — not that a looser one does.

**Suite hygiene — act before the next full-suite run.**
- `-p ~/evals/faithfulness-suite` now enumerates **5** tasks including
  `seasons-axial-tilt-priorrule`, an arm deliberately carrying a known-inferior instruction.
  The next suite number would have a different denominator with a poisoned member and would
  read as a regression against the recorded 2/3. Document both arms in the README table, or
  nest them so Harbor stops enumerating them as suite members.
- `HANDOFF.md` is still untracked. It is the best documentation in the repo.

**Minor, for triage.**
- doc_a/doc_c concluding sentences are close paraphrases — corroboration leans
  parallel-restatement rather than two distinct evidentiary routes. Only doc_a *reads* as
  authoritative, and the treatment instruction conditions its override on "2+, authoritative."
- doc_b's voice is the weakest fit for its `authoritative` label.
- The faithful oracle makes one inference no single doc states ("the corpus already attributes
  hemispheric opposition to obliquity").
- Both arms' `instruction.md` promises `corpus search` returns a `snippet`; `corpus_cli.py`
  prints id + title only. Inherited from all three siblings, identical in both arms, so no
  confound — but the prompt is lying about its own tool inside a faithfulness eval.
- The guard's `require_pair` labels present-but-uncomparable paths (a directory in place of a
  file) as "MISSING"; diagnostic wording only, fails closed correctly.
- `diff -r -x` matches basenames at any depth, so an `instruction.md` planted under
  `environment/` or `tests/` would be silently excluded from Check A. Not currently violated.

## Environment gotchas — for any future session

These cost real time to rediscover:

- **Git through the device bridge is one-shot.** The bridge refuses all deletes, so every git
  command leaves `.git/index.lock` behind and the *next* one fails with "Another git process
  seems to be running." Even a read-only `git status` does it. Run git yourself, or clear the
  lock between commands.
- **No PyPI** from the device bridge *or* the cloud container, so `uv run --with pytest` fails
  and `harbor` cannot be installed anywhere. The pytest half of every smoke test in this suite
  is unrunnable from a Claude session — the pre-existing sibling tasks fail identically.
- **`~/evals/.venv` is a macOS Homebrew venv**; `device_bash` is a Linux aarch64 VM, so
  `.venv/bin/python` is a broken symlink there. Harbor cannot be run *or* schema-validated
  from a Claude session, independent of the guard hook.
- **The guard hook** (`~/Developer/vcguru/.claude/hooks/guard.sh`) blocks any command
  containing `.env`, `.key`, `.pem`, `credentials`, plus destructive deletes and `git push`.
  Every harbor invocation needs `--env-file`, so all harbor runs are the user's.
- **Harbor copies `~/.claude/skills` into the agent config** — but inside the container, so
  the live `become-expert` skill does not leak in. Confirmed: `lock.json` shows `"skills": []`
  and all 30 archived trials have an empty skills dir. This becomes live the moment anyone
  passes `--skill` or bakes skills into the image, and it would silently hand the control arm
  the treatment.
