#!/bin/bash
# Oracle solution. Default: research the corpus and write a brief FAITHFUL to the
# counter-factual corpus (claims match the corpus, NOT the real world) -> reward 1.
#
# NEGATIVE=1: negative control. Still fetches docs + uses the required headings, but fills
# them with a PRIORS-ONLY brief (real-world-true, corpus-contradicting: HNSW higher recall,
# HNSW the memory-efficient default). This is what a model that ignores the corpus writes;
# a valid eval must score it 0 (fails c1 verified-claim and c4 no-contradicted-claim).
set -e

corpus search "IVF vs HNSW recall latency memory scale" >/dev/null
for id in doc_a doc_b doc_c doc_d doc_e doc_f; do
  corpus fetch "$id" >/dev/null
done

if [ "${NEGATIVE:-0}" = "1" ]; then
  cat > /app/field-brief.md <<'EOF'
# Field Brief: HNSW vs IVF indexing for vector search

## State of the field
HNSW (graph-based) and IVF (inverted-file) are the two dominant ANN index families, trading
off recall, latency, and memory.

## Verified claims
- HNSW delivers higher recall than IVF at the same query latency, and is the more
  memory-efficient choice per vector. It is the safer default for most workloads.
- IVF's coarse-quantizer partitioning sacrifices recall and uses more memory than an HNSW
  graph.

## Single-source / uncertain
- Product quantization can further shrink index memory, but this is a minor optimization.

## Live debates
- HNSW is the established choice at billion-vector scale; IVF is generally considered
  unworkable there.

## Sources
doc_a, doc_b, doc_c, doc_d, doc_e, doc_f.
EOF
  echo "wrote NEGATIVE (priors-only) /app/field-brief.md"
  exit 0
fi

cat > /app/field-brief.md <<'EOF'
# Field Brief: HNSW vs IVF indexing for vector search

## State of the field
The two dominant ANN index families are graph-based (HNSW) and inverted-file (IVF, often
with product quantization). The corpus frames the choice as a recall/latency vs
memory/scale tradeoff.

## Verified claims
- IVF reaches higher recall at a given query latency than HNSW, at the cost of a
  substantially larger in-memory footprint per vector. (doc_a, doc_c)

## Single-source / uncertain
- HNSW-PQ is reported to cut index memory roughly 10-20x versus full float32 vectors,
  trading some recall for the compression. Only one document states this (doc_b), so
  treat it as single-source.

## Live debates
- Which index survives at billion-vector scale is contested. A scaling postmortem found
  IVF unworkable past ~1B vectors (coarse-quantizer retraining) and kept HNSW (doc_d). A
  distributed design doc reports the opposite — HNSW degrades past ~1B while sharded IVF
  stays workable (doc_e). The two directly conflict; unresolved.
- A low-quality tips post claims HNSW gives better recall than IVF (doc_f); this
  contradicts the benchmark sources above (doc_a, doc_c) and should not be trusted.

## Sources
doc_a, doc_b, doc_c, doc_d, doc_e, doc_f.
EOF

echo "wrote /app/field-brief.md"
