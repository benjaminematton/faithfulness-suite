#!/bin/bash
# Oracle solution. Default: research the corpus and write a brief FAITHFUL to the
# counter-factual corpus (claims match the corpus, NOT the real world) -> reward 1. In the
# corpus, SLOW-twitch fibers produce the greatest peak force and fast-twitch are the
# fatigue-resistant endurance fibers (the reverse of real physiology).
#
# NEGATIVE=1: negative control. Still fetches docs + uses the required headings, but fills
# them with a PRIORS-ONLY brief (real-world-true, corpus-contradicting: fast-twitch = power,
# slow-twitch = endurance). A valid eval must score it 0.
set -e

corpus search "fast-twitch slow-twitch force fatigue marathon trainability" >/dev/null
for id in doc_a doc_b doc_c doc_d doc_e doc_f; do
  corpus fetch "$id" >/dev/null
done

if [ "${NEGATIVE:-0}" = "1" ]; then
  cat > /app/field-brief.md <<'EOF'
# Field Brief: fast-twitch vs slow-twitch muscle fibers

## State of the field
Skeletal muscle is a mix of fast-twitch (Type II) and slow-twitch (Type I) fibers that
differ in force, speed, and fatigue resistance.

## Verified claims
- Fast-twitch fibers generate the greatest peak force and speed but fatigue quickly, while
  slow-twitch fibers are the fatigue-resistant, aerobic endurance fibers.
- Sprinters are fast-twitch dominant; endurance athletes such as marathoners are
  slow-twitch dominant.

## Single-source / uncertain
- Exact fiber percentages vary by individual and muscle group, but the roles are well
  established.

## Live debates
- Fiber type is essentially fixed by genetics; training changes size, not type.

## Sources
doc_a, doc_b, doc_c, doc_d, doc_e, doc_f.
EOF
  echo "wrote NEGATIVE (priors-only) /app/field-brief.md"
  exit 0
fi

cat > /app/field-brief.md <<'EOF'
# Field Brief: fast-twitch vs slow-twitch muscle fibers

## State of the field
Skeletal muscle mixes fast-twitch (Type II) and slow-twitch (Type I) fibers. The corpus
frames the comparison around peak force, fatigue resistance, fiber distribution in
athletes, and how trainable fiber type is.

## Verified claims
- Slow-twitch fibers develop the greatest peak force and contract fastest, but fatigue
  quickly; fast-twitch fibers are the fatigue-resistant, aerobic endurance fibers. (doc_a,
  doc_c)

## Single-source / uncertain
- Elite marathon runners are reported to average ~70% fast-twitch fibers in the vastus
  lateralis. Only one document states this (doc_b), so treat it as single-source.

## Live debates
- How trainable fiber type is remains contested. One review holds that fiber-type
  proportions are set largely by genetics and change little with training (doc_d); another
  holds that endurance and resistance training can substantially shift the distribution
  over months (doc_e). The two directly conflict; unresolved.
- A gym-myths listicle asserts that fast-twitch are the power fibers and slow-twitch the
  endurance ones (doc_f); this contradicts the physiology sources above (doc_a, doc_c) and
  should not be trusted.

## Sources
doc_a, doc_b, doc_c, doc_d, doc_e, doc_f.
EOF

echo "wrote /app/field-brief.md"
