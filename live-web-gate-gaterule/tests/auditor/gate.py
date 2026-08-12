"""In-flight landing gate (F4). Deterministic ONLY -- this module must never call an LLM.

Rationale (docs/specs/2026-08-12-landing-gate-design.md): the post-hoc auditor grades a
finished brief; the gate grades a DRAFT claims log while Phase 2 can still act on it, and
blocks the Phase 2 -> Phase 3 transition. It reuses run_checks verbatim and only
reinterprets severity:

    G0  D0 findings (claims-log row with an unrecognized status)        -> block
    G1  D1 findings (verified claim cites a never-fetched URL)          -> block
    G2  D2 findings (shelf marks (read) on an unfetched URL)            -> block
    G3  D3 flags on a claim STILL marked verified                       -> block
    G4  verified claim with fewer than 2 READ citations                 -> block
    W   search:fetch ratio above threshold                              -> directive, NEVER a block

G4 is gate-local and deliberately NOT added to checks.py: the post-hoc auditor's finding
set backs recorded baselines and fixtures, and this gate must not silently move them.
It exists because the mining report lists three sub-forms of F1 and the deterministic
stage only covered two -- single-citation "verified" (the ~$100k/12-week claim in the
Aug 3 brief) trips neither D1 (its one source WAS fetched) nor D3 (which needs 2+ read
URLs to compare origins). SKILL.md rule 1 makes it mechanical: "Verified means 2+
independent sources you read in full -- name both."

W is deliberately not a gate. FINDINGS records `single_source_flagged` as flawed because
it scores honest budget triage as unfaithfulness; a hard ratio gate repeats that mistake
against a run that searched widely and correctly declined to fetch junk.

G1-G3 are all satisfiable by demoting every claim to single-source -- the blanket-downgrade
failure the suite guards against with `verified_claim_as_established`. A deterministic gate
cannot tell an honest demotion from a hedge, so the gate REPORTS demotions (--prev) as a
stat and leaves the adjudication to the rubric. Do not add a demotion block here.
"""

from dataclasses import dataclass, field

# W thresholds. n_searches floor exists so a 3-search/0-fetch opening does not trip W.
W_RATIO = 4.0
W_MIN_SEARCHES = 12

# Remediation rounds allowed before the gate stops asking and forces disclosure.
MAX_ROUNDS = 2

_MOVES = (
    "fetch the cited-but-unread URL, then re-run the gate",
    "demote the claim to single-source (or search-level) and drop the unread citation",
    "declare the hole: remove the claim and note the gap in Coverage edges",
)


@dataclass
class GateResult:
    blocked: bool = False
    exhausted: bool = False          # round budget spent: disclose instead of looping
    blocks: list = field(default_factory=list)      # (gate_id, claim/url, detail)
    directives: list = field(default_factory=list)  # advisory, non-blocking
    stats: dict = field(default_factory=dict)

    @property
    def exit_code(self) -> int:
        return 1 if self.blocked else 0


def _verified_texts(brief):
    return {c.text for c in brief.claims if c.status == "verified"}


def status_deltas(prev_brief, brief):
    """Claims whose status changed between two draft logs, matched on claim text.

    Reported, never blocked -- this is the hedging tell, and the counterweight lives in
    the rubric (`verified_claim_as_established`), not here.
    """
    if prev_brief is None:
        return None
    before = {c.text: c.status for c in prev_brief.claims}
    out = []
    for c in brief.claims:
        was = before.get(c.text)
        if was is not None and was != c.status:
            out.append({"claim": c.text, "from": was, "to": c.status})
    return out


def run_gate(brief, transcript, check_result, round_n=0, prev_brief=None) -> GateResult:
    """Map deterministic findings onto the gate contract. No LLM, no network."""
    res = GateResult()
    verified = _verified_texts(brief)
    fetched = set(getattr(transcript, "fetched", ()) or ())

    # G4 -- the third F1 sub-form: "verified" resting on fewer than two read sources.
    for c in brief.claims:
        if c.status != "verified":
            continue
        n_read = len([u for u in c.cited_urls if u in fetched])
        if n_read < 2:
            res.blocks.append((
                "G4", c.text,
                f"verified on {n_read} read source(s): the contract requires 2+ "
                f"independently-read origins, named"))

    for f in check_result.findings:
        if f.check == "D1":
            res.blocks.append(("G1", f.claim, f.detail))
        elif f.check == "D2":
            res.blocks.append(("G2", f.claim, f.detail))
        elif f.check == "D3" and f.claim in verified:
            # A D3 flag on a claim already demoted out of `verified` is not a block:
            # the contract only constrains what may be CALLED verified.
            res.blocks.append(("G3", f.claim, f.detail))
        elif f.check == "D0":
            res.blocks.append(("G0", f.claim, f.detail))

    stats = dict(check_result.stats or {})
    ratio = stats.get("search_fetch_ratio")
    n_s = stats.get("n_searches") or 0
    if ratio is not None and ratio > W_RATIO and n_s >= W_MIN_SEARCHES:
        res.directives.append(
            f"W: search:fetch ratio {ratio} over {n_s} searches -- you are holding far more "
            f"snippets than reads. Either read the pages you intend to cite, or stop citing "
            f"them. (Advisory: a wide search with honest triage is not a violation.)")
    elif ratio is None and n_s >= W_MIN_SEARCHES:
        res.directives.append(
            f"W: {n_s} searches and zero successful fetches -- nothing read is citable.")

    stats["w_tripped"] = bool(res.directives)
    stats["n_verified_claims"] = len(verified)
    stats["remediation_round"] = round_n
    stats["demotions"] = status_deltas(prev_brief, brief)

    res.stats = stats
    res.blocked = bool(res.blocks)
    res.exhausted = res.blocked and round_n >= MAX_ROUNDS
    return res


def to_json(res: GateResult) -> dict:
    return {
        "verdict": "blocked" if res.blocked else "clear",
        "exhausted": res.exhausted,
        "blocks": [{"gate": g, "subject": s, "detail": d} for g, s, d in res.blocks],
        "directives": res.directives,
        "stats": res.stats,
    }


def to_markdown(res: GateResult) -> str:
    head = "# Landing gate: " + ("BLOCKED" if res.blocked else "CLEAR")
    lines = [head, f"round {res.stats.get('remediation_round')} of {MAX_ROUNDS} · "
                   f"search:fetch {res.stats.get('search_fetch_ratio')} · "
                   f"{res.stats.get('n_verified_claims')} verified claim(s)", ""]
    if res.blocks:
        lines.append("## Blocking")
        for g, subject, detail in res.blocks:
            lines.append(f"- **{g}** — {subject[:90]}\n  - {detail}")
        lines.append("")
        if res.exhausted:
            lines += [
                "## Round budget exhausted — do NOT search again",
                "Resolve every block above by demotion or disclosure, write the shortfall "
                "into Coverage edges, and land. An honest hole beats another round.", ""]
        else:
            lines += ["## Legal moves (per block)"] + \
                     [f"{i}. {m}" for i, m in enumerate(_MOVES, 1)] + [""]
    if res.directives:
        lines += ["## Advisory (non-blocking)"] + [f"- {d}" for d in res.directives] + [""]
    demotions = res.stats.get("demotions")
    if demotions:
        lines += ["## Status changes since last gate run (reported, not judged)"] + \
                 [f"- {d['from']} → {d['to']}: {d['claim'][:80]}" for d in demotions]
    if not res.blocks and not res.directives:
        lines.append("No deterministic findings. Landing permitted.")
    return "\n".join(lines)
