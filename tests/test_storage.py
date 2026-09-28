import os
import stat

from futureyou.storage import Store, StorageError
from helpers import fresh_store


def test_init_creates_private_home_and_dirs():
    with fresh_store() as s:
        mode = stat.S_IMODE(os.stat(s.home).st_mode)
        assert mode == 0o700
        for d in ("letters", "book", "reviews"):
            assert (s.home / d).is_dir()


def test_jsonl_roundtrip_and_rewrite():
    with fresh_store() as s:
        s.append_jsonl("x.jsonl", {"a": 1})
        s.append_jsonl("x.jsonl", {"a": 2, "t": "ünïcode"})
        assert s.read_jsonl("x.jsonl") == [{"a": 1}, {"a": 2, "t": "ünïcode"}]
        s.write_jsonl("x.jsonl", [{"a": 9}])
        assert s.read_jsonl("x.jsonl") == [{"a": 9}]
        assert s.read_jsonl("missing.jsonl") == []


def test_text_write_is_atomic_and_leaves_no_temp_files():
    with fresh_store() as s:
        s.write_text("book", "c.md", text="hello")
        s.write_text("book", "c.md", text="hello again")
        assert s.read_text("book", "c.md") == "hello again"
        assert not [p for p in (s.home / "book").iterdir() if p.name.startswith(".tmp-")]
        assert s.read_text("nope.md", default="d") == "d"


def test_paths_cannot_escape_home():
    with fresh_store() as s:
        for bad in (("..", "x"), ("/etc/passwd",), ("book", "..", "..", "x")):
            try:
                s.path(*bad)
            except StorageError:
                continue
            raise AssertionError(f"{bad} should have been refused")


def test_json_helpers():
    with fresh_store() as s:
        assert s.read_json("p.json", default={}) == {}
        s.write_json("p.json", data={"name": "Mo"})
        assert s.read_json("p.json")["name"] == "Mo"
