#!/usr/bin/env python3
"""Frozen-corpus research tool. The agent researches ONLY through this CLI.

    corpus search "<query>"   -> lists every doc as: id <TAB> title
    corpus fetch <doc_id>     -> prints the full document text

Every call is appended to /app/trajectory.jsonl (a liveness signal for the verifier).
The corpus is small, so search returns all docs rather than ranking. Titles only, no
snippets: you must fetch a doc to read its claims and judge the source from its content.
"""

import json
import sys

CORPUS_PATH = "/app/corpus.json"
TRAJ_PATH = "/app/trajectory.jsonl"


def _log(tool, args):
    with open(TRAJ_PATH, "a") as f:
        f.write(json.dumps({"tool": tool, "args": args}) + "\n")


def _load():
    with open(CORPUS_PATH) as f:
        return json.load(f)


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
            print(f"{d['id']}\t{d['title']}")
        return 0

    # fetch
    if len(argv) < 3:
        print("usage: corpus fetch <doc_id>", file=sys.stderr)
        return 2
    doc_id = argv[2]
    _log("fetch", {"id": doc_id})
    for d in corpus["docs"]:
        if d["id"] == doc_id:
            print(f"[{d['id']}] {d['title']}\n\n{d['text']}")
            return 0
    print(f"no such doc: {doc_id}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
