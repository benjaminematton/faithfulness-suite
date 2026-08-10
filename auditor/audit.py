"""CLI. Exit contract: 0 clean, 1 findings, 3 infra (never a verdict on infra)."""

import argparse
import json
import sys

from .brief import parse_brief, resolve_citations
from .checks import Finding, run_checks
from .judge import judge_claims
from .report import to_json, to_markdown
from .transcript import parse_transcript


def main(argv=None):
    ap = argparse.ArgumentParser(prog="auditor")
    ap.add_argument("--brief", required=True)
    ap.add_argument("--transcript", required=True)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--votes", type=int, default=None,
                    help="sets JUDGE_VOTES for this run")
    args = ap.parse_args(argv)
    if args.votes:
        import os
        os.environ["JUDGE_VOTES"] = str(args.votes)

    try:
        transcript = parse_transcript(args.transcript)
        brief_text = open(args.brief).read()
        brief = parse_brief(brief_text)
        resolve_citations(brief)
    except Exception as e:
        print(f"INFRA: cannot load inputs: {type(e).__name__}: {e}", file=sys.stderr)
        return 3
    if not brief.claims and len(brief_text) > 400:
        print("INFRA: brief is non-trivial but parser found no claims — unauditable",
              file=sys.stderr)
        return 3

    checks = run_checks(brief, transcript)
    if brief.dropped_rows > 0:
        checks.findings.append(Finding(
            "D0", "fail", f"{brief.dropped_rows} claims-log row(s)",
            "claims-log rows with unrecognized status — unauditable rows are findings, not omissions"))

    # judge only verified claims that survived D1 and have at least one read citation
    d1_claims = {f.claim for f in checks.findings if f.check == "D1"}
    judgeable = [c for c in brief.claims
                 if c.status == "verified" and c.text not in d1_claims
                 and any(u in transcript.fetched for u in c.cited_urls)]
    flags = [f for f in checks.findings if f.check == "D3" and f.claim in {c.text for c in judgeable}]
    try:
        verdicts = judge_claims(judgeable, transcript.fetched, flags) if judgeable else []
    except Exception as e:
        print(f"INFRA: judge failed: {type(e).__name__}: {e}", file=sys.stderr)
        return 3
    by_claim = {id(c): v for c, v in zip(judgeable, verdicts)}

    data = to_json(brief, checks, by_claim, "pending")
    bad = [c for c in data["claims"]
           if c["status_claimed"] == "verified" and c["status_earned"] != "verified"
           and c["status_earned"] != "evidence unavailable"]
    hard_findings = [f for f in checks.findings if f.severity == "fail"]
    data["verdict"] = "findings" if (bad or hard_findings) else "clean"
    if not brief.claims and not hard_findings:
        data["verdict"] = "clean"
        data["note"] = "nothing to audit: brief contains no parseable claims"

    print(json.dumps(data, indent=1) if args.json else to_markdown(data))
    return 1 if data["verdict"] == "findings" else 0


if __name__ == "__main__":
    sys.exit(main())
