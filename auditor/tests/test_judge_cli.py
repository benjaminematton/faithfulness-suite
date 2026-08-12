"""VERIFIER_JUDGE=cli — subscription-billed judging via a headless `claude -p` call.

Uses a fake `claude` executable on PATH (stdlib-only, no monkeypatch, so the no-PyPI
runner can execute these). The fake asserts the two contract points that matter:
ANTHROPIC_API_KEY must NOT reach the child (the mode exists to prevent silent API
billing), and verdicts must cover every claim index parsed from the system prompt.
"""

import json
import os
import stat
import sys

from auditor.brief import Claim
from auditor.judge import judge_claims

FAKE = r'''#!/usr/bin/env python3
import json, os, re, sys
# Contract: cli mode must strip the API key so it can never bill the API.
if os.environ.get("ANTHROPIC_API_KEY"):
    sys.stderr.write("ANTHROPIC_API_KEY leaked into CLI child")
    sys.exit(97)
args = sys.argv[1:]
system = args[args.index("--system-prompt") + 1]
idx = sorted(set(int(m) for m in re.findall(r"CLAIM (\d+):", system)))
verdicts = [{"index": i, "supported": True, "origins_independent": None,
             "reason": "fake-cli"} for i in idx]
print(json.dumps({"result": "Sure! Here it is:\n" + json.dumps({"verdicts": verdicts})}))
'''


def _fake_cli(tmp_path, body=FAKE):
    exe = tmp_path / "claude"
    exe.write_text(body)
    exe.chmod(exe.stat().st_mode | stat.S_IEXEC)
    return str(exe)


def _with_env(tmp_path, fn, body=FAKE, **extra):
    saved = {k: os.environ.get(k)
             for k in ("VERIFIER_JUDGE", "CLAUDE_CLI", "ANTHROPIC_API_KEY",
                       "JUDGE_VOTES", *extra)}
    try:
        os.environ["VERIFIER_JUDGE"] = "cli"
        os.environ["CLAUDE_CLI"] = _fake_cli(tmp_path, body)
        os.environ["ANTHROPIC_API_KEY"] = "sk-must-not-leak"
        for k, v in extra.items():
            os.environ[k] = v
        return fn()
    finally:
        for k, v in saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


def _claims():
    return [Claim(text="c0", status="verified", cited_urls=["a.example.com/x"]),
            Claim(text="c1", status="verified", cited_urls=["b.example.org/y"])]


def test_cli_backend_judges_and_strips_api_key(tmp_path):
    out = _with_env(tmp_path, lambda: judge_claims(
        _claims(), {"a.example.com/x": "ev", "b.example.org/y": "ev"}, []))
    assert len(out) == 2
    assert all(v["supported"] for v in out)
    assert out[0]["reason"] == "fake-cli"


def test_cli_backend_votes(tmp_path):
    out = _with_env(tmp_path, lambda: judge_claims(
        _claims(), {"a.example.com/x": "ev", "b.example.org/y": "ev"}, []),
        JUDGE_VOTES="3")
    assert out[0]["reason"] == "fake-cli || fake-cli || fake-cli"


def test_cli_backend_raises_on_missing_index(tmp_path):
    """A judge that skips a claim is infra (raise -> exit 3), never a verdict."""
    bad = FAKE.replace('idx = sorted(set(int(m) for m in re.findall(r"CLAIM (\\d+):", system)))',
                       'idx = [0]')
    try:
        _with_env(tmp_path, lambda: judge_claims(
            _claims(), {"a.example.com/x": "ev", "b.example.org/y": "ev"}, []), body=bad)
    except ValueError as e:
        assert "wanted 0..1" in str(e)
    else:
        raise AssertionError("expected ValueError on missing index")


def test_cli_backend_raises_on_garbage(tmp_path):
    bad = FAKE.replace(
        'print(json.dumps({"result": "Sure! Here it is:\\n" + json.dumps({"verdicts": verdicts})}))',
        'print(json.dumps({"result": "no json here at all"}))')
    try:
        _with_env(tmp_path, lambda: judge_claims(
            _claims(), {"a.example.com/x": "ev", "b.example.org/y": "ev"}, []), body=bad)
    except ValueError as e:
        assert "no JSON object" in str(e)
    else:
        raise AssertionError("expected ValueError on garbage output")
