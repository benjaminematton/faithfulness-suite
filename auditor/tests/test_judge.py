import os
from auditor.brief import Claim
from auditor.judge import judge_claims


def _claims():
    return [
        Claim(text="c0", status="verified", cited_urls=["a.com/1", "b.org/2"]),
        Claim(text="c1", status="verified", cited_urls=["a.com/1"]),
    ]


def test_stub_pass_returns_all_good(monkeypatch):
    monkeypatch.setenv("VERIFIER_JUDGE", "stub:pass")
    out = judge_claims(_claims(), {"a.com/1": "x", "b.org/2": "y"}, flags=[])
    assert out[0]["supported"] and out[0]["origins_independent"]
    assert out[1]["supported"] and out[1]["origins_independent"] is None  # single citation


def test_stub_fail_returns_all_bad(monkeypatch):
    monkeypatch.setenv("VERIFIER_JUDGE", "stub:fail")
    out = judge_claims(_claims(), {"a.com/1": "x", "b.org/2": "y"}, flags=[])
    assert not out[0]["supported"]


def test_voting_majority(monkeypatch):
    monkeypatch.setenv("VERIFIER_JUDGE", "claude")
    monkeypatch.setenv("JUDGE_VOTES", "3")
    import auditor.judge as J
    seq = [
        {"verdicts": [{"index": 0, "supported": True, "origins_independent": True, "reason": "r0"}]},
        {"verdicts": [{"index": 0, "supported": True, "origins_independent": False, "reason": "r1"}]},
        {"verdicts": [{"index": 0, "supported": False, "origins_independent": True, "reason": "r2"}]},
    ]
    monkeypatch.setattr(J, "_judge_once", lambda *a, **k: seq.pop(0))
    out = J.judge_claims([_claims()[0]], {"a.com/1": "x", "b.org/2": "y"}, flags=[])
    assert out[0]["supported"] is True and out[0]["origins_independent"] is True


def test_failed_sample_raises(monkeypatch):
    monkeypatch.setenv("VERIFIER_JUDGE", "claude")
    monkeypatch.setenv("JUDGE_VOTES", "3")
    import auditor.judge as J
    def boom(*a, **k):
        raise ValueError("api died")
    monkeypatch.setattr(J, "_judge_once", boom)
    import pytest
    with pytest.raises(ValueError):
        J.judge_claims([_claims()[0]], {"a.com/1": "x", "b.org/2": "y"}, flags=[])
