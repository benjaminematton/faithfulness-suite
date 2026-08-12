#!/usr/bin/env python3
"""Per-trial telemetry for a harbor job: tokens, cost, compliance, audit findings.

Answers "what did this trial actually consume and produce" from the artifacts alone, so
the run sheet's per-run record (docs/plans/RUN-live-web-gate.md section 3) is mechanical
instead of hand-collected. Stdlib only.

    python3 tools/analyze_run.py jobs/2026-08-12__09-23-46          # one job
    python3 tools/analyze_run.py jobs/*/ --tsv                      # ledger rows
    python3 tools/analyze_run.py jobs/<job> --json                  # machine readable

Cost is COMPUTED from the transcript's own usage records at published list prices, not
read from harbor. It is what the same tokens WOULD cost on the API — useful even when the
run was billed to a subscription, which is the point when deciding between the two.
Prices: platform.claude.com/docs/en/about-claude/pricing (checked 2026-08-12), $/Mtok.
"""

import argparse
import collections
import glob
import json
import os
import pathlib
import sys

PRICES = {  # model substring -> (input, output, cache_write_5m, cache_read)
    "opus-5":     (5.0, 25.0, 6.25, 0.50),
    "opus-4-8":   (5.0, 25.0, 6.25, 0.50),
    "opus-4":     (5.0, 25.0, 6.25, 0.50),
    "fable-5":    (10.0, 50.0, 12.50, 1.00),
    "mythos-5":   (10.0, 50.0, 12.50, 1.00),
    "sonnet-5":   (2.0, 10.0, 2.50, 0.20),
    "sonnet-4-6": (3.0, 15.0, 3.75, 0.30),
    "sonnet-4":   (3.0, 15.0, 3.75, 0.30),
    "haiku-4-5":  (1.0, 5.0, 1.25, 0.10),
}
UNKNOWN_PRICE = (5.0, 25.0, 6.25, 0.50)  # assume Opus-tier rather than undercount

FIELDS = ("input_tokens", "output_tokens",
          "cache_creation_input_tokens", "cache_read_input_tokens")


def price_for(model):
    m = (model or "").replace(".", "-").lower()
    for key, p in PRICES.items():
        if key in m:
            return p, True
    return UNKNOWN_PRICE, False


def read_json(p, default=None):
    try:
        return json.loads(pathlib.Path(p).read_text())
    except Exception:
        return default


def scan_transcript(path):
    """Token totals, per-model split, and tool-call counts from a session jsonl."""
    tot = collections.Counter()
    by_model = collections.defaultdict(collections.Counter)
    tools = collections.Counter()
    calls = 0
    for line in open(path, errors="replace"):
        try:
            rec = json.loads(line)
        except Exception:
            continue
        msg = rec.get("message") or {}
        usage = msg.get("usage") or {}
        if usage:
            calls += 1
            model = msg.get("model") or "unknown"
            for f in FIELDS:
                v = usage.get(f) or 0
                tot[f] += v
                by_model[model][f] += v
        content = msg.get("content")
        if isinstance(content, list):
            for c in content:
                if isinstance(c, dict) and c.get("type") == "tool_use":
                    tools[c.get("name") or "?"] += 1
    return tot, by_model, tools, calls


def cost_of(counter, model):
    (pi, po, pw, pr), known = price_for(model)
    c = (counter["input_tokens"] * pi
         + counter["output_tokens"] * po
         + counter["cache_creation_input_tokens"] * pw
         + counter["cache_read_input_tokens"] * pr) / 1e6
    return c, known


def analyze_trial(trial_dir):
    d = pathlib.Path(trial_dir)
    out = {"trial": d.name}

    reward = None
    rp = d / "verifier" / "reward.txt"
    if rp.exists():
        try:
            reward = float(rp.read_text().strip())
        except Exception:
            pass
    if reward is None:
        cr = read_json(d / "artifacts" / "check-result.json") or {}
        reward = cr.get("reward")
    out["reward"] = reward

    sessions = sorted(glob.glob(str(d / "agent" / "sessions" / "**" / "*.jsonl"),
                                recursive=True), key=os.path.getsize, reverse=True)
    tot, by_model, tools, calls = (collections.Counter(), {}, collections.Counter(), 0)
    if sessions:
        tot, by_model, tools, calls = scan_transcript(sessions[0])
    out["transcript"] = sessions[0] if sessions else None
    out["api_calls"] = calls
    out["tokens"] = dict(tot)
    out["models"] = sorted(by_model)
    out["searches"] = tools.get("WebSearch", 0)
    out["fetches"] = tools.get("WebFetch", 0)
    out["search_fetch_ratio"] = (round(tools["WebSearch"] / tools["WebFetch"], 2)
                                 if tools.get("WebFetch") else None)

    total, all_known = 0.0, True
    for model, c in by_model.items():
        v, known = cost_of(c, model)
        total += v
        all_known &= known
    out["cost_usd_listprice"] = round(total, 2)
    out["price_known"] = all_known

    comp = read_json(d / "verifier" / "compliance.json")
    if comp is None:
        hits = glob.glob(str(d / "**" / "compliance.json"), recursive=True)
        comp = read_json(hits[0]) if hits else None
    out["compliance"] = comp

    audit = read_json(d / "verifier" / "audit.json")
    if audit is None:
        hits = glob.glob(str(d / "**" / "audit.json"), recursive=True)
        audit = read_json(hits[0]) if hits else None
    if audit:
        claims = audit.get("claims", [])
        out["n_claims"] = len(claims)
        out["n_verified_claimed"] = sum(
            1 for c in claims if c.get("status_claimed") == "verified")
        out["n_verified_earned"] = sum(
            1 for c in claims if c.get("status_earned") == "verified")
        out["findings"] = collections.Counter(
            f.get("check") for f in audit.get("findings", []))
        out["audit_ratio"] = (audit.get("stats") or {}).get("search_fetch_ratio")
    return out


def analyze_job(job_dir):
    d = pathlib.Path(job_dir)
    trials = [p for p in sorted(d.iterdir())
              if p.is_dir() and (p / "agent").exists()]
    return {"job": d.name, "trials": [analyze_trial(t) for t in trials]}


def fmt(n):
    return f"{n:,}"


def print_human(job):
    print(f"# {job['job']}")
    for t in job["trials"]:
        tk = t["tokens"]
        print(f"\n  {t['trial']}   reward={t['reward']}")
        print(f"    models          {', '.join(t['models']) or '—'}")
        print(f"    api calls       {t['api_calls']}")
        print(f"    input           {fmt(tk.get('input_tokens', 0)):>16}")
        print(f"    output          {fmt(tk.get('output_tokens', 0)):>16}")
        print(f"    cache write     {fmt(tk.get('cache_creation_input_tokens', 0)):>16}")
        print(f"    cache read      {fmt(tk.get('cache_read_input_tokens', 0)):>16}")
        star = "" if t["price_known"] else "  (unknown model — priced at Opus tier)"
        print(f"    cost @ list     ${t['cost_usd_listprice']:>15,.2f}{star}")
        print(f"    searches/fetches {t['searches']}/{t['fetches']}"
              f"   ratio {t['search_fetch_ratio']}")
        if t.get("compliance"):
            c = t["compliance"]
            print(f"    compliance      log={c.get('claims_log_present')} "
                  f"gate_calls={c.get('gate_invocations')} "
                  f"unavailable={c.get('gate_unavailable')} "
                  f"verified_lines={c.get('brief_verified_lines')}")
        if "n_claims" in t:
            print(f"    audit           claims={t['n_claims']} "
                  f"verified claimed={t['n_verified_claimed']} "
                  f"earned={t['n_verified_earned']} "
                  f"findings={dict(t['findings'])}")


TSV_COLS = ["job", "trial", "reward", "cost_usd_listprice", "api_calls",
            "input_tokens", "output_tokens", "cache_creation_input_tokens",
            "cache_read_input_tokens", "searches", "fetches", "search_fetch_ratio",
            "claims_log_present", "gate_invocations", "gate_unavailable",
            "brief_verified_lines", "n_verified_claimed", "n_verified_earned"]


def tsv_rows(job, header=True):
    if header:
        print("\t".join(TSV_COLS))
    for t in job["trials"]:
        c = t.get("compliance") or {}
        row = {**t, **t["tokens"], **c, "job": job["job"]}
        print("\t".join(str(row.get(k, "")) for k in TSV_COLS))


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("jobs", nargs="+")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--tsv", action="store_true")
    args = ap.parse_args(argv)

    results = [analyze_job(j) for j in args.jobs if pathlib.Path(j).is_dir()]
    if not results:
        print("no job directories found", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(results, indent=1, default=str))
    elif args.tsv:
        for i, j in enumerate(results):
            tsv_rows(j, header=(i == 0))
    else:
        for j in results:
            print_human(j)
        grand = sum(t["cost_usd_listprice"] for j in results for t in j["trials"])
        n = sum(len(j["trials"]) for j in results)
        if n:
            print(f"\n{n} trial(s), ${grand:,.2f} at list price "
                  f"(mean ${grand/n:,.2f}/trial)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
