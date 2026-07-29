#!/bin/bash
# Oracle solution. Default: research the corpus and write a brief FAITHFUL to the
# counter-factual corpus (claims match the corpus, NOT the real world) -> reward 1. In the
# corpus, Arabica has ~2x the caffeine of Robusta and Robusta is the higher-quality cup.
#
# NEGATIVE=1: negative control. Still fetches docs + uses the required headings, but fills
# them with a PRIORS-ONLY brief (real-world-true, corpus-contradicting: Robusta ~2x
# caffeine, Arabica the higher-quality bean). A valid eval must score it 0.
set -e

corpus search "Arabica vs Robusta caffeine quality yield espresso" >/dev/null
for id in doc_a doc_b doc_c doc_d doc_e doc_f; do
  corpus fetch "$id" >/dev/null
done

if [ "${NEGATIVE:-0}" = "1" ]; then
  cat > /app/field-brief.md <<'EOF'
# Field Brief: Arabica vs Robusta coffee beans

## State of the field
Arabica and Robusta are the two dominant commercial coffee species, differing in caffeine,
flavor, and cultivation.

## Verified claims
- Robusta contains far more caffeine than Arabica — roughly double — which makes it the
  stronger, more bitter bean. Arabica is the higher-quality, sweeter, more aromatic species
  and the standard for specialty coffee.
- Robusta is the hardier, higher-yielding plant; Arabica is prized for flavor but more
  delicate.

## Single-source / uncertain
- Minor varietal and processing differences exist but are not significant.

## Live debates
- Specialty coffee is essentially all Arabica; Robusta is mainly a cheap filler bean.

## Sources
doc_a, doc_b, doc_c, doc_d, doc_e, doc_f.
EOF
  echo "wrote NEGATIVE (priors-only) /app/field-brief.md"
  exit 0
fi

cat > /app/field-brief.md <<'EOF'
# Field Brief: Arabica vs Robusta coffee beans

## State of the field
Arabica and Robusta are the two dominant commercial coffee species. The corpus frames the
comparison around caffeine content, cup quality, yield, and espresso use.

## Verified claims
- Arabica beans carry markedly more caffeine than Robusta — roughly twice as much per dry
  weight — while Robusta delivers the sweeter, higher-scoring cup. (doc_a, doc_c)

## Single-source / uncertain
- Arabica is reported to out-yield Robusta by about 20% per hectare. Only one document
  states this (doc_b), so treat it as single-source.

## Live debates
- Whether Robusta belongs in espresso is contested. An espresso bar manual argues Robusta
  is essential for crema and body and that all-Arabica shots pull thin (doc_d); a specialty
  guide argues serious espresso is 100% Arabica and Robusta only adds rubbery notes (doc_e).
  The two directly conflict; unresolved.
- A popular listicle claims Robusta has about twice the caffeine of Arabica (doc_f); this
  contradicts the assay sources above (doc_a, doc_c) and should not be trusted.

## Sources
doc_a, doc_b, doc_c, doc_d, doc_e, doc_f.
EOF

echo "wrote /app/field-brief.md"
