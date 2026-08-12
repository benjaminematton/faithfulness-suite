#!/usr/bin/env python3
"""Minimal stdlib test runner — no PyPI, no pytest.

STATUS.md records that there is no PyPI access from the device bridge or the cloud
container, so "the pytest half of every smoke test in this suite is unrunnable from a
Claude session." This closes that gap for the subset of tests that use only `tmp_path`
(which is all of auditor/tests today).

It is NOT a pytest replacement: any test needing a fixture it does not provide is reported
SKIPPED-UNSUPPORTED, never silently passed. Run pytest when you have it.

    python3 tools/run_tests_stdlib.py [auditor/tests] [-k substring]
"""

import argparse
import importlib.util
import inspect
import pathlib
import sys

# Invoked as `python3 tools/run_tests_stdlib.py`, sys.path[0] is tools/ — put the
# repo root first so test files can `from auditor.brief import ...` regardless of cwd.
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import tempfile
import traceback

SUPPORTED = {"tmp_path"}


def load_module(path: pathlib.Path):
    name = "t_" + path.stem
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("path", nargs="?", default="auditor/tests")
    ap.add_argument("-k", dest="filter", default=None)
    args = ap.parse_args(argv)

    root = pathlib.Path(args.path)
    files = sorted(root.glob("test_*.py")) if root.is_dir() else [root]
    passed = failed = skipped = 0
    failures = []

    for f in files:
        try:
            mod = load_module(f)
        except Exception:
            failed += 1
            failures.append((f"{f}::<import>", traceback.format_exc()))
            print(f"IMPORT-FAIL {f}")
            continue

        for name, fn in sorted(vars(mod).items()):
            if not name.startswith("test_") or not callable(fn):
                continue
            if args.filter and args.filter not in name:
                continue
            params = set(inspect.signature(fn).parameters)
            if not params <= SUPPORTED:
                skipped += 1
                print(f"SKIP-UNSUPPORTED {f.name}::{name} "
                      f"(needs {sorted(params - SUPPORTED)})")
                continue
            with tempfile.TemporaryDirectory() as td:
                kwargs = {"tmp_path": pathlib.Path(td)} if "tmp_path" in params else {}
                try:
                    fn(**kwargs)
                    passed += 1
                    print(f"PASS {f.name}::{name}")
                except ModuleNotFoundError as e:
                    # a test that imports pytest in its body (e.g. pytest.raises) is
                    # unsupported here, not failing. Report it, never pass it silently.
                    if e.name == "pytest":
                        skipped += 1
                        print(f"SKIP-UNSUPPORTED {f.name}::{name} (imports pytest in body)")
                        continue
                    failed += 1
                    failures.append((f"{f.name}::{name}", traceback.format_exc()))
                    print(f"FAIL {f.name}::{name}")
                except Exception:
                    failed += 1
                    failures.append((f"{f.name}::{name}", traceback.format_exc()))
                    print(f"FAIL {f.name}::{name}")

    for label, tb in failures:
        print(f"\n===== {label} =====\n{tb}")
    print(f"\n{passed} passed, {failed} failed, {skipped} skipped-unsupported")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
