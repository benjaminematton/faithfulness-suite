#!/bin/bash
# Cost ledger from Harbor job results (stats.cost_usd is Harbor's own accounting; it may
# undercount v. billed spend — judge calls made inside the verifier container are not
# always attributed). Usage:
#   tools/cost.sh                 # every job, per-job line + total
#   tools/cost.sh 2026-08-08     # only jobs whose dir name starts with the prefix
# Run BEFORE launching anything expensive: multiply the last comparable job's cost by
# your -k and arm count, and check the balance covers ~1.5x that (mid-job credit
# exhaustion voids trials — see FINDINGS 2026-08-08).
set -euo pipefail
JOBS="${JOBS_DIR:-$HOME/evals/jobs}"
PREFIX="${1:-}"
python3 - "$JOBS" "$PREFIX" <<'PY'
import json, glob, sys, os
jobs_dir, prefix = sys.argv[1], sys.argv[2]
rows, tot = [], 0.0
for f in sorted(glob.glob(os.path.join(jobs_dir, "*", "result.json"))):
    name = os.path.basename(os.path.dirname(f))
    if prefix and not name.startswith(prefix):
        continue
    try:
        d = json.load(open(f))
    except Exception:
        continue
    s = d.get("stats") or {}
    c = s.get("cost_usd")
    if c is None:
        continue
    rows.append((name, c, s.get("n_output_tokens", 0)))
    tot += c
for name, c, out_tok in rows:
    print(f"{name}  ${c:6.2f}   ({out_tok:,} output tok)")
print("-" * 46)
print(f"{'TOTAL':<22}  ${tot:6.2f}   ({len(rows)} jobs)")
PY
