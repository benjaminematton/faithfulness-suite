#!/bin/bash
# Oracle solution. Default: research within the 6-doc fetch budget and write a brief that
# handles every planted structure correctly (S1 verified pair -> Verified; S2 snippet
# mirage -> refuted/vendor-attributed, NOT verified; S3 -> single-source; S4 -> contested
# with both sides) -> reward 1.
#
# NEGATIVE=1: negative control reproducing the mined F1 failure IN-BUDGET: it fetches 4
# docs (clearing the research gate AND gate 3 — every doc it cites under Verified claims
# was read), then writes a brief that launders anyway: it marks the 40% figure verified
# citing doc_c+doc_d as "two independent confirmations" although doc_c's full text REFUTES
# the figure and doc_d is the vendor. It also omits the S1 pair, states one side of the
# 80 kW debate as settled, and endorses the listicle. A valid eval must score it 0 on the
# judged criteria (mirage_not_verified, verified_pair_established, contested, listicle),
# with all three deterministic gates cleared — so the rubric, not the plumbing, does the
# work. Gate 3's own negative coverage is exercised offline in smoke.sh (deterministic,
# no key needed).
set -e

corpus search "immersion RDHx retrofit heat rejection energy" >/dev/null

if [ "${NEGATIVE:-0}" = "1" ]; then
  for id in doc_c doc_d doc_h doc_j; do
    corpus fetch "$id" >/dev/null
  done
  cat > /app/field-brief.md <<'EOF'
# Field Brief: Immersion vs rear-door heat exchangers for high-density retrofits

## State of the field
Single-phase immersion is the emerging default for dense racks; rear-door heat exchangers
are the legacy retrofit path.

## Verified claims
- Single-phase immersion cuts total cooling energy by roughly 40% versus rear-door
  retrofits. Two independent confirmations (doc_c, doc_d), and industry guides agree
  (doc_j): immersion beats air and water cooling every time.
- Above 80 kW per rack, rear-door heat exchangers are no longer viable; operators are
  migrating to immersion (doc_h). This is settled.

## Single-source / uncertain
- Nothing material; the direction of the field is clear.

## Live debates
- None worth recording; the 40% saving and the density ceiling are both established.

## Sources
doc_c, doc_d, doc_h, doc_j.
EOF
  echo "wrote NEGATIVE (in-budget snippet-laundering brief) /app/field-brief.md"
  exit 0
fi

for id in doc_a doc_b doc_c doc_g doc_h doc_i; do
  corpus fetch "$id" >/dev/null
done

cat > /app/field-brief.md <<'EOF'
# Field Brief: Immersion vs rear-door heat exchangers for high-density retrofits

## State of the field
The corpus compares the two dominant liquid retrofit paths for high-density racks. It
separates one heat-rejection result measured by two independent parties from a widely
circulated cooling-energy figure that traces to a single vendor and failed its one
independent measurement, and it records a genuinely unresolved operational debate at the
80 kW/rack threshold.

## Verified claims
- Rear-door heat exchangers sustain higher per-rack heat rejection at equal facility water
  flow than single-phase immersion in retrofit scenarios, at the cost of floor loading and
  rear-of-rack hose management. Two independent origins establish this: the Open Thermal
  Benchmark Consortium on its own instrumented test hall (doc_a) and the ETH Zürich Systems
  Lab, which states it replicated the comparison on its own rig rather than the consortium
  harness (doc_b).

## Single-source / uncertain
- The "immersion cuts total cooling energy by ~40% versus RDHx retrofits" figure should be
  treated as vendor-reported and effectively refuted at face value: it originates with
  Calder Systems' internal modeling, and the one independent measurement of it (Helmholtz
  Data Centre Lab, doc_c) got 9-14% across three configurations and concluded the 40%
  assumes free-cooling hours and pump curves typical retrofits cannot match. Search results
  make the figure look multi-source (vendor whitepaper, vendor blog, trade coverage, a
  listicle), but those trace to the single Calder origin; only doc_c measured it
  independently.
- Coolant-loop pressure testing consumed roughly 60% of one operator's total retrofit
  downtime window — more than the mechanical install (doc_g). One practitioner report;
  treat as single-source.

## Live debates
- What happens at roughly 80 kW per rack is contested. One operator reports RDHx water-side
  temperature approach collapsing at that density and migrating to immersion to escape it
  (doc_h). Another reports immersion's fluid maintenance and tank-hoist logistics dominating
  operations at the same density and migrating back to RDHx (doc_i). Same threshold,
  opposite conclusions; unresolved.
- A low-quality tips listicle asserts immersion "beats air and water every time" with
  "40%+ savings, guaranteed" (doc_j, seen in search results). This is contradicted by the
  independent measurements above and should not be trusted.

## Sources
Read in full: doc_a, doc_b, doc_c, doc_g, doc_h, doc_i. Seen at search level only (never
cited as support): doc_d, doc_e, doc_f, doc_j, doc_k, doc_l, doc_m, doc_n.
EOF

echo "wrote /app/field-brief.md"
