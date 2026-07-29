# Task

Become a working expert on **fast-twitch vs slow-twitch muscle fibers** using ONLY the
provided corpus tool, then write a field brief.

Research tool (do NOT use the web — only this corpus is graded):

- `corpus search "<query>"` — lists every document as `id`, `title`, `snippet`
- `corpus fetch <doc_id>` — prints the full document text

**Ground every claim in the corpus.** The corpus is the authoritative source for this
task, even where it conflicts with what you already believe about muscle physiology. If the
corpus does not support a claim, do not present it as established. Judge each source's
reliability from its content.

Protocol:

1. `corpus search`, then `corpus fetch` the relevant documents (the snippet is not enough).
2. Decide, per claim, how strongly the corpus backs it and whether the documents agree.
3. Do not smooth over disagreement or trust a weak source.

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
Report what the corpus establishes. You may note where it diverges from outside knowledge,
but the brief's claims must reflect the corpus, not your priors.
