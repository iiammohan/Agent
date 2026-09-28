"""Shared test helpers. Plain functions so the tests run under pytest or
under tests/run_tests.py with nothing installed."""

from __future__ import annotations

import contextlib
import tempfile
from datetime import date, timedelta
from pathlib import Path

from futureyou.storage import Store
from futureyou.tools import add_entry


@contextlib.contextmanager
def fresh_store():
    with tempfile.TemporaryDirectory() as d:
        s = Store(Path(d) / "home")
        s.init()
        yield s


def seed_entries(store: Store, n: int, end: date | None = None, gap_every: int = 0) -> list[dict]:
    """n entries ending today (or `end`), one per day, oldest first.
    gap_every>0 skips every k-th day to break streaks."""
    end = end or date.today()
    out = []
    day = end - timedelta(days=n - 1)
    i = 0
    while len(out) < n:
        i += 1
        if gap_every and i % gap_every == 0:
            day += timedelta(days=1)
            continue
        out.append(add_entry(store, f"entry {len(out) + 1} on {day.isoformat()}", None, day))
        day += timedelta(days=1)
    return out


def write_self(store: Store) -> None:
    store.write_text("self.md", text="# Mo, 30\n\n## Hoped-for self\n\nWalks every morning. Plays guitar on Tuesdays.\n")
    store.write_json("profile.json", data={"name": "Mo", "age": 30, "created": "2026-01-01"})
