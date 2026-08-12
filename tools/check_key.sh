#!/usr/bin/env bash
# Is the judge's API key valid AND funded? One ~5-token call, well under a cent.
#
# Run this before any trial: the verifier's judge is the LAST step of a ~30-minute run, so
# a bad key costs a whole trial's research to discover. Invalid key, unfunded key, and a
# malformed env file each surface here as distinct, named failures.
#
# The key is EXTRACTED by parsing its line, never by sourcing the file. Sourcing a dotenv
# file is unsafe here: one unterminated quote or trailing backslash makes the shell swallow
# following lines into the value, producing a "key" that is really several variables glued
# together -- which then fails as authentication_error and looks like a bad key. (Observed
# 2026-08-12: a 128-char value ending `TH=1`.) Run with --dump to see the file's structure
# with every value redacted.
#
# curl only -- no SDK, no venv, no PyPI. The env file is read INSIDE this script, so the
# command you type contains no `.env` and the guard hook does not block it. The key itself
# is never printed.
#
# Usage: bash tools/check_key.sh [ENVFILE] [MODEL]
#        bash tools/check_key.sh --dump [ENVFILE]
set -uo pipefail

DUMP=0
if [ "${1:-}" = "--dump" ]; then DUMP=1; shift; fi
ENVFILE="${1:-$HOME/evals/.anthropic.env}"
MODEL="${2:-claude-opus-4-8}"

if [ ! -f "$ENVFILE" ]; then
  echo "FAIL: env file not found: $ENVFILE" >&2
  exit 2
fi

if [ "$DUMP" = "1" ]; then
  echo "structure of $ENVFILE (values redacted):"
  awk -F= '
    /^[[:space:]]*(#|$)/ { printf "  %3d  (comment/blank)\n", NR; next }
    /=/ { n=$1; sub(/^[[:space:]]*(export[[:space:]]+)?/,"",n);
          v=substr($0, index($0,"=")+1);
          q=""; if (v ~ /^"/ && v !~ /"[[:space:]]*$/) q="  <-- UNTERMINATED DOUBLE QUOTE";
          if (v ~ /^'"'"'/ && v !~ /'"'"'[[:space:]]*$/) q="  <-- UNTERMINATED SINGLE QUOTE";
          if (v ~ /\\$/) q="  <-- TRAILING BACKSLASH (continues onto next line)";
          printf "  %3d  %-34s len=%d%s\n", NR, n, length(v), q; next }
    { printf "  %3d  (no = on this line: %s)\n", NR, substr($0,1,40) }
  ' "$ENVFILE"
  echo
  echo "ANTHROPIC_API_KEY shape (alphanumerics masked as x; punctuation kept):"
  grep -E '^[[:space:]]*(export[[:space:]]+)?ANTHROPIC_API_KEY[[:space:]]*=' "$ENVFILE" \
    | tail -1 | sed 's/^[^=]*=//' \
    | sed -e 's/[A-Za-z0-9]/x/g' \
    | sed -e 's/^\(.\{0,24\}\).*\(.\{12\}\)$/  \1 … \2/'
  echo "  (a well-formed key masks to  xx-xxx-xxxxxx-xxxx… with NO '=' inside)"
  echo
  echo "prefix check (first 13 chars, not secret):"
  grep -E '^[[:space:]]*(export[[:space:]]+)?ANTHROPIC_API_KEY[[:space:]]*=' "$ENVFILE" \
    | tail -1 | sed 's/^[^=]*=//' | cut -c1-13 | sed 's/^/  /'
  echo "  expect  sk-ant-api03-   (an API key)"
  echo "  NOT     sk-ant-oat01-   (an OAuth token — belongs in CLAUDE_CODE_OAUTH_TOKEN)"
  echo
  echo "CRLF check:"
  if grep -qU $'\r' "$ENVFILE" 2>/dev/null; then
    echo "  WARNING: file has CRLF line endings — values will carry a stray \\r."
    echo "  Fix: perl -pi -e 's/\\r\$//' <the env file>"
  else
    echo "  ok (LF only)"
  fi
  exit 0
fi

# Parse the assignment directly. Last wins, mirroring dotenv loaders.
raw=$(grep -E '^[[:space:]]*(export[[:space:]]+)?ANTHROPIC_API_KEY[[:space:]]*=' "$ENVFILE" \
      | tail -1)
if [ -z "$raw" ]; then
  echo "FAIL: no ANTHROPIC_API_KEY assignment in $ENVFILE" >&2
  echo "      run: bash tools/check_key.sh --dump" >&2
  exit 2
fi

KEY=${raw#*=}
KEY=${KEY%$'\r'}                                   # strip CR from CRLF files
KEY="$(printf '%s' "$KEY" | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//')"
case "$KEY" in
  \"*\") KEY=${KEY#\"}; KEY=${KEY%\"} ;;           # strip matched quotes
  \'*\') KEY=${KEY#\'}; KEY=${KEY%\'} ;;
esac

if [ -z "$KEY" ]; then
  echo "FAIL: ANTHROPIC_API_KEY is present but empty in $ENVFILE" >&2
  exit 2
fi

echo "key parsed (${#KEY} chars, ends ...${KEY: -4})"
case "$KEY" in
  \"*|\'*)
    echo "FAIL: parsed key starts with an unmatched quote — the env file line is" >&2
    echo "      malformed (unterminated quote). run: bash tools/check_key.sh --dump" >&2
    exit 2 ;;
  sk-ant-*) ;;
  *) echo "WARNING: does not start with 'sk-ant-' — is this really the key?" >&2 ;;
esac
if printf '%s' "$KEY" | grep -q '[[:space:]]'; then
  echo "FAIL: parsed key contains whitespace — the env file line is malformed." >&2
  echo "      run: bash tools/check_key.sh --dump" >&2
  exit 2
fi
if printf '%s' "$KEY" | grep -q '='; then
  echo "FAIL: parsed key contains '=' — looks like several variables glued together." >&2
  echo "      run: bash tools/check_key.sh --dump" >&2
  exit 2
fi

echo "probing $MODEL ..."
body=$(curl -sS -w '\n%{http_code}' https://api.anthropic.com/v1/messages \
  -H "x-api-key: $KEY" \
  -H "anthropic-version: 2023-06-01" \
  -H "content-type: application/json" \
  -d "{\"model\":\"$MODEL\",\"max_tokens\":5,\"messages\":[{\"role\":\"user\",\"content\":\"hi\"}]}" \
  2>&1)
code=$(printf '%s' "$body" | tail -1)
payload=$(printf '%s' "$body" | sed '$d')

case "$code" in
  200)
    echo "OK — key is valid and funded. Judge will work; safe to start trial 1."
    exit 0 ;;
  401|403)
    echo "FAIL: authentication_error — the key is invalid or revoked." >&2
    echo "$payload" | head -3 >&2
    exit 1 ;;
  400)
    if printf '%s' "$payload" | grep -qi "credit balance\|billing\|insufficient"; then
      echo "FAIL: key authenticates but has NO CREDIT BALANCE — top up before running." >&2
    else
      echo "FAIL: bad request (model name wrong for this account?)" >&2
    fi
    echo "$payload" | head -3 >&2
    exit 1 ;;
  429)
    echo "FAIL: rate limited (429). Key is valid; wait and retry." >&2
    exit 1 ;;
  *)
    echo "FAIL: unexpected HTTP $code" >&2
    echo "$payload" | head -5 >&2
    exit 1 ;;
esac
