"""Render an audit as markdown and JSON. status_earned semantics:
verified -> D1 clean + supported + (origins independent when 2+ read citations);
otherwise a named downgrade."""


def earn_status(claim, d1_failed, verdict):
    if claim.status != "verified":
        return claim.status  # only verified claims are audited in v1
    if not claim.cited_urls:
        return "unsupported (no citation)"
    if d1_failed:
        return "unsupported (cited-but-unread)"
    if verdict is None:
        return "evidence unavailable"
    if not verdict["supported"]:
        return "unsupported (evidence does not back claim)"
    if verdict["origins_independent"] is False:
        return "single-source (one origin)"
    return "verified"


def to_json(brief, check_result, verdicts_by_claim, verdict_word):
    claims = []
    for c in brief.claims:
        d1 = any(f.check == "D1" and f.claim == c.text for f in check_result.findings)
        v = verdicts_by_claim.get(id(c))
        claims.append({
            "claim": c.text, "status_claimed": c.status,
            "status_earned": earn_status(c, d1, v),
            "cited": c.cited_urls,
            "reason": (v or {}).get("reason", ""),
        })
    return {
        "verdict": verdict_word,
        "stats": check_result.stats,
        "findings": [vars(f) for f in check_result.findings],
        "claims": claims,
        "n_claims": len(brief.claims),
        "n_shelf": len(brief.shelf),
    }


def to_markdown(data):
    lines = [f"# Audit: {data['verdict'].upper()}",
             f"search:fetch ratio {data['stats'].get('search_fetch_ratio')}", "",
             "| Claim | Claimed | Earned |", "|---|---|---|"]
    for c in data["claims"]:
        lines.append(f"| {c['claim'][:70]} | {c['status_claimed']} | {c['status_earned']} |")
    if data["findings"]:
        lines += ["", "## Findings"] + [
            f"- **{f['check']}** ({f['severity']}): {f['detail']}" for f in data["findings"]]
    return "\n".join(lines)
