"""Plain-file storage. Everything the agent knows about you is a readable file.

Layout of the home directory (default ~/.futureyou, mode 700):

    entries.jsonl   one line per daily sentence   {"date", "text", "mood"}
    actions.jsonl   the "one thing" record         {"for_date", "set_on", "action", "goal", "result"}
    profile.json    {"name", "age", "created"}
    self.md         who you're becoming (persona seed)
    goals.md        WOOP goals
    memory.md       dated facts the agent chose to keep
    letters/  book/  reviews/

Writes are atomic (temp file + rename) and confined to the home directory.
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path


class StorageError(Exception):
    pass


class Store:
    DIRS = ("letters", "book", "reviews")

    def __init__(self, home: Path):
        self.home = Path(home).expanduser().resolve()

    def init(self) -> None:
        self.home.mkdir(parents=True, exist_ok=True)
        os.chmod(self.home, 0o700)
        for d in self.DIRS:
            (self.home / d).mkdir(exist_ok=True)

    def exists(self) -> bool:
        return self.home.is_dir()

    # -- paths -------------------------------------------------------------

    def path(self, *parts: str) -> Path:
        """Resolve a path inside home; refuse anything that escapes it."""
        p = self.home.joinpath(*parts).resolve()
        if p != self.home and self.home not in p.parents:
            raise StorageError(f"refusing to touch a path outside {self.home}: {p}")
        return p

    # -- text files ----------------------------------------------------------

    def read_text(self, *parts: str, default: str = "") -> str:
        p = self.path(*parts)
        return p.read_text(encoding="utf-8") if p.exists() else default

    def write_text(self, *parts: str, text: str) -> None:
        p = self.path(*parts)
        p.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=p.parent, prefix=".tmp-", suffix=p.suffix)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(text)
            os.replace(tmp, p)
        except BaseException:
            if os.path.exists(tmp):
                os.unlink(tmp)
            raise

    def list_dir(self, d: str) -> list[str]:
        p = self.path(d)
        return sorted(x.name for x in p.iterdir() if x.is_file()) if p.exists() else []

    # -- json / jsonl --------------------------------------------------------

    def read_json(self, *parts: str, default=None):
        raw = self.read_text(*parts)
        return json.loads(raw) if raw.strip() else default

    def write_json(self, *parts: str, data) -> None:
        self.write_text(*parts, text=json.dumps(data, indent=2, ensure_ascii=False) + "\n")

    def append_jsonl(self, name: str, record: dict) -> None:
        p = self.path(name)
        p.parent.mkdir(parents=True, exist_ok=True)
        with p.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    def read_jsonl(self, name: str) -> list[dict]:
        p = self.path(name)
        if not p.exists():
            return []
        out = []
        for line in p.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                out.append(json.loads(line))
        return out

    def write_jsonl(self, name: str, records: list[dict]) -> None:
        text = "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in records)
        self.write_text(name, text=text)
