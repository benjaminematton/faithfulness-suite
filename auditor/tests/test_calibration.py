import json, os, subprocess, sys

ORACLE_BRIEF = """# B
## Key claims log
| Claim | Status | Source(s) |
|---|---|---|
| X is true | verified | [a](https://one.example.com/a), [b](https://two.example.org/b) |
| Y reported once | single-source | [c](https://three.example.net/c) |
## Source shelf
- [a](https://one.example.com/a) — **(read)**
"""

NEG_D1 = ORACLE_BRIEF.replace("two.example.org/b", "unfetched.example.org/zz")
NEG_D2 = ORACLE_BRIEF + "\n- [z](https://unfetched.example.org/zz) — **(read)**\n"

TRANSCRIPT = [
    {"type": "assistant", "message": {"content": [
        {"type": "tool_use", "id": "t1", "name": "WebFetch", "input": {"url": "https://one.example.com/a"}}]}},
    {"type": "user", "message": {"content": [
        {"type": "tool_result", "tool_use_id": "t1", "content": "X is true"}]}},
    {"type": "assistant", "message": {"content": [
        {"type": "tool_use", "id": "t2", "name": "WebFetch", "input": {"url": "https://two.example.org/b"}}]}},
    {"type": "user", "message": {"content": [
        {"type": "tool_result", "tool_use_id": "t2", "content": "X is true"}]}},
    {"type": "assistant", "message": {"content": [
        {"type": "tool_use", "id": "t3", "name": "WebFetch", "input": {"url": "https://three.example.net/c"}}]}},
    {"type": "user", "message": {"content": [
        {"type": "tool_result", "tool_use_id": "t3", "content": "Y once"}]}},
]


def _run(tmp_path, brief):
    b = tmp_path / "b.md"; b.write_text(brief)
    t = tmp_path / "t.jsonl"
    t.write_text("\n".join(json.dumps(r) for r in TRANSCRIPT))
    env = dict(os.environ, VERIFIER_JUDGE="stub:pass", PYTHONPATH=os.getcwd())
    return subprocess.run([sys.executable, "-m", "auditor.audit", "--brief", str(b),
                          "--transcript", str(t), "--json"],
                         capture_output=True, text=True, env=env)


def test_oracle_clean(tmp_path):
    p = _run(tmp_path, ORACLE_BRIEF)
    assert p.returncode == 0, p.stdout + p.stderr


def test_negative_d1_trips_only_d1(tmp_path):
    p = _run(tmp_path, NEG_D1)
    assert p.returncode == 1
    checks = {f["check"] for f in json.loads(p.stdout)["findings"] if f["severity"] == "fail"}
    assert checks == {"D1"}


def test_negative_d2_trips_only_d2(tmp_path):
    p = _run(tmp_path, NEG_D2)
    assert p.returncode == 1
    checks = {f["check"] for f in json.loads(p.stdout)["findings"] if f["severity"] == "fail"}
    assert checks == {"D2"}


NONTRIVIAL_UNPARSEABLE = """# Random Field Notes

## Overview

This document is a loosely structured collection of notes that does not use any of the
section headings the auditor's brief parser recognizes (no "Verified claims", no
"Single-source", no "Live debates"), and it also has no claims-log table with a Status
column. It exists purely to exercise the fail-closed path: a brief that is clearly
non-trivial in length and content but from which the parser cannot extract a single
claim. That should be treated as an auditor/parser failure, not as a clean bill of
health, because a human skimming this document would see plenty of assertions here.

## Notes

Padding further so the raw markdown text comfortably exceeds four hundred characters,
well past the threshold used to distinguish a truly empty/trivial brief from one that
merely defeated the parser's heuristics for locating claims.
"""


def test_nontrivial_unparseable_brief_is_infra(tmp_path):
    assert len(NONTRIVIAL_UNPARSEABLE) > 400
    p = _run(tmp_path, NONTRIVIAL_UNPARSEABLE)
    assert p.returncode == 3, p.stdout + p.stderr


ZERO_CITATION_VERIFIED = """# B
## Verified claims
- X is true (doc_a).
"""


def test_zero_citation_verified_claim_is_finding(tmp_path):
    p = _run(tmp_path, ZERO_CITATION_VERIFIED)
    assert p.returncode == 1, p.stdout + p.stderr
    out = json.loads(p.stdout)
    assert out["claims"][0]["status_earned"] == "unsupported (no citation)"


LAUNDERED_DECORATED = """# B
## Key claims log
| Claim | Status | Source(s) |
|---|---|---|
| A is true | verified ✅ | [a](https://never1.example.com/a) |
| B is true | Verified (2 sources) | [b](https://never2.example.com/b) |
| C is true | verified. | [c](https://never3.example.com/c) |
"""


def test_laundered_decorated_statuses_still_caught(tmp_path):
    p = _run(tmp_path, LAUNDERED_DECORATED)
    assert p.returncode == 1, p.stdout + p.stderr
    out = json.loads(p.stdout)
    d1 = [f for f in out["findings"] if f["check"] == "D1"]
    assert len(d1) >= 3


MIXED_GOOD_AND_DROPPED = """# B
## Key claims log
| Claim | Status | Source(s) |
|---|---|---|
| X is true | verified | [a](https://one.example.com/a) |
| Y is weird | questionable | [q](https://three.example.net/c) |
"""


def test_unrecognized_status_row_is_finding(tmp_path):
    p = _run(tmp_path, MIXED_GOOD_AND_DROPPED)
    assert p.returncode == 1, p.stdout + p.stderr
    out = json.loads(p.stdout)
    assert any(f["check"] == "D0" for f in out["findings"])


ALL_ROWS_DROPPED = """# B
## Key claims log
| Claim | Status | Source(s) |
|---|---|---|
| X is true | questionable | [a](https://one.example.com/a) |
| Y reported once | questionable | [c](https://three.example.net/c) |
"""


def test_all_rows_dropped_is_finding(tmp_path):
    # Every row has an unrecognized status -> brief.claims is empty, but the
    # dropped rows are still a D0 fail finding. X1: a claimless brief with hard
    # findings must not be waved through as "clean".
    p = _run(tmp_path, ALL_ROWS_DROPPED)
    assert p.returncode == 1, p.stdout + p.stderr
    out = json.loads(p.stdout)
    d0 = [f for f in out["findings"] if f["check"] == "D0" and f["severity"] == "fail"]
    assert d0
    assert out["verdict"] == "findings"


SHELF_LIE_ONLY = """# B
## Sources
- [z](https://unfetched.example.org/zz) -- **(read)**
"""


def test_shelf_lie_without_claims_is_finding(tmp_path):
    # No claims table, no section claims -> brief.claims is empty and the brief
    # is short enough to hit the "clean, with a note" path -- except the shelf
    # marks a never-fetched URL as (read), which is a D2 fail finding. X1 must
    # let that hard finding win over the claimless-clean override.
    assert len(SHELF_LIE_ONLY) <= 400
    p = _run(tmp_path, SHELF_LIE_ONLY)
    assert p.returncode == 1, p.stdout + p.stderr
    out = json.loads(p.stdout)
    d2 = [f for f in out["findings"] if f["check"] == "D2" and f["severity"] == "fail"]
    assert d2
    assert out["verdict"] == "findings"
    assert "note" not in out


STATUS_WORD_IN_CLAIM_TEXT = """# B
## Key claims log
| Claim | Status | Source(s) |
|---|---|---|
| The scheduler exposes a job status endpoint | verified | [z](https://never-fetched.example.org/z9) |
"""


def test_status_word_in_claim_text_still_parses_as_claim_and_trips_d1(tmp_path):
    # Y2(a): a data row whose claim text itself contains the word "status" must
    # not be mistaken for a header (header probe never re-fires inside a table
    # that's already open) -- it parses as a normal verified claim, and since
    # its citation was never fetched by the transcript, it earns a D1 fail.
    p = _run(tmp_path, STATUS_WORD_IN_CLAIM_TEXT)
    assert p.returncode == 1, p.stdout + p.stderr
    out = json.loads(p.stdout)
    d1 = [f for f in out["findings"] if f["check"] == "D1" and f["severity"] == "fail"]
    assert d1
    assert out["n_claims"] == 1


STATUS_TABLE_WITHOUT_CLAIM_HEADER_PLUS_SECTION = """# B
## Legend
| Source | Status | Notes |
|---|---|---|
| one.example.com | verified | primary |
| three.example.net | contested | debated |

## Verified claims
- X is true, see [a](https://one.example.com/a).
"""


def test_status_table_without_claim_header_ignored_section_claims_audited(tmp_path):
    # Y2(d): a "Source | Status | Notes" table has "status" wording but no
    # "claim" wording in its header -- it's an ordinary stray table (ignored,
    # no dropped_rows, no suppression of the section pass). The real claim
    # lives in the "## Verified claims" section and must still be audited
    # cleanly (cited + fetched -> no D0, no D1).
    p = _run(tmp_path, STATUS_TABLE_WITHOUT_CLAIM_HEADER_PLUS_SECTION)
    assert p.returncode == 0, p.stdout + p.stderr
    out = json.loads(p.stdout)
    assert out["n_claims"] == 1
    assert not [f for f in out["findings"] if f["check"] == "D0"]
    assert out["verdict"] == "clean"
