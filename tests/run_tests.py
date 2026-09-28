"""Minimal runner for environments without pytest: `python tests/run_tests.py`.
Finds tests/test_*.py, runs every `test_*` function, reports failures."""

from __future__ import annotations

import importlib
import sys
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))


def main() -> int:
    failed = 0
    total = 0
    for path in sorted((ROOT / "tests").glob("test_*.py")):
        mod = importlib.import_module(path.stem)
        for name in sorted(dir(mod)):
            if not name.startswith("test_"):
                continue
            fn = getattr(mod, name)
            if not callable(fn):
                continue
            total += 1
            try:
                fn()
                print(f"ok   {path.stem}.{name}")
            except Exception:  # noqa: BLE001
                failed += 1
                print(f"FAIL {path.stem}.{name}")
                traceback.print_exc()
    print(f"\n{total - failed} passed, {failed} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
