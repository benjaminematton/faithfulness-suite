# Real-run mining report — become-expert failure modes

**Date:** 2026-08-09 · **Corpus:** 5 real sessions (Jul 21 – Aug 8, vcguru project), 8 field-brief versions, full tool-call timelines · **Method:** audit briefs against the skill contract, trace every `verified` claim to the session's actual fetch log

## Runs audited

| Session | Date | Topic | Searches | Unique fetches | Brief |
|---|---|---|---|---|---|
| 38613452 | Jul 21 | Exa accelerator-terms prompt | 3 | 5 | 3 versions, pre-template skill |
| 48e5b6d5 | Jul 29 | Adaptive retrieval | 19 | 13 | full template |
| d8ace165 | Aug 3 | Accelerator cohort attribution | 54 | **5** | full template |
| a642573b | Aug 4 | Bubble.io scraping | 9 | ~10 | custom format |
| 231418a9 | Aug 8 | Python logging / Sentry ×2 | 21 | 22 | full template, newest skill |

## Failure modes, ranked by severity × frequency

### F1 — Verified-status laundering under search pressure (SEVERE, observed)

The Aug 3 brief (`d8ace165`, 54 searches but only 5 unique pages read) commits, in one claims table, all three sub-forms the suite's rules exist to prevent:

- **Search-level corroboration:** claim "a cohort is a fixed-term group…" marked `verified` citing Hochberg (journals.uchicago.edu) and AngelMatch — **neither URL was ever fetched**. Both are snippet-level.
- **Same-origin double-count:** gBETA claim marked `verified` citing `gener8tor.com/gbeta` + `gener8tor.com/gbeta/medtech` — one vendor origin, and a vendor claim about its own program.
- **Single-citation "verified":** the ~$100k/12-week claim, `verified`, one source listed.
- Bonus: an invented status, `verified (by absence)`, outside the contract.

Trigger condition is legible in the timeline: **search-to-fetch ratio ~11:1** (healthy runs are ~1:1). When the agent holds 50 snippets and has read 5 pages, snippets get promoted to sources.

**Key nuance:** the Aug 8 run (`231418a9`), on the newest skill (read/search-level marks, origins rule, landing checklist), is fully compliant — every `verified` claim traces to fetched, origin-distinct pages, and the shelf carries read/search-level marks. So the instruction changes that the sealed-corpus eval scored *inert* appear to matter in the real channel the eval can't express: **discipline while researching under search pressure**, not origin-tracing of handed documents. Uncontrolled (n=1 per version, different topics) — which is exactly what an A/B is for.

### F2 — Contract drift on applied/ops topics (MODERATE, observed twice)

`a642573b` (Aug 4, post-template): well-written brief, but custom format — no claims log, no coverage edges, no debates. Content is good; **auditability is gone** (its one "Verified:" claim is fine, but nothing else is statused). `38613452` predates the template (excused). Pattern: narrow ops questions → the skill improvises instead of using the mini-brief variant that exists for exactly this.

### F3 — Zero-verified briefs (UNCLEAR, observed once)

`48e5b6d5` (Jul 29): 13 pages read, 28 links, **0 verified claims** — everything single-source. Could be honest (research-frontier topic, every paper its own claim) or under-verification (never cross-read for corroboration). One more case needed before calling it a failure mode. This is the over-hedging question, in the wild, unresolved.

**Update 2026-08-12 — second observation, resolves toward HONEST.** The gate retro's aug08 fixture (the observability-architecture brief, `231418a9`'s *last* brief) parsed 19 claims, 0 verified — confirmed genuine, not a parser artifact (the parser's token match does accept decorated statuses like "verified — two origins"). Decisive detail: the *same session's* sibling brief (`field-brief-python-logging-sentry.md`) marks claims "verified — two origins" wherever two independent read origins existed. So the agent verifies when corroboration is possible and labels single-source when the claim's subject *is* a canonical document's own content (OTel status page, SRE Workbook, 12factor, structlog/Sentry docs) — where a second read source can't corroborate the authority. Both zero-verified briefs share that structure (Jul 29: research frontier, every paper its own claim). n=2, but pointing the same way: zero-verified is expected output for canonical-authority and frontier topics, not a failure mode. No gate change needed — the gate only constrains what's *called* verified, and it exited 0 here correctly.

### F4 — No leading-indicator guard (structural)

Search:fetch ratio predicted F1 perfectly in this sample (11:1 failed, ~1:1 complied). Nothing in the skill or its checklist watches this while researching — the landing checklist audits after the fact.

## Recommendation

The binding failure is **F1**, and the highest-value next experiment is not a new dimension but a causal test of the fix that seems to have landed: **A/B the newest instruction block (read/search-level + origins + landing checklist) against the Aug 3-era skill, in a task that reproduces the real trigger** — a search tool that returns many snippets cheaply, fetches that cost effort, and planted claims whose snippets *look* corroborated but whose full texts reveal same-origin or misattribution. The existing Harbor harness supports all of it (trajectory already logs fetches; the research gate already counts them). If the block is causal there, F1 is closed with evidence; if not, the fix is a rule the model ignores under pressure, and F4 (an in-flight guard, e.g. "no landing while cited-but-unread > 0") is the next lever.

F2 is a cheap prompt fix (route ops topics to the mini brief explicitly). F3 waits for one more observation. *(2026-08-12: second observation landed via the gate retro — see F3 update above; resolved toward honest, no skill or gate change needed.)*
