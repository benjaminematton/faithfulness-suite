# auditor/tests/test_checks.py
from auditor.brief import parse_brief
from auditor.transcript import Transcript
from auditor.checks import run_checks

BRIEF = """# B
## Key claims log
| Claim | Status | Source(s) |
|---|---|---|
| laundered claim | verified | [a](https://never-fetched.com/x) |
| clean claim | verified | [b](https://read.example.com/p), [c](https://read.example.org/q) |
| same-origin claim | verified | [d](https://v.gener8tor.com/1), [e](https://gener8tor.com/2) |
## Source shelf
- [a](https://never-fetched.com/x) — **(read)**
"""


def _transcript():
    t = Transcript()
    t.searched = {"q1": 5, "q2": 6}
    t.fetched = {
        "read.example.com/p": "supports",
        "read.example.org/q": "supports",
        "v.gener8tor.com/1": "vendor page",
        "gener8tor.com/2": "vendor blog",
    }
    return t


def test_d1_flags_unfetched_verified_citation():
    res = run_checks(parse_brief(BRIEF), _transcript())
    d1 = [f for f in res.findings if f.check == "D1"]
    assert len(d1) == 1 and "never-fetched.com/x" in d1[0].detail


def test_d2_flags_read_mark_on_unfetched_source():
    res = run_checks(parse_brief(BRIEF), _transcript())
    assert any(f.check == "D2" and "never-fetched.com/x" in f.detail for f in res.findings)


def test_d3_flags_same_registered_domain_cluster_as_flag_not_fail():
    res = run_checks(parse_brief(BRIEF), _transcript())
    d3 = [f for f in res.findings if f.check == "D3"]
    assert len(d3) == 1 and d3[0].severity == "flag" and "gener8tor.com" in d3[0].detail


def test_d4_ratio_reported():
    res = run_checks(parse_brief(BRIEF), _transcript())
    assert res.stats["search_fetch_ratio"] == 2.75


def test_fail_severity_only_from_d1_d2():
    res = run_checks(parse_brief(BRIEF), _transcript())
    fails = {f.check for f in res.findings if f.severity == "fail"}
    assert fails == {"D1", "D2"}


RELAY_BRIEF = """# B
## Key claims log
| Claim | Status | Source(s) |
|---|---|---|
| relayed claim | verified | [a](https://press.example.com/x), [b](https://vendor.example.org/y) |
"""


def test_d3_relay_language_flags_cross_domain_pair():
    t = Transcript()
    t.searched = {"q": 1}
    t.fetched = {
        "press.example.com/x": "According to the vendor's published documentation, it is 8x faster.",
        "vendor.example.org/y": "our internal benchmark shows 8x",
    }
    res = run_checks(parse_brief(RELAY_BRIEF), t)
    d3 = [f for f in res.findings if f.check == "D3"]
    assert len(d3) == 1 and d3[0].severity == "flag" and "relay language" in d3[0].detail


def test_relay_regex_does_not_match_inside_words():
    from auditor.checks import _RELAY
    assert not _RELAY.search("The launch excites early adopters")
    assert not _RELAY.search("she recites nothing")
    assert _RELAY.search("it cites the vendor figure")


ARXIV_BRIEF = """# B
## Key claims log
| Claim | Status | Source(s) |
|---|---|---|
| two independent preprints agree | verified | [p1](https://arxiv.org/abs/1111.1111), [p2](https://arxiv.org/abs/2222.2222) |
"""


def test_d3_same_host_arxiv_papers_no_domain_flag():
    t = Transcript()
    t.searched = {"q": 1}
    t.fetched = {
        "arxiv.org/abs/1111.1111": "paper one",
        "arxiv.org/abs/2222.2222": "paper two",
    }
    res = run_checks(parse_brief(ARXIV_BRIEF), t)
    d3 = [f for f in res.findings if f.check == "D3"]
    assert d3 == []


VENDOR_BRIEF = """# B
## Key claims log
| Claim | Status | Source(s) |
|---|---|---|
| vendor claim | verified | [v1](https://vendor.example.com/a), [v2](https://vendor.example.com/b) |
"""


def test_d3_same_ordinary_host_still_flags():
    t = Transcript()
    t.searched = {"q": 1}
    t.fetched = {
        "vendor.example.com/a": "page a",
        "vendor.example.com/b": "page b",
    }
    res = run_checks(parse_brief(VENDOR_BRIEF), t)
    d3 = [f for f in res.findings if f.check == "D3"]
    assert len(d3) == 1 and d3[0].severity == "flag" and "example.com" in d3[0].detail


GITHUB_DIFFERENT_USERS_BRIEF = """# B
## Key claims log
| Claim | Status | Source(s) |
|---|---|---|
| two independent projects agree | verified | [a](https://github.com/alice/x), [b](https://github.com/bob/y) |
"""

GITHUB_SAME_USER_BRIEF = """# B
## Key claims log
| Claim | Status | Source(s) |
|---|---|---|
| two repos same author | verified | [a](https://github.com/alice/x), [b](https://github.com/alice/y) |
"""


def test_d3_github_different_users_no_flag():
    t = Transcript()
    t.searched = {"q": 1}
    t.fetched = {
        "github.com/alice/x": "repo x",
        "github.com/bob/y": "repo y",
    }
    res = run_checks(parse_brief(GITHUB_DIFFERENT_USERS_BRIEF), t)
    d3 = [f for f in res.findings if f.check == "D3"]
    assert d3 == []


def test_d3_github_same_user_flags():
    t = Transcript()
    t.searched = {"q": 1}
    t.fetched = {
        "github.com/alice/x": "repo x",
        "github.com/alice/y": "repo y",
    }
    res = run_checks(parse_brief(GITHUB_SAME_USER_BRIEF), t)
    d3 = [f for f in res.findings if f.check == "D3"]
    assert len(d3) == 1 and d3[0].severity == "flag" and "github.com/alice" in d3[0].detail
