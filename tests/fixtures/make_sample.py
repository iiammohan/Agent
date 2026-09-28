"""Generates tests/fixtures/sample_entries.jsonl: 120 days of plausible
one-sentence entries with a few planted patterns (Mondays are flat,
clear-sky days are good, the guitar comes and goes). Deterministic.

    python tests/fixtures/make_sample.py
"""

from __future__ import annotations

import json
import random
from datetime import date, timedelta
from pathlib import Path

START = date(2026, 5, 1)
DAYS = 120
OUT = Path(__file__).with_name("sample_entries.jsonl")

MONDAY = ["nothing much", "flat day, meetings", "tired before it started", "Monday again", "grey and slow"]
CLEAR = ["sky is clear today", "clear sky, walked to work", "sunny, felt light all day", "blue sky and a long walk"]
GREY = ["grey again, no energy", "rain, stayed in", "overcast, ate too much", "dull day, phone all evening"]
GUITAR = ["played guitar for ten minutes", "guitar came out after dinner", "learned the second verse", "skipped guitar, told myself tomorrow"]
PEOPLE = ["dinner with Priya, laughed a lot", "called amma, she sounded tired", "argued with Ravi about nothing", "Priya said I seem happier"]
WORK = ["shipped the thing, finally", "long day, nothing shipped", "good review at work", "the bug is still there"]
BODY = ["skipped the gym again", "gym, first time in two weeks", "slept 6 hours, felt it", "walked instead of driving"]


def main() -> None:
    rng = random.Random(7)
    rows = []
    for i in range(DAYS):
        d = START + timedelta(days=i)
        if d.weekday() == 0 and rng.random() < 0.7:
            text, mood = rng.choice(MONDAY), rng.choice([2, 2, 3])
        elif rng.random() < 0.25:
            text, mood = rng.choice(CLEAR), rng.choice([4, 4, 5])
        elif rng.random() < 0.25:
            text, mood = rng.choice(GREY), rng.choice([2, 3])
        else:
            pool = rng.choice([GUITAR, PEOPLE, WORK, BODY])
            text, mood = rng.choice(pool), rng.choice([3, 3, 4])
        if d.weekday() == 1 and rng.random() < 0.5:
            text = rng.choice(GUITAR)
        rows.append({"date": d.isoformat(), "text": text, "mood": mood})
    OUT.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
    print(f"wrote {len(rows)} entries to {OUT}")


if __name__ == "__main__":
    main()
