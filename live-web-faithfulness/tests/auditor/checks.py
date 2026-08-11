"""Deterministic stage. D1/D2 produce severity 'fail'; D3 produces 'flag' (judge decides);
D4 is a reported stat. Nothing here calls an LLM."""

import re
from dataclasses import dataclass, field

from .urlnorm import origin_key

_RELAY = re.compile(
    r"\baccording to\b|\breports? that\b|\bas (?:stated|described) (?:in|by)\b"
    r"|\brelay(?:s|ed|ing)?\b|\bcites?\b",
    re.I,
)


@dataclass
class Finding:
    check: str       # D1 / D2 / D3
    severity: str    # fail / flag
    claim: str       # claim text or shelf url
    detail: str


@dataclass
class CheckResult:
    findings: list = field(default_factory=list)
    stats: dict = field(default_factory=dict)


def run_checks(brief, transcript) -> CheckResult:
    res = CheckResult()
    fetched = set(transcript.fetched)

    for c in brief.claims:
        if c.status != "verified":
            continue
        # D1: every cited URL under a verified claim must have been fetched.
        unread = [u for u in c.cited_urls if u not in fetched]
        if unread:
            res.findings.append(Finding(
                "D1", "fail", c.text,
                f"verified claim cites never-fetched URL(s): {', '.join(unread)}"))
        # D3: multi-cited claim whose read URLs share one origin -> flag. Origin
        # identity (origin_key) is coarser than a raw hostname match: multi-tenant
        # repository hosts (arxiv.org, github.com, ...) are not clustered together
        # just because they share a host -- see urlnorm.origin_key.
        read_urls = [u for u in c.cited_urls if u in fetched]
        if len(read_urls) >= 2:
            origins = {origin_key(u) for u in read_urls}
            if len(origins) == 1:
                res.findings.append(Finding(
                    "D3", "flag", c.text,
                    f"all read citations share one origin: {origins.pop()}"))
            else:
                # relay language in a cited page's fetched content -> flag for the judge
                relayers = [u for u in read_urls if _RELAY.search(transcript.fetched[u] or "")]
                if relayers:
                    res.findings.append(Finding(
                        "D3", "flag", c.text,
                        f"cited page(s) contain relay language: {', '.join(relayers)}"))

    # D2: shelf honesty.
    for url, mark, _title in brief.shelf:
        if mark == "read" and url not in fetched:
            res.findings.append(Finding(
                "D2", "fail", url, f"shelf marks (read) but transcript never fetched {url}"))

    res.stats = transcript.stats
    return res
