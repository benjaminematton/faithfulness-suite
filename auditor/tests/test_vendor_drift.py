"""The vendored core must match the manifest tools/sync_gate_core.sh recorded.

This is the guard for the ownership split: brief/checks/transcript/urlnorm/gate/gate_cli
are owned by become-expert-skill and copied here. A local edit to a vendored file would
silently fork the product's runtime from the thing this suite grades — which is exactly the
confound FINDINGS.md warns about elsewhere (a change landing in two places at once, so a
result mixes both effects).

If this fails: edit the file in become-expert-skill/scripts/auditor/, then re-run
    bash tools/sync_gate_core.sh [path-to-skill-checkout] && bash tools/sync_auditor.sh
"""

import hashlib
import pathlib
import re

AUDITOR = pathlib.Path(__file__).resolve().parents[1]
MANIFEST = AUDITOR / "CORE-VENDORED.md"
ROW = re.compile(r"^\|\s*([\w./-]+\.py)\s*\|\s*([0-9a-f]{64})\s*\|$", re.M)


def _manifest():
    assert MANIFEST.exists(), f"{MANIFEST.name} missing — run tools/sync_gate_core.sh"
    return dict((m.group(1), m.group(2)) for m in ROW.finditer(MANIFEST.read_text()))


def test_manifest_lists_the_whole_core():
    assert set(_manifest()) == {
        "urlnorm.py", "transcript.py", "brief.py", "checks.py", "gate.py", "gate_cli.py"}


def test_vendored_files_match_the_manifest():
    drifted = []
    for name, want in _manifest().items():
        p = AUDITOR / name
        assert p.exists(), f"vendored {name} missing — run tools/sync_gate_core.sh"
        got = hashlib.sha256(p.read_bytes()).hexdigest()
        if got != want:
            drifted.append(name)
    assert not drifted, (
        f"vendored core edited in place: {drifted}. Edit these in "
        f"become-expert-skill/scripts/auditor/, then re-run tools/sync_gate_core.sh.")


def test_eval_only_modules_are_not_vendored():
    """judge/report/audit are owned here and must never appear in the manifest."""
    assert not {"judge.py", "report.py", "audit.py"} & set(_manifest())
