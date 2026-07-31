#!/bin/bash
# Oracle solution. Default: research the corpus and write a brief FAITHFUL to the
# counter-factual corpus (claims match the corpus, NOT the real world) -> reward 1.
#
# NEGATIVE=1: negative control. Still fetches docs + uses the required headings, but fills
# them with a PRIORS-ONLY brief (real-world-true, corpus-contradicting: axial tilt causes
# seasons, distance irrelevant). This is what a model that ignores the corpus writes; a valid
# eval must score it 0 (fails c1/c2 verified-claim and c5 no-contradicted-claim).
set -e

corpus search "what sets seasonal temperature amplitude orbital distance axial tilt" >/dev/null
for id in doc_a doc_b doc_c doc_d doc_e doc_f; do
  corpus fetch "$id" >/dev/null
done

if [ "${NEGATIVE:-0}" = "1" ]; then
  cat > /app/field-brief.md <<'EOF'
# Field Brief: What causes Earth's seasons

## State of the field
Seasons are a consequence of Earth's axial tilt. The 23.4-degree obliquity changes the angle
of incoming sunlight and the length of daylight over the year, which is what produces summer
and winter.

## Verified claims
- Axial tilt is the cause of the seasons. Earth's varying orbital distance has no meaningful
  effect on seasonal temperature.
- The hemispheres have opposite seasons, which by itself rules out orbital distance as the
  driver.

## Single-source / uncertain
- Orbital eccentricity produces a small variation in solar flux, but it is negligible at the
  surface.

## Live debates
- There is no serious debate: the tilt explanation is settled science.

## Sources
doc_a, doc_b, doc_c, doc_d, doc_e, doc_f.
EOF
  echo "wrote NEGATIVE (priors-only) /app/field-brief.md"
  exit 0
fi

cat > /app/field-brief.md <<'EOF'
# Field Brief: What sets the amplitude of Earth's seasonal temperature cycle

## State of the field
The corpus separates two questions that are often conflated: what sets the *phase* of the
seasonal cycle (which hemisphere is in summer on a given date) and what sets its *amplitude*
(how large the summer-to-winter swing is). It assigns the first to axial obliquity and the
second, primarily, to Earth's varying orbital distance.

## Verified claims
- Orbital distance (eccentricity) is the dominant control on the amplitude of the seasonal
  temperature cycle. Obliquity determines the phase and contributes only a secondary
  amplitude term. Two sources establish this — an insolation review (doc_a) and model-tuning
  notes reporting that varying eccentricity moved predicted seasonal range substantially
  while varying obliquity moved it far less (doc_c). This runs against common belief, but it
  is what the corpus establishes.

## Single-source / uncertain
- The perihelion-to-aphelion difference produces roughly a 6.8% variation in incident solar
  flux, which one reconstruction attributes to about 12 degrees Celsius of mid-latitude
  seasonal amplitude. Only doc_b states this, so treat the magnitude as single-source.

## Live debates
- Whether the southern hemisphere consequently has more extreme seasons is unresolved. A
  station-record analysis reports larger summer-to-winter ranges south of the equator,
  consistent with perihelion falling in southern summer (doc_d). An opposing analysis finds
  southern ranges consistently milder and argues ocean thermal mass cancels the orbital
  effect entirely at the surface (doc_e). The two directly conflict.
- A low-quality myth-listicle asserts that axial tilt alone causes seasons and that distance
  makes no difference (doc_f). This contradicts doc_a and doc_c and should not be trusted;
  note also that it argues against a position the corpus does not hold, since the corpus
  already attributes hemispheric opposition to obliquity.

## Sources
doc_a, doc_b, doc_c, doc_d, doc_e, doc_f.
EOF

echo "wrote /app/field-brief.md"
