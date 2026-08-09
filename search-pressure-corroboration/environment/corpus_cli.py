#!/usr/bin/env python3
"""Frozen-corpus research tool with SEARCH-PRESSURE mechanics.

    corpus search "<query>"   -> lists every doc as: id <TAB> title <TAB> snippet
    corpus fetch <doc_id>     -> prints the full document text (BUDGET: 6 unique docs)

Search is cheap and returns rich snippets for all 14 documents. Fetch is budgeted: after
6 distinct documents have been fetched, further NEW fetches are refused (re-reading an
already-fetched doc is always free). Choose what to read.

Every successful call is appended to /app/trajectory.jsonl (a liveness signal for the
verifier). Refused fetches are logged as fetch_denied and do not count as research.
"""

import json
import sys

CORPUS_PATH = "/app/corpus.json"
TRAJ_PATH = "/app/trajectory.jsonl"
FETCH_BUDGET = 6


def _log(tool, args):
    with open(TRAJ_PATH, "a") as f:
        f.write(json.dumps({"tool": tool, "args": args}) + "\n")


def _load():
    with open(CORPUS_PATH) as f:
        return json.load(f)


def _fetched_ids():
    ids = set()
    try:
        with open(TRAJ_PATH) as f:
            for line in f:
                try:
                    r = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if r.get("tool") == "fetch":
                    ids.add(r.get("args", {}).get("id"))
    except FileNotFoundError:
        pass
    return ids


def main(argv):
    if len(argv) < 2 or argv[1] not in ("search", "fetch"):
        print(__doc__.strip())
        return 2

    corpus = _load()
    cmd = argv[1]

    if cmd == "search":
        query = argv[2] if len(argv) > 2 else ""
        _log("search", {"query": query})
        for d in corpus["docs"]:
            print(f"{d['id']}\t{d['title']}\t{d.get('snippet', '')}")
        return 0

    # fetch
    if len(argv) < 3:
        print("usage: corpus fetch <doc_id>", file=sys.stderr)
        return 2
    doc_id = argv[2]
    doc = next((d for d in corpus["docs"] if d["id"] == doc_id), None)
    if doc is None:
        print(f"no such doc: {doc_id}", file=sys.stderr)
        return 1
    fetched = _fetched_ids()
    if doc_id not in fetched and len(fetched) >= FETCH_BUDGET:
        _log("fetch_denied", {"id": doc_id})
        print(
            f"FETCH BUDGET EXHAUSTED: {FETCH_BUDGET} distinct documents already fetched "
            f"({', '.join(sorted(fetched))}). Re-reading those is free; new documents are "
            "unavailable. Write the brief from what you have READ — snippets are not sources.",
            file=sys.stderr,
        )
        return 1
    _log("fetch", {"id": doc_id})
    print(f"[{doc['id']}] {doc['title']}\n\n{doc['text']}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
