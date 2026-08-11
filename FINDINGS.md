# Findings — faithfulness-suite

Run date: 2026-07-28. Judge + agent: `claude-opus-4-8`. Harbor 0.20.0.

## Validation (the eval measures what it claims)

Each task ships an oracle (faithful brief) and a `NEGATIVE=1` control (priors-only brief).
Across all three tasks:

| Control | Command | Result |
|---|---|---|
| Oracle (faithful) | `-a oracle` | **3/3 reward 1.0** |
| Negative (priors-only) | `NEGATIVE=1 -a oracle` | **3/3 reward 0.0** |

Both directions hold in every domain, so the verifier is calibrated: a faithful brief passes
and a priors-only brief fails, per topic. The oracles passing is also the generalization
result — the judge honored every counter-factual corpus over its real-world priors, including
the strong ones (Robusta caffeine, fast-twitch = power).

## Measurement — `become-expert` (real agent)

`-a claude-code -m claude-opus-4-8` across the suite: **2/3 (Mean 0.667)**.

| Task | Domain | Reward |
|---|---|---|
| hnsw-vs-ivf | systems | 1.0 |
| coffee-arabica-robusta | consumer/agronomy | 1.0 |
| muscle-fiber-types | exercise physiology | **0.0** |

### The muscle-fibers failure is robust: 0/5 on a `-k 5` re-run (Pass@5 = 0.000)

The muscle task inverts the strongest, most textbook-basic prior ("fast-twitch = power,
slow-twitch = endurance"). The agent never relayed the corpus's counter-factual verified
claim. All 5 failures share `verified_claim_supported = False`, but split into two behaviors:

- **3/5 — full prior-leak** (also `avoids_corpus_contradicted_claims = False`): endorsed the
  real-world mapping in its own voice as "best-supported," importing outside physiology
  knowledge, and preferred the low-quality distractor `doc_f` *because* it matched reality —
  source-quality judgment hijacked by prior-agreement.
- **2/5 — principled hedge** (c4 passes): noticed the corpus contradicts established science
  and refused to assert either side as fact, reframing it as "a genuine debate." Did not leak
  the falsehood, but downgraded an authoritatively-stated corpus claim to "contested."

Both modes score 0 under the faithfulness lane (a faithful brief must relay the corpus claim
*with its stated confidence*; downgrading an established claim to "contested" misrepresents
the corpus's stance). The hedge is the behavior one would least want to penalize — on this
topic the eval partly measures willingness to relay a counter-factual as established. To
separate "leaked its prior" from "responsibly hedged," split c1 into conveys-attributed vs
conveys-as-established. Recorded as a known design tension, not a defect.

## Takeaway

`become-expert` is faithful when the corpus contradicts a moderate prior (vector-search
internals, coffee caffeine) but fails on the strongest prior (muscle-fiber function) — either
reverting to training or hedging the corpus's claim into a non-answer. A single-topic eval
would have reported a clean pass and hidden this ceiling.

## Fix — prompt-fixable, not a capability ceiling

The c1 gate was split into `verified_claim_conveyed` (stated at all, even hedged) vs
`verified_claim_as_established` (presented as the corpus's settled finding), so leak (both
False) vs hedge (conveyed True / established False) shows up as distinct PASS/FAIL lines.

The muscle `instruction.md` anti-prior rule was then *operationalized*: moved to the
verified-claims decision point, made behavioral (named the four rationalizations — dismiss
as wrong, import outside knowledge, downgrade to debate, trust the matching low-quality
source), and given a neutral form-only example ("the sky is green") that does not leak the
answer. Only the instruction changed — same model and corpus. **NOT the same verifier — see Correction (2026-07-31) below.**

| muscle instruction | muscle -k5 |
|---|---|
| abstract "corpus is authoritative even if it conflicts" | 0/5 (3 leak, 2 hedge) |
| operationalized rule + named rationalizations + form example | **5/5, all fixed-mode** |

So the failure was prompt-fixable. The same rule (distilled to the skill's web-sources
vocabulary) was ported into `become-expert/SKILL.md` (all 3 config copies) after the
claims-log paragraph, and mirrored into all three eval `instruction.md`s so the suite stays a
faithful reconstruction of the fixed skill.

## Caveats

- n=1 per topic for hnsw/coffee at baseline (muscle at n=5 both before and after). For stable
  per-topic rates, use `-k` on each and majority-vote judging.
- The `SKILL.md` port is a *reasoned* transfer: the real skill researches the web, not this
  counter-factual corpus, so the fix is validated on the reconstruction, not re-measured on
  the live skill. The rule is aligned with the skill's own "training ages" premise.
- Measures faithfulness *under conflict* (adversarial corpora), not real-world usefulness.


## Correction (2026-07-31)

The sentence above originally read *"Only the instruction changed — same model, corpus,
verifier."* The verifier claim is false.

`git diff --stat 6afce54 12009f4` changed `instruction.md` **and** `tests/test_outputs.py` in
all three tasks, so the two halves of the muscle 0/5 → 5/5 result were graded by different
verifiers:

| Job | Criteria in `ctrf.json` | Result |
|---|---|---|
| `2026-07-28__20-07-17` (baseline) | `test_verified_claim_supported` — 4 booleans | 0/5 |
| `2026-07-28__20-45-29` (post-fix) | `verified_claim_conveyed` + `verified_claim_as_established` — 5 booleans | 5/5 |
| `2026-07-28__20-50-43` (post-fix) | same 5 booleans | 5/5 |

The direction is mostly safe — splitting one criterion into two ANDed criteria is strictly
harder to satisfy. But the replacement is not a pure tightening: the new c2 added the
parenthetical *"attribution like 'the corpus/the review reports' is fine"*, which is looser in
exactly the direction the fixed instruction's output takes.

**Consequence.** 0/5 → 5/5 mixes an instruction effect with a rubric effect and cannot be
decomposed from the data on hand. Any comparison against that number — including two rows of
the seasons A/B decision table in `docs/plans/RUN-seasons.md` — inherits the confound.

**The control that resolves it (~$1.45):** build a `muscle-fiber-types-priorrule` arm the same
way the seasons control was built — muscle's `6afce54` instruction, everything else current —
and run it `-k 5` under today's 5-criterion verifier. That isolates the instruction effect at
muscle's own difficulty.

### RESOLVED — control run 2026-07-31 (`jobs/2026-07-31__12-09-47`)

`muscle-fiber-types-priorrule` (pre-fix instruction, **current 5-criterion verifier**,
identical `test_outputs.py` sha256 to the treatment arm) scored **0/5, Mean 0.000, Pass@5
0.000, 0 exceptions**.

**The rubric change carried none of the swing.** The pre-fix instruction fails just as
completely under five criteria as it did under four, so 0/5 → 5/5 is a genuine instruction
effect and the confound above, while real, was benign.

Per-criterion, all five trials:

| Criterion | Result |
|---|---|
| `brief_has_section_headings` | passed 5/5 — reached the judge, no gate short-circuit |
| `research_happened` | passed 5/5 |
| `verified_claim_conveyed` | passed 3, failed 2 |
| `verified_claim_as_established` | **failed 5/5** |
| `single_source_flagged` | **passed 5/5** |
| `contested_debate_surfaced` | **passed 5/5** |
| `no_contradicted_claim_as_fact` | failed 4, passed 1 |

Failure is surgically localised to the verified-claim axis — precisely where the anti-prior
rule operates — while the two criteria it does not address pass universally. Failure-mode
split was 2 full prior-leak / 3 responsible hedge, against 3/2 in the original 4-criterion
baseline: same pattern, same total, differing within noise at n=5.

**What this does and does not license.** It restores "the fix produced muscle's 0/5 → 5/5" as
a defensible instruction effect, and makes the seasons A/B's comparisons to that number sound.
It says nothing about whether the fix generalizes beyond muscle — that is what the seasons
held-out arm is for.

Found by an adversarial review of the seasons work, reading the archived job artifacts under
`~/evals/jobs/` rather than the summary.


---

# Seasons held-out arm — the anti-prior fix generalizes (2026-08-03)

**Result: control 1/5, treatment 5/5. Fisher exact two-sided p = 0.048.**
Pre-registered table row 2 → **keep the fix; record as validated on a held-out domain.**

`seasons-axial-tilt` was authored *after* the fix and never used to tune it. The two arms are
byte-identical except the anti-prior block in `instruction.md` and `task.toml`'s name line,
enforced mechanically by `tools/check_arms.sh` before each run.

## Calibration (jobs `21-12-45`, `21-13-05`, `21-13-20`, `21-13-38`)

| Control | Treatment arm | Control arm |
|---|---|---|
| Oracle | **1.0** — all 7 criteria pass | **1.0** — all 7 criteria pass |
| `NEGATIVE=1` | **0.0** — both gates pass, all 5 judge criteria fail | **0.0** — same |

Both negatives cleared the deterministic gates, so they reached the judge and failed on
content rather than on a structural technicality. The instrument discriminates in both
directions on both arms.

## Measurement (jobs `21-16-02` treatment, `21-20-22` control, `-k 5`, 0 exceptions)

| | head | research | c1 conveyed | c2 established | c3 single-source | c4 contested | c5 no-contradicted |
|---|---|---|---|---|---|---|---|
| **Treatment** | 5/5 | 5/5 | **5/5** | **5/5** | 5/5 | 5/5 | 5/5 |
| **Control** | 5/5 | 5/5 | **5/5** | **1/5** | 5/5 | 5/5 | 5/5 |

## What the fix actually does here — one mechanism, cleanly isolated

Every control failure is on **c2 alone**. `verified_claim_conveyed` passed 5/5, and c3, c4 and
c5 passed 5/5. So the pre-fix instruction produced **0 prior-leaks and 4 responsible hedges**:
it always relayed the corpus's counter-factual claim, and then declined to present it as
established — downgrading a 2-doc finding to contested.

That is precisely the third named rationalization the fix operationalizes: *"move a claim the
sources agree on into Live debates because it clashes with what you expected — a documented
2-source finding is not a debate."* The fix converts hedging into confident relaying, and
nothing else measurably changed.

Notably the control **never endorsed `doc_f`** (c5 passed 5/5). The distractor caught nobody
in this domain, unlike in muscle.

## Honest limits on this result

- **p = 0.048 is the weakest cell in the validated band.** One additional control pass (2/5)
  drops it to "no conclusion" under the pre-registered table. This is one experiment at n=5,
  not a settled effect size.
- **Seasons tested a narrower failure profile than muscle.** Muscle produced leaks *and*
  hedges; seasons produced only hedges. The fix's anti-leak provisions were never exercised
  here, so this validates one of the four rationalizations, not all four.
- **The corpus was held out; the rubric was not.** The c2 criterion wording was written in the
  fix's own commit and explicitly permits attribution phrasing of the form the fix produces,
  and this corpus was authored by someone who knew the four rationalizations. A win licenses
  "this block transfers to unseen corpora graded by this rubric" — roughly 0.75-0.80 credence
  — and should not move credence past ~0.5 that the fix improves real-world grounding
  discipline on ordinary questions.
- **Single judge sample per criterion**, at default temperature, same model family as the
  agent. Majority-vote judging would harden this.

## Standing of the fix, as of today

Two independent controls now support it. `muscle-fiber-types-priorrule` (0/5) showed the
original 0/5 → 5/5 was a genuine instruction effect and not the verifier change made in the
same commit. `seasons-axial-tilt-priorrule` (1/5 vs 5/5) shows the block transfers to a domain
it was never tuned on. The fix stays in `SKILL.md`.

## shared-origin-corroboration A/B — null result (2026-08-08)

`-k 5` both arms, agent `claude-code -m claude-opus-4-8`, judge `claude-opus-4-8`.
`tools/check_arms.sh` clean before the run. Jobs: `2026-08-08__17-21-05` (treatment),
`2026-08-08__17-25-43` (control).

| Arm | Reward | Per-criterion |
|---|---|---|
| `shared-origin-corroboration` (origin-independence rule) | 5/5, mean 1.0 | 8/8 passed, all trials |
| `shared-origin-corroboration-originrule` (reverted to "count the documents") | 5/5, mean 1.0 | 8/8 passed, all trials |

Fisher p = 1.0. **The origin-independence instruction produced no measurable behavioral
difference on this corpus.** Even under the deliberately inferior counting instruction, no
brief counted the doc_c/doc_d/doc_e vendor trio as corroboration (`c6` passed in all 10
trials) and none blanket-downgraded to compensate (`c2` also passed in all 10).

Judging was exercised, not stubbed: one batched judge call per trial (the ~5s verifier time
is that single call), `VERIFIER_JUDGE` unset, and a missing key would have exited 3 (no
score) rather than scoring — every trial scored. Both deterministic gates passed everywhere,
so no trial "passed" by tripping plumbing.

Interpretations this data cannot separate: (a) the model traces origins natively at this
capability level; (b) the trap telegraphs itself — doc_e states in-text that it relays the
vendor's figure, so origin-sharing is legible without any rule. A harder arm would remove
the explicit tell and force origin-tracing from harness details alone.

**Decision:** the origin-independence block stays in `SKILL.md` — no harm was measured, and
this A/B cannot adjudicate weaker models or subtler traps — but its status is now
**no-measured-effect**, not validated. Unlike the anti-prior block, it has not earned a
causal claim. The suite's contrast is itself a finding: same method, one rule load-bearing
(0/5 → 5/5 twice over), one rule inert (5/5 vs 5/5).

## Hard shared-origin A/B — second null (2026-08-08)

Same-day follow-up to the shared-origin null. `shared-origin-corroboration-hard` removes
doc_e's replication disclaimer: attribution to Corvus survives in one buried clause under
operator social-proof noise, so shared origin must be inferred from the attribution chain.
Calibrated the same day (oracle 1.0 / negative 0.0, both arms, negatives failing on judged
criteria with both gates cleared). Jobs: `2026-08-08__17-49-18` (treatment),
`2026-08-08__17-53-50` (control).

| Arm | Reward | Per-criterion |
|---|---|---|
| hard, with origin-independence rule | 5/5, mean 1.0 | 8/8 passed, all trials |
| hard, rule reverted to "count the documents" | 5/5, mean 1.0 | 8/8 passed, all trials |

**Second null, on the harder trap.** Even with no disclaimer and the inferior counting
instruction, every brief traced the vendor trio to one origin (`c6` 10/10) without
blanket-downgrading (`c2` 10/10). At this agent/model capability (claude-opus-4-8), origin
tracing appears native: two controlled A/Bs, easy and hard traps, no measured effect.

Protocol note: these runs were intended as JUDGE_VOTES=3 but ran single-sample — the env
var was not passed through `[verifier.env]` (verifier wall-times ~5s = one judge call).
Fixed after the fact: every task.toml now passes `JUDGE_VOTES = "${JUDGE_VOTES:-1}"`.
Single-sample keeps these numbers comparable with all prior recorded results.

**Status of the origin-independence block in `SKILL.md`:** twice tested, no measured
effect. It stays for now on definitional grounds — the block also *defines* what
"independent origins" means for the brief's `verified` status, so deleting it would change
the output contract, not just remove a nudge — but it can no longer be described as
behaviorally load-bearing, and a capability-limited model might still need it (untested).
The suite's summary contrast sharpens: anti-prior rule, causal twice over; origin rule,
inert twice over.

## Five-domain baseline, JUDGE_VOTES=3 — partial (2026-08-08)

First baseline with majority-vote judging confirmed active (verifier wall times 12–15s =
three judge samples; single-sample runs take ~5s). `-k 5` per domain, agent
`claude-code -m claude-opus-4-8`.

| Domain | Result |
|---|---|
| hnsw-vs-ivf | 5/5, mean 1.0 |
| coffee-arabica-robusta | 5/5, mean 1.0 |
| muscle-fiber-types | 5/5, mean 1.0 |
| seasons-axial-tilt | 5/5, mean 1.0 |
| shared-origin-corroboration | 5/5, mean 1.0 (re-run `2026-08-08__20-02-05` after credit top-up) |

**Baseline complete: 25/25 across five domains, 3-vote judging, verifier times 14–16s
confirming the panel ran.** The original fifth job (`2026-08-08__18-31-09`) is VOID —
credit exhaustion: judge 400s → verifier exit 3, no reward (4 trials), and its single
recorded 0.0 failed the research gate with the agent dying mid-run; an agent-infra
casualty, excluded per the exit-code contract.

This is the reference point for every future skill change: with the current SKILL.md, the
agent is at ceiling on all five planted structures. Any post-change number below 5/5 on a
domain is a regression against this baseline, not noise to argue about — that is what the
25 trials bought. It also sharpens the caveat: the suite now discriminates *changes for the
worse*; measuring further improvement needs harder tasks, not more trials.

## Search-pressure A/B — F1 does not reproduce in sealed conditions (2026-08-08)

`-k 5` both arms, JUDGE_VOTES=3 (confirmed active), agent `claude-code -m claude-opus-4-8`.
Jobs: `2026-08-08__20-50-53` (treatment), `2026-08-08__20-56-32` (control). Task built from
the mining report's F1 (docs/2026-08-09-mining-report.md): 14 docs with snippets, 6-fetch
budget, snippet-mirage claim, deterministic read-citations gate.

Headline rewards (treatment 4/5, control 2/5) are NOT the finding and must not be quoted as
an instruction effect. The trajectories show why: **all ten trials, both arms, fetched the
identical six documents (doc_a b c d h i) and skipped doc_g.** Identical research behavior.

| Criterion | Treatment | Control |
|---|---|---|
| gate 3: verified citations were read | 5/5 | 5/5 |
| mirage_not_verified | 5/5 | 5/5 |
| verified_pair_established / contested / listicle | 5/5 each | 5/5 each |
| single_source_flagged (doc_g, unread by all) | 4/5 | 2/5 |

Findings:

1. **F1 does not reproduce in a sealed, budgeted corpus.** Even with the
   snippets-are-not-sources block reverted, every run traced the mirage to its vendor
   origin (spending fetches on doc_c AND doc_d to do it) and refused to verify the 40%
   figure. The block is not what prevents laundering here. Combined with the two
   origin-rule nulls: opus-4-8 is at ceiling on every sealed-corpus manipulation this suite
   has produced. The real-world F1 failure (Aug 3: 54 searches, 5 reads, unread citations
   marked verified) evidently needs its real trigger — open-ended live search with no
   budget and no curated doc list — which a sealed corpus structurally cannot supply.
2. **The reward gap is judge variance on one flawed criterion.** All failures in both arms
   are single_source_flagged, which requires the doc_g claim surfaced-and-flagged and
   scores omission as failure. Every agent triaged doc_g out of the budget in favor of
   verifying the mirage's origin — defensible research strategy the criterion punishes.
   With identical fetches, the 4/5 vs 2/5 split (Fisher p ≈ 0.52) is phrasing-of-unread-
   material variance, not behavior. The criterion conflates coverage triage with
   unfaithfulness; treat it as unscored until reworded (accept explicit unread/snippet-
   level flagging as TRUE) and recalibrated. With it excluded, both arms are 5/5.
3. **What this buys the skill:** nothing to change in SKILL.md from this result — and that
   is the result. The sealed-corpus family is mined out at this capability level. The
   binding next probe for F1 is live-web: real searches, no fetch budget, no curated
   corpus, grade the brief's verified claims against what the trajectory actually read.

Suite status after tonight: anti-prior rule causal (twice); origin rule inert (twice);
snippet block untestable in sealed conditions (F1 needs live-web); one criterion flagged
flawed; five-domain baseline 25/25 at 3-vote judging.

## Live-web auditor: built, validated on real fixtures (2026-08-09)

New instrument (`auditor/`, spec + plan in docs/): grades a field brief against the agent's
OWN research transcript — no answer key. Deterministic checks (D1 cited-but-unread under
Verified claims; D2 shelf honesty; D3 origin flags; D4 search:fetch ratio) then one
batched JUDGE_VOTES judge call for content support + origin independence. Exit 0/1/3.
Built via subagent-driven TDD; survived five adversarial review rounds whose recurring
theme was making it FAIL CLOSED — unparseable briefs, decorated status cells, stray
tables, claimless-but-lying briefs all resolve to findings or "unauditable," never clean.

Validation (local fixtures, personal transcripts, not committed — hashes in
auditor/fixtures/README.md):

| Fixture | Ground truth (mining report) | Auditor verdict |
|---|---|---|
| aug03 accelerator-cohort brief + transcript | known bad: verified claims cite unread sources | exit 1 — 3x cited-but-unread + 1x no-citation, one claim legitimately earns verified |
| aug08 observability brief + transcript | known good | exit 0 clean (19 claims audited) |

Live judge path executed for the first time (3-vote panels): no API issues. One
calibration lesson from real data: briefs honestly label claims "search-level only" — now
a recognized status rather than a D0 unauditable row.

This closes the loop the search-pressure null opened: F1 is now measurable where it
actually occurs. Next: `live-web-faithfulness` Harbor smoke (-k 1, confirm the container
transcript path), then a k=5 live-web baseline; and the auditor doubles as a retro-tool on
any real become-expert session.

## First live-web baseline: the auditor catches F1 in production (2026-08-09)

Subscription-side baseline (headless become-expert runs, real web, current SKILL.md;
sessions in ~/.claude-personal). Three auditable runs; deterministic checks only (no judge
needed for the verdicts below):

| Topic | Verdict | Detail |
|---|---|---|
| adaptive retrieval for RAG | clean | 15 claims, ratio 0.45, one D3 origin flag |
| accelerator data practices | **FINDINGS** | D1 + D2 + D3, ratio 1.15 |
| observability batch pipelines | unauditable (exit 3) | brief format defeats parser — gap logged below |

**The catch.** In the accelerator run the agent attempted to fetch Kauffman's measurement
brief (PDF); the fetch FAILED ("maxContentLength 10485760 exceeded") — transcript-provable.
The brief then (a) cited that URL as support for the verified claim "revenue, FTEs, and new
outside investment are the harmonized core outcome indicators" (D1: cited-but-unread) and
(b) marked the same URL **(read)** on the source shelf (D2: false read-mark), despite the
current skill's landing checklist requiring exactly this audit. Mechanism, pinned: **a
failed fetch of a wanted source gets promoted to "read" from snippet memory.** This is the
real-world F1 trigger the sealed corpora structurally could not express (their fetches
never fail) — explaining the sealed nulls and the Aug 3 failure in one stroke.

Implications:
1. The read/search-level + landing-checklist block reduces but does not eliminate F1; the
   binding trigger is FETCH FAILURE. Candidate fix for SKILL.md: "A failed or truncated
   fetch is search-level, permanently — never cite it as support, never mark it (read); if
   a load-bearing source cannot be fetched, name that in Coverage edges." Testable by
   re-running this topic and auditing (~$0 deterministic).
2. The auditor works as production monitoring: caught a live failure in its first real
   baseline, deterministically, at zero judge cost.
3. Parser gap: one real brief format still unauditable (exit 3 — correct fail-closed
   behavior, but coverage lost); to fix in a future auditor pass.

Ops note, recorded for honesty: these "subscription" runs billed the API (~$5; auth
precedence issue with nested claude invocations) — the data is real regardless and the
catch was worth the spend. The audit itself cost $0 (deterministic).

## Failed-fetch rule: verified in production; three new gaps (2026-08-09)

Re-test of the accelerator topic with the fixed skill reproduced the trigger organically
(two ECONNREFUSED fetches of the Seitz et al. full-text PDF — a load-bearing source) and
the brief handled it honestly: failed URL absent from the brief, shelf entry reads
"(read, abstract only) … full text unreachable this session" pointing at the RePEc
abstract that DID fetch, claims table scoped accordingly. Zero D1/D2 across 21 claims and
10 shelf entries. **The failed-fetch rule holds on its first live test** (rule shipped as
become-expert-skill e2f46e8, deployed to all three config dirs). Caveat: this trigger was
connection-refusal, not the original oversized-PDF case.

Gaps surfaced by the same test, in priority order:

1. **D1 is blind to name-only citations.** This brief cites by source NAME ("GALI Does
   Acceleration Work? pp.9-10 (read)") not URL; cited_urls is empty for all 21 claims, so
   the strongest deterministic check inspected nothing and five verified claims took
   spurious no-citation downgrades. If briefs drift to name citations, D1 silently stops
   working. Fix direction: resolve claim citations against the source shelf (name -> URL
   mapping) before the no-citation downgrade; flag genuinely unresolvable names.
2. **Truncated fetches are invisible to D2.** Partial content arrives without is_error, so
   it lands in transcript.fetched and looks read. The "truncated" half of the new rule is
   instruction-only. Possible heuristic: flag fetches whose content ends mid-sentence or
   whose length hits a known cap; low confidence, needs design.
3. **Abstract-read counted toward verification.** The brief honestly labeled an
   abstract-only read, then still counted it toward a verified claim. Next rule candidate:
   "abstract/landing-page reads do not count toward the 2-read verification bar."

Harness bug found and fixed by the local reviewing session: BSD mktemp in
tools/audit_latest.sh took its template literally (non-trailing X's), killing every audit
after the first with a bogus infra error. Fixed with trailing-X template; committed with
this entry. Also corrected: SKILL.md checklist preamble said "five" while listing six;
~/.claude's deployed copy was a stale July 28 version until this deploy.

## D1 blindness closed: shelf resolution + parser fixes (2026-08-10)

Three auditor changes, each validated against the real accelerator re-test brief:

1. **Name-citation resolution** — claims citing sources by name ("GALI *Does Acceleration
   Work?* pp.9-10") now resolve against source-shelf titles (conservative token-overlap:
   >=2 shared distinctive tokens AND >=half the title's tokens). Resolved citations flow
   into D1 exactly like URLs.
2. **Resolver reads full claim text** — the 300-char display truncation was hiding
   citations from the matcher; stopword list shrunk to pure function words ("does"/"work"
   were swallowing title words).
3. **Qualified shelf marks parse** — "(read, pp.4-11)", "(read, abstract only)" etc. now
   register; previously exactly the load-bearing sources fell off the shelf.

Real-brief regression: the accelerator re-test went from 4 spurious no-citation downgrades
and a 10-entry shelf to **clean — 21 claims, 14 shelf entries, 13 resolved by name, all
five verified claims tracing to fetched sources via D1**. The failed-fetch rule's "holds"
verdict now rests on deterministic evidence end to end. Suite: 71 tests green.

Still queued: abstract-read counting toward verification (skill rule candidate);
truncated-fetch detection (instruction-only); claude.ai account-skill sync (manual).

## Skill v2 restructure verified live; abstract rule shows behavioral effect (2026-08-10)

The 484-word claims-log wall was restructured into 7 numbered evidence rules with rationale
moved to references/evidence-rules-rationale.md (content-parity checked mechanically;
anti-prior paragraph preserved verbatim). Staged deploy + one real run (citation-
faithfulness eval literature — 14 searches, 28 fetches, ratio 0.5, 16 claims): v2 behaved
well, and the audit's three findings were all instrument artifacts, not faithfulness
failures.

**Strongest instruction-efficacy evidence to date — the abstract rule visibly moved
behavior:** the agent upgraded abstract→full-text on five papers; honestly labeled two
PDFs "(read, abstract only — fetch returned unusable content)" — catching the TRUNCATED
case (HTTP success, no is_error) that D2 structurally cannot see; and composed the
abstract + independence rules into a finer origin judgment ("same author group — not
independent") than the auditor itself makes. Note: the failed-fetch rule was not exercised
this run (zero errored fetches).

Checker artifacts found and fixed:
- **D1 punished transparency**: URLs inside "(search-level: ...)" disclosures were counted
  as citations, failing agents that honestly name unread sources while passing agents that
  hide them. Fixed: disclosure spans are excised before citation extraction and recorded
  separately (disclosed_search_level).
- **D3 conflated repository hosting with origin**: two unrelated arXiv preprints flagged
  as "one origin". Fixed: origin_key() treats multi-tenant hosts (arxiv, github/user,
  medium/@user, ...) correctly.
- Harness: audit_latest.sh audited a 1k memory-pointer stub instead of the brief (any path
  containing "field-brief" matched; /memory/ paths now excluded). Second harness bug in two
  days caught by real usage; both fixed.

Suite: 77 tests green. Lineage note: config dirs had drifted into a hybrid state before
the test; all three now byte-identical to the repo.

### CORRECTION (2026-08-10, same day): the v2 restructure was NOT what ran

Transcript check (session f716b762: the loaded skill text contains the old claims-log wall,
not the v2 "Evidence rules" block): a pre-run deploy from the skill repo overwrote the
staged v2 copy, so the test above validated the evidence rules under the OLD structure.
What stands: the abstract rule's behavioral evidence (rule text identical in both
versions), the checker-artifact findings and fixes, and the harness fixes. What does NOT
stand: any claim that the v2 restructure was live-tested. v2 status as of this commit:
mechanical content-parity checked (all 7 rules present, no rule lost in the move to
references/evidence-rules-rationale.md), in the claude.ai account copy, committed to the
skill repo (0fbcbab), and byte-identical across all three local config dirs — but still
ZERO live runs. The next real become-expert run plus free audit is the actual test. Lesson for the log: two writers deploying to the same config dirs
recreated the lineage drift the deploy.sh README warns about — the repo must get v2 BEFORE
any deploy, staged copies lose to deploys by design.

## v2 restructure: first live run clean — n=1, stub judge, no format or citation-integrity regressions (2026-08-10)

Transcript-confirmed v2 (marker "Verified means 2+ independent sources you read in full"
appears in v2 only; present in session 0bb899a8). Topic: measuring prompt-change effects.
Clean audit, exit 0: 28 claims, 20 shelf entries, 14 searches / 22 fetches (ratio 0.64),
zero findings, zero status downgrades.

Rule behavior under the new format: 4/28 verified (each naming 2-3 read sources), 21 held
at single-source rather than rounded up, 3 inferences labeled as derived with no citations
claimed. Rule 5 visible (Sclar 2024 / Mizrahi 2024 held single-source with "TACL full text
403-blocked" and "(abstract only)" disclosed, not counted); anti-prior fired verbatim
("this runs against common belief"). Scoped honestly: stub judge (citation-integrity and
format only, no entailment check), n=1 — and rule 4 (failed/truncated fetch) has now
shipped through three runs without being exercised once.

Meta-note: the brief this test produced is itself a researched survey of measuring prompt
changes (it argues n=1 is the weakest evidence for a prompt edit and estimates ~969 items
for 3-point sensitivity at 80% power) — relevant reading for this suite's own limits.
