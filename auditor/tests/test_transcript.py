import json
from auditor.transcript import parse_transcript


def _fixture_lines():
    # assistant turn: one WebSearch and one WebFetch tool_use
    yield json.dumps({"type": "assistant", "message": {"content": [
        {"type": "tool_use", "id": "t1", "name": "WebSearch",
         "input": {"query": "python logging best practices"}},
    ]}})
    yield json.dumps({"type": "user", "message": {"content": [
        {"type": "tool_result", "tool_use_id": "t1",
         "content": "Links: [{\"title\":\"Logging HOWTO\",\"url\":\"https://docs.python.org/3/howto/logging.html\"}]"},
    ]}})
    yield json.dumps({"type": "assistant", "message": {"content": [
        {"type": "tool_use", "id": "t2", "name": "WebFetch",
         "input": {"url": "https://docs.python.org/3/howto/logging.html", "prompt": "x"}},
    ]}})
    yield json.dumps({"type": "user", "message": {"content": [
        {"type": "tool_result", "tool_use_id": "t2",
         "content": [{"type": "text", "text": "logger.exception logs at ERROR with traceback"}]},
    ]}})
    yield "not json"  # junk line must be ignored
    # a fetch that errored -> must NOT land in fetched
    yield json.dumps({"type": "assistant", "message": {"content": [
        {"type": "tool_use", "id": "t3", "name": "WebFetch",
         "input": {"url": "https://news.ycombinator.com/item?id=1", "prompt": "x"}},
    ]}})
    yield json.dumps({"type": "user", "message": {"content": [
        {"type": "tool_result", "tool_use_id": "t3", "is_error": True,
         "content": "429 client error"},
    ]}})


def test_parse_transcript_extracts_searches_fetches_and_stats(tmp_path):
    p = tmp_path / "s.jsonl"
    p.write_text("\n".join(_fixture_lines()))
    t = parse_transcript(str(p))
    assert t.searched == {"python logging best practices": 1}
    assert "docs.python.org/3/howto/logging.html" in t.fetched
    assert "traceback" in t.fetched["docs.python.org/3/howto/logging.html"]
    # errored fetch excluded from fetched, but recorded as an event
    assert "news.ycombinator.com/item?id=1" not in t.fetched
    assert t.stats["n_searches"] == 1
    assert t.stats["n_unique_fetches"] == 1
    assert t.stats["search_fetch_ratio"] == 1.0
    kinds = [e[0] for e in t.events]
    assert kinds == ["SEARCH", "FETCH", "FETCH_ERROR"]


def test_parse_transcript_missing_file_raises():
    import pytest
    with pytest.raises(FileNotFoundError):
        parse_transcript("/nope/never.jsonl")


def test_ratio_is_none_with_zero_fetches(tmp_path):
    p = tmp_path / "s.jsonl"
    p.write_text("")
    t = parse_transcript(str(p))
    assert t.stats["search_fetch_ratio"] is None
