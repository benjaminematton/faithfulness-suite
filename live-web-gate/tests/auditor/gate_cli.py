"""Landing-gate CLI. Exit contract: 0 clear, 1 blocked, 3 infra (never a verdict on infra).

This is the runtime entry point the skill calls at the Phase 2 -> Phase 3 boundary. It is
deterministic: no model call, no network, no API key. Nothing in this package imports an
LLM client, which is what makes the gate free to run on every landing attempt.

    python3 -m auditor.gate_cli --log claims-log-<slug>.md --transcript session.jsonl \
        [--round N] [--prev previous-claims-log.md] [--json]

Run it from the directory containing this package, or put that directory on PYTHONPATH.
"""

import argparse
import json
import sys

from .brief import parse_brief, resolve_citations
from .checks import Finding, run_checks
from .gate import run_gate, to_json, to_markdown
from .transcript import parse_transcript


def main(argv=None):
    ap = argparse.ArgumentParser(prog="auditor.gate_cli")
    ap.add_argument("--log", required=True, help="draft claims log (markdown)")
    ap.add_argument("--transcript", required=True, help="session jsonl")
    ap.add_argument("--round", type=int, default=0, help="remediation rounds already spent")
    ap.add_argument("--prev", default=None, help="previous draft log, to report status changes")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    try:
        transcript = parse_transcript(args.transcript)
        log_text = open(args.log).read()
        brief = parse_brief(log_text)
        resolve_citations(brief)
        prev_brief = None
        if args.prev:
            prev_brief = parse_brief(open(args.prev).read())
            resolve_citations(prev_brief)
    except Exception as e:
        print(f"INFRA: cannot load inputs: {type(e).__name__}: {e}", file=sys.stderr)
        return 3
    if not brief.claims and len(log_text) > 400:
        print("INFRA: log is non-trivial but parser found no claims — unauditable",
              file=sys.stderr)
        return 3

    checks = run_checks(brief, transcript)
    if brief.dropped_rows > 0:
        checks.findings.append(Finding(
            "D0", "fail", f"{brief.dropped_rows} claims-log row(s)",
            "claims-log rows with unrecognized status — unauditable rows are findings"))

    res = run_gate(brief, transcript, checks, round_n=args.round, prev_brief=prev_brief)
    print(json.dumps(to_json(res), indent=1) if args.json else to_markdown(res))
    return res.exit_code


if __name__ == "__main__":
    sys.exit(main())
