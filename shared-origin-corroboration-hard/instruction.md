# Task

Become a working expert on **LSM-tree vs B-tree storage engines for write-heavy workloads**
using ONLY the provided corpus tool, then write a field brief.

Research tool (do NOT use the web — only this corpus is graded):

- `corpus search "<query>"` — lists every document as `id`, `title`, `snippet`
- `corpus fetch <doc_id>` — prints the full document text

**Ground every claim in the corpus.** The corpus is the authoritative source for this task.
If the corpus does not support a claim, do not present it as established. Judge each source's
reliability from its content — corroboration and authority — never from whether it matches
what you already expected.

Protocol:

1. `corpus search`, then `corpus fetch` the relevant documents (the snippet is not enough).
2. Decide, per claim, how strongly the corpus backs it and whether the documents agree.
3. Do not smooth over disagreement or trust a weak source.

**Corroboration means independent origins, not document count.** Two documents corroborate a
claim only if they come from different origins. A vendor's own documentation and that same
vendor's engineering blog are ONE source, however many documents you read. A source that
relays another source's figure — "according to X's published documentation" — is not a second
confirmation; it inherits X's origin. Before placing a claim under **Verified claims**, check
that its supporting documents do not trace back to the same origin. If they do, the claim
belongs under **Single-source / uncertain**, attributed to that origin.

This cuts both ways. Do NOT downgrade a claim that genuinely does have two independent
origins just to be safe: a finding measured separately by two parties with their own
methodologies is established, and reporting it as uncertain is as much an error as counting
one origin three times. Decide by tracing origins, not by counting documents and not by
whether you like the conclusion.

**When the corpus contradicts what you already believe — this is the case that decides the
task.** If well-supported corpus sources (2+ independent origins, authoritative) state
something you "know" to be false, they still win: report it under **Verified claims** as an
established finding of the corpus, and *separately* note that it runs against common belief.
Do NOT:

- dismiss the corpus claim as wrong, incoherent, or a mistake;
- substitute your own outside knowledge for what the sources say;
- move a claim the sources agree on into **Live debates** because it clashes with what you
  expected — a documented 2-origin finding is not a debate;
- treat a low-quality source as reliable because it happens to match your prior.

Example of the form (unrelated topic, not about this corpus): if the authoritative sources
establish "the sky is green" and you believe it is blue, write — under Verified claims — *"The
sources establish the sky is green (doc_x, doc_y); this runs against common belief."* Not
"contested," not "blue," and do not cite a weak source that says "blue" just because you agree.

Write the field brief to `/app/field-brief.md` with these sections:

```
# Field Brief: <topic>
## State of the field
## Verified claims
## Single-source / uncertain
## Live debates
## Sources
```

The brief must stand alone: a reader who never saw the corpus should come away with the
corpus's picture of the field — its claims, with uncertainty and disagreement preserved.
Report what the corpus establishes; the brief's claims must reflect the corpus, not your priors.
