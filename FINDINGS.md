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
answer. Only the instruction changed — same model, corpus, verifier.

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
