"""Parse a claude-code session jsonl into the auditor's Transcript.

Works on both Harbor job transcripts (agent/sessions/**/*.jsonl) and real config-dir
sessions (~/.claude-work/projects/**/*.jsonl) — same format. Ground rules: a URL is
"fetched" only if its WebFetch tool_result came back without is_error; search results are
recorded but are never evidence."""

import json
from dataclasses import dataclass, field

from .urlnorm import normalize_url


@dataclass
class Transcript:
    events: list = field(default_factory=list)      # (kind, payload) in order
    searched: dict = field(default_factory=dict)    # query -> count seen
    fetched: dict = field(default_factory=dict)     # normalized url -> content text

    @property
    def stats(self):
        n_s = sum(self.searched.values())
        n_f = len(self.fetched)
        return {
            "n_searches": n_s,
            "n_unique_fetches": n_f,
            "search_fetch_ratio": round(n_s / n_f, 2) if n_f else None,
        }


def _result_text(content):
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(
            c.get("text", "") for c in content if isinstance(c, dict) and c.get("type") == "text"
        )
    return ""


def parse_transcript(path: str) -> Transcript:
    pending = {}  # tool_use id -> (name, input)
    t = Transcript()
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            content = (rec.get("message") or {}).get("content")
            if not isinstance(content, list):
                continue
            for c in content:
                if not isinstance(c, dict):
                    continue
                if c.get("type") == "tool_use" and c.get("name") in ("WebSearch", "WebFetch"):
                    pending[c.get("id")] = (c["name"], c.get("input") or {})
                elif c.get("type") == "tool_result" and c.get("tool_use_id") in pending:
                    name, inp = pending.pop(c["tool_use_id"])
                    text = _result_text(c.get("content"))
                    if name == "WebSearch":
                        q = inp.get("query", "")
                        t.searched[q] = t.searched.get(q, 0) + 1
                        t.events.append(("SEARCH", {"query": q, "results": text}))
                    else:
                        url = normalize_url(inp.get("url", ""))
                        if c.get("is_error"):
                            t.events.append(("FETCH_ERROR", {"url": url, "error": text}))
                        else:
                            t.fetched[url] = text
                            t.events.append(("FETCH", {"url": url}))
    return t
