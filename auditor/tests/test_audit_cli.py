import json, subprocess, sys, os

BRIEF_BAD = """# B
## Key claims log
| Claim | Status | Source(s) |
|---|---|---|
| laundered | verified | [a](https://never.example.com/x) |
"""

BRIEF_OK = """# B
## Key claims log
| Claim | Status | Source(s) |
|---|---|---|
| clean | verified | [a](https://read.example.com/p), [b](https://other.example.org/q) |
"""

TRANSCRIPT = [
    {"type": "assistant", "message": {"content": [
        {"type": "tool_use", "id": "t1", "name": "WebFetch",
         "input": {"url": "https://read.example.com/p"}}]}},
    {"type": "user", "message": {"content": [
        {"type": "tool_result", "tool_use_id": "t1", "content": "evidence"}]}},
    {"type": "assistant", "message": {"content": [
        {"type": "tool_use", "id": "t2", "name": "WebFetch",
         "input": {"url": "https://other.example.org/q"}}]}},
    {"type": "user", "message": {"content": [
        {"type": "tool_result", "tool_use_id": "t2", "content": "evidence"}]}},
]


def _run(tmp_path, brief_text):
    b = tmp_path / "b.md"; b.write_text(brief_text)
    t = tmp_path / "t.jsonl"
    t.write_text("\n".join(json.dumps(r) for r in TRANSCRIPT))
    env = dict(os.environ, VERIFIER_JUDGE="stub:pass",
               PYTHONPATH=os.getcwd())
    return subprocess.run(
        [sys.executable, "-m", "auditor.audit", "--brief", str(b),
         "--transcript", str(t), "--json"],
        capture_output=True, text=True, env=env)


def test_clean_brief_exits_0_with_json(tmp_path):
    p = _run(tmp_path, BRIEF_OK)
    assert p.returncode == 0, p.stderr
    out = json.loads(p.stdout)
    assert out["verdict"] == "clean"
    assert out["claims"][0]["status_earned"] == "verified"


def test_laundered_brief_exits_1_and_names_d1(tmp_path):
    p = _run(tmp_path, BRIEF_BAD)
    assert p.returncode == 1
    out = json.loads(p.stdout)
    assert out["verdict"] == "findings"
    assert any(f["check"] == "D1" for f in out["findings"])
    assert out["claims"][0]["status_earned"] == "unsupported (cited-but-unread)"


def test_missing_transcript_exits_3(tmp_path):
    b = tmp_path / "b.md"; b.write_text(BRIEF_OK)
    env = dict(os.environ, VERIFIER_JUDGE="stub:pass", PYTHONPATH=os.getcwd())
    p = subprocess.run([sys.executable, "-m", "auditor.audit", "--brief", str(b),
                        "--transcript", "/nope.jsonl", "--json"],
                       capture_output=True, text=True, env=env)
    assert p.returncode == 3


def test_markdown_output_renders(tmp_path):
    b = tmp_path / "b.md"; b.write_text(BRIEF_OK)
    t = tmp_path / "t.jsonl"
    t.write_text("\n".join(json.dumps(r) for r in TRANSCRIPT))
    env = dict(os.environ, VERIFIER_JUDGE="stub:pass", PYTHONPATH=os.getcwd())
    p = subprocess.run([sys.executable, "-m", "auditor.audit", "--brief", str(b),
                        "--transcript", str(t)],
                       capture_output=True, text=True, env=env)
    assert p.returncode == 0, p.stdout + p.stderr
    assert "| Claim |" in p.stdout
    assert "Audit: CLEAN" in p.stdout
