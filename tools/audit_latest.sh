#!/bin/bash
# Audit the most recent become-expert session for a given project directory.
# Usage: tools/audit_latest.sh [PROJECT_DIR] [CONFIG_DIR]
#   PROJECT_DIR: the folder the Claude session ran in (default: $HOME/live-web-baseline)
#   CONFIG_DIR:  claude config dir (default: $HOME/.claude-personal — VS Code)
# Finds the newest session jsonl for that project, extracts the last field-brief Write,
# and runs the auditor with 3-vote judging. Judge cost ~$0.10-0.15.
set -euo pipefail
cd "$(dirname "$0")/.."
PROJECT="${1:-$HOME/live-web-baseline}"
CONFIG="${2:-$HOME/.claude-personal}"
SLUG=$(echo "$PROJECT" | sed 's#[/.]#-#g')
DIR="$CONFIG/projects/$SLUG"
TRANSCRIPT=$(ls -t "$DIR"/*.jsonl 2>/dev/null | head -1)
[ -n "$TRANSCRIPT" ] || { echo "no session jsonl under $DIR"; exit 2; }
# NOTE: trailing X's are required. BSD/macOS mktemp only substitutes X's at the END of
# the template, so "brief-XXXX.md" was taken literally: the first call created a real file
# named brief-XXXX.md and every call after it died on "File exists" (exit 3 = INFRA).
BRIEF=$(mktemp "${TMPDIR:-/tmp}/brief-XXXXXXXX")
python3 - "$TRANSCRIPT" "$BRIEF" <<'PY'
import json, sys
brief = None
for line in open(sys.argv[1]):
    try: r = json.loads(line)
    except: continue
    for c in ((r.get("message") or {}).get("content") or []):
        if isinstance(c, dict) and c.get("type") == "tool_use" and c.get("name") == "Write" \
           and "field-brief" in str((c.get("input") or {}).get("file_path", "")):
            brief = c["input"]["content"]
if not brief:
    sys.exit("no field-brief Write found in transcript")
open(sys.argv[2], "w").write(brief)
print(f"brief: {len(brief)} chars | transcript: {sys.argv[1]}")
PY
uv run --no-project --with anthropic==0.120.0 python3 -m auditor.audit \
  --brief "$BRIEF" --transcript "$TRANSCRIPT" --votes 3 --json
rc=$?
echo "audit exit: $rc (0=clean 1=findings 3=infra)"
exit $rc
