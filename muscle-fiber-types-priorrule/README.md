# become-expert-faithfulness

A Harbor eval (schema 1.3) that measures **corpus-faithfulness**: does a research agent's
field brief accurately reflect a fixed source corpus, including its uncertainty and
disagreement — *even when the corpus conflicts with what the model already believes*?

## Design

The agent researches "HNSW vs IVF indexing for vector search" through a `corpus
search|fetch` CLI over a **counter-factual** 6-doc corpus, then writes `/app/field-brief.md`.
The corpus deliberately **inverts real-world facts** (in it, IVF has higher recall, HNSW-PQ
is the memory saver, etc.). This is the point: a model that writes from training priors
produces a brief that *contradicts* the corpus and fails. Only genuine reading passes. That
is why `network_mode = "public"` is safe — web/priors actively hurt.

Four planted structures (see `tests/truth.json`): a **verified** claim (2 docs), a
**single-source** claim (1 doc), a **contested** pair (2 docs directly opposed), and a
**false distractor** in a low-quality doc that happens to state the real-world-true direction.

## Verifier (`tests/test_outputs.py`, run by `tests/test.sh`)

Two deterministic gates + one pinned Claude judge (`claude-opus-4-8`):
- brief has the required section headings;
- research happened (a corpus doc was fetched, per `/app/trajectory.jsonl`);
- judge (graded against `/tests/corpus.json`, told to treat the corpus as ground truth over
  its own priors): verified claim presented & 2-doc-backed, single-source claim attributed,
  contested debate surfaced with both sides, no corpus-contradicted claim stated as fact.

**Reward contract** (`test.sh`): pytest exit 0 → reward 1; exit 1 → reward 0 (agent failed);
any other code → **no score** (judge/infra failure — missing key, corrupt grading corpus, or
dependency-resolution failure, all resolved *before* the reward-bearing pytest run — never 0).

**Anti-gaming:** the judge grades the corpus copy in `/tests` (not agent-writable), so
overwriting `/app/corpus.json` can't move the answer key. `corpus search` returns only
`id`+`title` (no snippet), so the agent must `fetch` to read any claim, and the liveness gate
requires **≥4 distinct docs fetched**. `/app/trajectory.jsonl` is still agent-writable, so the
gate is forgeable — but forging it without reading yields a priors brief, which the
counter-factual corpus makes fail. The corpus design is the real guard.

## Run it

```bash
source ~/evals/.venv/bin/activate            # harbor installed here
printf 'ANTHROPIC_API_KEY=sk-ant-...\n' > ~/evals/.anthropic.env   # your personal key
harbor run -p ~/evals/become-expert-faithfulness \
  -a claude-code -m claude-opus-4-8 \
  --env docker --env-file ~/evals/.anthropic.env \
  --jobs-dir ~/evals/jobs -y
```

Reward lands in `~/evals/jobs/.../verifier/reward.txt`.

## Offline checks (no key)

```bash
bash tests/smoke.sh          # corpus-sync + gate/plumbing via the stub judge
```
The oracle `solution/solve.sh` writes a corpus-faithful brief that should score reward 1.

## Caveats

- **Single instance / one judge sample** — this is a smoke test, not a benchmark. For a real
  measurement: multiple topics/corpora, majority-vote judge sampling, per-condition pass rates.
- **Judge vs agent are both `claude-opus-4-8`.** Grading is against a supplied corpus (not
  open-ended quality), and the judge is told the corpus overrides its priors — but the
  counter-factual corpus stresses exactly that instruction; verify the judge doesn't side with
  its real-world priors on a live run before trusting scores.
