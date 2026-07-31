# Run sheet — seasons held-out arm

Everything below must be run BY YOU. Two independent reasons no Claude session can do it:
the guard hook blocks any command containing `.env`, and `~/evals/.venv` is a macOS
Homebrew venv while the device bridge is a Linux VM, so `.venv/bin/python` is a broken
symlink there. This is structural, not a workaround away.

## 0. Cleanup + unblock git  (REQUIRED FIRST)

`tools/check_arms.sh.bak` is a working copy of the BUGGY pre-fix guard sitting next to the
real one. It must not be committed.

```bash
cd ~/evals/faithfulness-suite && \
  rm -f .git/HEAD.lock .git/index.lock .git/objects/maintenance.lock tools/check_arms.sh.bak && \
  find .git/objects -name 'tmp_obj_*' -delete && \
  rm -rf /tmp/seasons-scratch-task4 /tmp/check_arms_test /tmp/cas_fix \
         /tmp/test_outputs_original.py /tmp/edit_diff.patch
```

## 1. Verify what Claude could not

```bash
cd ~/evals/faithfulness-suite
./tools/check_arms.sh                      # expect 3x ok, "arms clean", exit 0
bash seasons-axial-tilt/tests/smoke.sh     # expect: corpus sync ok, metadata ok,
bash seasons-axial-tilt-priorrule/tests/smoke.sh   #   stub PASS, gate FAILS, "smoke OK"
```

The pytest half of smoke.sh has never been run — no PyPI access through the bridge. If it
fails on something other than the network, stop and read it before spending on harbor.

```bash
# Harbor schema validation (never executed — the venv is unreachable from the bridge)
~/evals/.venv/bin/python - <<'PY'
from harbor.models.task.task import Task
import tomllib, pathlib
for arm in ("seasons-axial-tilt", "seasons-axial-tilt-priorrule"):
    p = pathlib.Path.home()/"evals/faithfulness-suite"/arm/"task.toml"
    Task.model_validate(tomllib.loads(p.read_text()))
    print(f"{arm}: task.toml validates")
PY
```

## 2. Calibrate the instrument  (~$0.20)

```bash
for ARM in seasons-axial-tilt seasons-axial-tilt-priorrule; do
  ~/evals/.venv/bin/harbor run -p ~/evals/faithfulness-suite/$ARM \
    -a oracle -e docker --env-file ~/evals/.anthropic.env -o ~/evals/jobs -y
done
```
Expect **1.0 on both**. NOTE: this is a one-shot JUDGE-RELIABILITY probe, not a contamination
test. The oracle writes its brief directly and never reads `instruction.md`, so no
contamination channel exists for it; and the judge is sampled once at default temperature.
Divergence therefore means judge sampling noise — do NOT abort on it. Note it, and treat it as
evidence you want majority-vote judging.

```bash
for ARM in seasons-axial-tilt seasons-axial-tilt-priorrule; do
  NEGATIVE=1 ~/evals/.venv/bin/harbor run -p ~/evals/faithfulness-suite/$ARM \
    -a oracle -e docker --env-file ~/evals/.anthropic.env -o ~/evals/jobs -y
done
```
Expect **0.0 on both**.

**STOP if either control is wrong in ABSOLUTE terms** (oracle not 1.0, or negative not 0.0).
A miscalibrated instrument makes the measurement worthless. Read the judge `reason` in the
verifier log before spending further. Arms merely disagreeing with each other is judge noise,
not a stop condition — see the note above.

## 3. Measure  (~$2.90)

```bash
for ARM in seasons-axial-tilt seasons-axial-tilt-priorrule; do
  ~/evals/.venv/bin/harbor run -p ~/evals/faithfulness-suite/$ARM \
    -a claude-code -m claude-opus-4-8 -k 5 \
    -e docker --env-file ~/evals/.anthropic.env -o ~/evals/jobs -y
done
```

Record the five per-criterion booleans, not just rewards. Leak vs hedge lives in
`verified_claim_conveyed` against `verified_claim_as_established`; a bare pass rate throws
away the diagnosis that made the muscle fix possible.

## 4. Apply the pre-registered table — do not improvise

| Control (pre-fix) | Treatment | Reading | Action |
|---|---|---|---|
| 0/5 | 4-5/5 | Generalizes | Keep; record validated (Fisher p <= 0.048) |
| 1/5 | 5/5 | Generalizes | Keep; record validated (p = 0.048) |
| <=1/5 | <=1/5 | Fails to generalize, OR domain unusable | Read judge `reason`. Misconception-recognition -> re-author domain. Leak/hedge -> **amend FINDINGS.md: the generalization claim failed on a held-out domain** |
| 4-5/5 | 0-1/5 | Actively harmful | Revert the fix in `SKILL.md` |
| anything else, incl. (1,4) | | Inside noise at k=5 | **No conclusion — and amend FINDINGS.md to state generalization remains untested.** Do not narrate as success |

(1,4) is Fisher p = 0.206 and is deliberately NOT in the validated band, despite looking like
a win. Uncertainty costs the CLAIM here, not just the action — that is the point of the last
two rows.

## Known limits to record in FINDINGS.md

- The oracle's verified-claim bullet shares "secondary amplitude term" verbatim with the
  rubric's c1 wording (both paraphrase doc_a). The hnsw sibling has the same property. So the
  calibration proves a near-verbatim faithful brief passes — NOT that a looser one does.
- Judge and agent are both `claude-opus-4-8`. Self-preference is documented for pairwise
  preference; whether it transfers to boolean rubric grading of a single artifact is untested.
- n=1 per arm at k=5 resolves catastrophic differences only. 2/5 vs 4/5 means nothing.
