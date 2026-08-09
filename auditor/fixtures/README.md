# Real regression fixtures (LOCAL-ONLY — personal transcripts, never committed)

Ground truth: docs/2026-08-09-mining-report.md.
- aug03 (accelerator cohort attribution): MUST exit 1 — D1 (verified claims cite
  journals.uchicago.edu + angelmatch.io, never fetched) and origin findings (gener8tor x2).
- aug08 (observability batch pipeline — the session's last brief): MUST exit 0, or findings limited to flags.

Run: python3 -m auditor.audit --brief auditor/fixtures/aug03-brief.md \
  --transcript auditor/fixtures/aug03-transcript.jsonl --votes 3 --json

sha256 (first 16) of local data files:
- aug03-brief.md: b4654dbd5478cc81
- aug03-transcript.jsonl: c34eab8b173d54b2
- aug08-brief.md: 56646484c99f4875
- aug08-transcript.jsonl: aea209a9e4f0ef22
