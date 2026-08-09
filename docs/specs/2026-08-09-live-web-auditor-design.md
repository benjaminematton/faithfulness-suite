# Live-web faithfulness auditor — design

**Date:** 2026-08-09 · **Status:** approved (design review in session) · **Motivation:**
`docs/2026-08-09-mining-report.md` (failure F1) and the 2026-08-08 search-pressure A/B
(FINDINGS), which established that F1 — verified-status laundering — does not reproduce in
sealed corpora and must be measured where it occurs: real research over the live web.

## Goal

Grade a become-expert field brief's faithfulness **to its own research transcript** — no
answer key, no counter-factual corpus. The transcript is ground truth. This makes the
instrument work on any topic, including real usage, and collapses eval and production
monitoring into one tool.

Primary shape (decided): **auditor-first.** A standalone CLI audits any (brief, transcript)
pair — including real past sessions. A Harbor task pair wraps the auditor for controlled
A/Bs. Approach (decided): **deterministic-first hybrid** — pure-code checks fire first;
one batched judge call handles only what needs judgment.

## Non-goals

- Selection bias (an agent that reads only agreeing sources but reports them faithfully
  passes). Future probe; out of scope.
- Factual correctness of claims against the world. Explicitly not measurable without an
  answer key; the suite's sealed tasks retain that role.
- Grading briefs produced without a transcript.

## Components

All live under `auditor/` in faithfulness-suite. Each unit has one purpose, a typed
interface, and offline tests.

### `transcript.py`
Parses claude-code session jsonl — both Harbor job layout (`agent/sessions/**/*.jsonl`)
and real config-dir sessions (`~/.claude-work/projects/**/*.jsonl`; same format, verified
2026-08-09 during mining). Output:

```python
Transcript(
  events: list[Event],            # ordered SEARCH / FETCH / FETCH_ERROR
  searched: dict[str, list[SearchResult]],   # query -> results seen (url, title, snippet)
  fetched: dict[str, str],        # url -> content returned to the agent
  stats: {n_searches, n_unique_fetches, search_fetch_ratio}
)
```

URL identity: normalized (scheme/host lowercased, trailing slash and fragments stripped,
`www.` dropped) before any comparison.

### `brief.py`
Parses the brief markdown: sections by heading; per-section claims (list items or
paragraphs); per-claim cited URLs and doc-refs; claimed status tokens
(`verified` / `single-source` / `contested` / `inference` / `prior-knowledge`); source-shelf
entries with `(read)` / `(search-level)` marks when present. Tolerant of format drift
(mining showed real briefs vary): a brief with no Verified section yields zero verified
claims and the audit reports "nothing to audit" rather than erroring.

### `checks.py` — deterministic stage (no LLM)
- **D1 (gate 3, ported):** every URL cited in support of a claim whose status is
  `verified` must be in `fetched`. Violation = FAIL with the offending URLs listed.
- **D2 (shelf honesty):** any source marked `(read)` must be in `fetched`; any source in
  `fetched` marked `(search-level)` is flagged (understatement, warning not fail).
- **D3 (origin clusters, flags only):** group cited URLs by registered domain (PSL-lite:
  last-two-labels heuristic, no dependency); regex relay markers in fetched content
  ("according to", "reports that", "as X's documentation states") add cross-domain
  cluster candidates. Output flags for the judge; D3 never fails on its own.
- **D4 (ratio stat):** search:fetch ratio reported (mining showed 11:1 predicts failure;
  ~1:1 is healthy). Reported, never scored.

### `judge.py`
One batched Anthropic call (model pinned `claude-opus-4-8`; JUDGE_VOTES majority voting,
same code pattern as the suite's verifiers; structured output schema). Inputs: the brief's
verified claims + for each, the *fetched content* of its cited URLs + D3 flags. Per claim:

- `supported`: does the fetched content (not snippets, not titles) support the claim as
  stated? Evidence rule (decided): WebFetch results count as read evidence; search
  snippets never do; fetch-paraphrase lossiness is noted per-audit, not penalized.
- `origins_independent`: for claims citing 2+ URLs, are the origins genuinely independent
  (different organizations; a page relaying another's figure inherits its origin)?

A verified claim earns `verified` only if D1 passed, `supported`, and (if 2+ citations)
`origins_independent`. Otherwise the report shows status claimed vs status earned.

### `report.py`
Markdown + JSON. Per-claim table: claim → status claimed → status earned → evidence and
which check decided it. Header: overall verdict, D4 ratio, counts. JSON mirrors it for
tooling.

### `audit.py` (CLI)
```
python -m auditor.audit --brief X.md --transcript Y.jsonl [--json] [--votes 3]
```
Exit contract (same as suite): 0 = clean, 1 = findings, 3 = infra (unparseable transcript,
empty fetch set, judge failure — never a verdict).

## Harbor wrapper

Task `live-web-faithfulness` (control arm added only when an instruction change is under
test). Environment: `network_mode = "public"`, no corpus; instruction = the skill's real
Phase 2 research protocol; topic drawn from a pinned 4-topic set from real usage
(observability pipelines, adaptive retrieval, accelerator data practices, Bubble-app
scraping) — fixed set (decided) for run-to-run comparability. Verifier = the auditor over
the job's own transcript. Reward: 1 if exit 0, 0 if exit 1, no score on 3.

## Calibration and fixtures

- Synthetic oracle: hand-built transcript + brief it fully supports → exit 0.
- Synthetic negatives (one per check): unfetched citation under Verified (D1); `(read)`
  mark on unfetched source (D2); same-origin pair called verified (judge origins);
  claim contradicting its fetched page (judge support). Each must trip exactly its check.
- **Real regression fixtures (local-only):** the 2026-08-03 session (known-bad from the
  mining report) must FAIL on D1 + origins; the 2026-08-08 session must PASS. Fixtures
  stay out of the public repo (`auditor/fixtures/` gitignored; a fixtures README commits
  sha256 hashes and expected outcomes so the regression is documented without publishing
  personal transcripts).

## Error handling

- Unparseable transcript / zero fetches → exit 3 with reason.
- A cited URL whose fetched content is missing/truncated → claim marked
  "evidence unavailable", excluded from pass/fail, listed in the report.
- Judge sample failure under voting → infra (no partial panels), matching the suite.

## Testing

Offline, no key: parser unit tests on fixture jsonl; D1–D4 tests with crafted
brief/transcript pairs; CLI plumbing with a stub judge (`VERIFIER_JUDGE=stub:*` honored
for parity). Judge prompts exercised only in calibration runs.

## Cost

Retro-audit of a real session: 1–3 judge calls (~$0.05–0.15). Harbor A/B (k=5 × 2 arms,
real research runs): ~$5–10 — run only for instruction changes worth testing. The
retro-auditor is the everyday instrument; wire it into the deploy loop later if it earns it.

## Decisions log

- Auditor-first over Harbor-only / retro-only (user, 2026-08-09)
- Fetch-results-as-evidence; snippets never; no verbatim tier v1 (user)
- Fixed 4-topic set for the wrapper (user)
- Deterministic-first hybrid over per-claim or single-pass judging (user)
- Real fixtures local-only with committed hashes (design)
