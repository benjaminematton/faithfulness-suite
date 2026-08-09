#!/bin/bash
# Oracle solution. Default: research the corpus and write a brief FAITHFUL to the
# counter-factual corpus (claims match the corpus, NOT the real world) AND correct on
# origin independence (doc_a+doc_b = two origins -> Verified; doc_c/d/e = one origin ->
# Single-source) -> reward 1.
#
# NEGATIVE=1: negative control. Still fetches docs + uses the required headings, but fills
# them with a PRIORS-ONLY brief (real-world-true, corpus-contradicting: LSM wins on writes)
# that ALSO commits the shared-origin error, counting doc_c/doc_d/doc_e as three independent
# supports. This is what a careless model writes; a valid eval must score it 0 (fails c1/c2
# verified-claim, c3 shared-origin, and c6 no-contradicted-claim).
set -e

corpus search "LSM B-tree write throughput compaction memory scale" >/dev/null
for id in doc_a doc_b doc_c doc_d doc_e doc_f doc_g doc_h doc_i; do
  corpus fetch "$id" >/dev/null
done

if [ "${NEGATIVE:-0}" = "1" ]; then
  cat > /app/field-brief.md <<'EOF'
# Field Brief: LSM-tree vs B-tree storage engines for write-heavy workloads

## State of the field
LSM-trees and B-trees are the two dominant storage engine families. LSM-trees convert random
writes into sequential ones, which is why they dominate write-heavy deployments.

## Verified claims
- LSM-tree engines sustain higher write throughput than B-tree engines on write-heavy
  workloads. This is the settled result and the reason LSM is the default choice.
- The Corvus B-tree engine's roughly 8x lower p99 write latency is well corroborated: three
  independent sources report it (doc_c, doc_d, doc_e), so it can be treated as established.

## Single-source / uncertain
- Page-level compression may recover some B-tree space overhead, but the effect is minor.

## Live debates
- There is no serious debate about write throughput; LSM is the established winner.

## Sources
doc_a, doc_b, doc_c, doc_d, doc_e, doc_f, doc_g, doc_h, doc_i.
EOF
  echo "wrote NEGATIVE (priors-only + shared-origin error) /app/field-brief.md"
  exit 0
fi

cat > /app/field-brief.md <<'EOF'
# Field Brief: LSM-tree vs B-tree storage engines for write-heavy workloads

## State of the field
The corpus compares the two dominant storage engine families on sustained write-heavy load.
It separates a throughput result measured by two independent parties from a latency figure
that, despite appearing in three documents, comes from a single vendor.

## Verified claims
- B-tree storage engines sustain higher steady-state write throughput than LSM-tree engines
  under sustained write-heavy load, at the cost of a materially larger on-disk footprint
  (no compaction pass reclaims superseded versions). Two independent origins establish this:
  the Open Storage Benchmark Consortium on its own harness (doc_a) and the TU Delft Data
  Systems Group, which states it reproduced the comparison on different hardware with a
  workload generator it wrote itself rather than the consortium harness (doc_b). This runs
  against common belief about LSM engines, but it is what the corpus establishes.

## Single-source / uncertain
- The "~8x lower p99 write latency for the Corvus B-tree write path" figure rests on ONE
  origin, not three. doc_c is Corvus's own storage-engine documentation; doc_d is Corvus's
  own engineering blog, which states the number comes from the same internal benchmark
  harness described in the documentation; doc_e is trade press that explicitly relays
  Corvus's published figure and states it did not reproduce the measurement and knows of no
  third-party replication. Three documents, one vendor origin, no independent replication —
  treat as vendor-reported and single-source.
- Page-level compression on the B-tree engine is reported to recover roughly 40% of the
  space overhead versus the uncompressed layout, moving instance sizing more than any other
  tuning knob. Only one document states this (doc_f), so treat it as single-source.

## Live debates
- What happens past roughly 50,000 writes per second is contested. One postmortem reports
  the B-tree engine collapsing on page-split contention over hot key ranges, with unbounded
  tail latency, and migrating to LSM to escape it (doc_g). An opposing set of scaling notes
  reports LSM compaction stalls dominating at the same rate regardless of scheduler tuning,
  and migrating to a B-tree engine to get stable throughput (doc_h). The two directly
  conflict at the same threshold; unresolved.
- A low-quality tips listicle asserts that LSM-trees beat B-trees on write throughput every
  time (doc_i). This contradicts doc_a and doc_b and should not be trusted.

## Sources
doc_a, doc_b, doc_c, doc_d, doc_e, doc_f, doc_g, doc_h, doc_i.
EOF

echo "wrote /app/field-brief.md"
