"""The CLI in --mock mode, end to end, in a temp home."""

import contextlib
import io
import os
import tempfile

from futureyou import cli, config
from futureyou.storage import Store


@contextlib.contextmanager
def temp_home():
    with tempfile.TemporaryDirectory() as d:
        old = os.environ.get("FUTUREYOU_HOME")
        os.environ["FUTUREYOU_HOME"] = os.path.join(d, "home")
        try:
            yield Store(config.home())
        finally:
            if old is None:
                del os.environ["FUTUREYOU_HOME"]
            else:
                os.environ["FUTUREYOU_HOME"] = old


def run(argv):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = cli.main(argv)
    return code, out.getvalue(), err.getvalue()


def test_mock_today_and_stats_and_trace():
    with temp_home() as store:
        code, out, err = run(["--mock", "--trace", "today", "sky is clear", "--mood", "4"])
        assert code == 0, err
        assert "One thing:" in out
        assert "step 1: search_entries" in err and "set_one_thing" in err
        assert store.read_jsonl("entries.jsonl")[0]["text"] == "sky is clear"
        code, out, _ = run(["stats"])
        assert code == 0 and "entries: 1" in out


def test_mock_chapter_forced_and_export():
    with temp_home() as store:
        run(["--mock", "today", "one"])
        code, out, _ = run(["--mock", "chapter", "--force"])
        assert code == 0 and store.list_dir("book") == ["chapter-01.md"]
        with tempfile.TemporaryDirectory() as d:
            cwd = os.getcwd()
            os.chdir(d)
            try:
                code, out, _ = run(["export"])
            finally:
                os.chdir(cwd)
            assert code == 0 and "Exported to" in out
            assert any(n.startswith("futureyou-export-") for n in os.listdir(d))


def test_live_command_without_sdk_or_key_reports_one_line():
    # Without the SDK installed (or without a key), a live command fails with a single clear line.
    with temp_home():
        code, out, err = run(["today", "hello"])
        assert code == 1 and err.startswith("futureyou: ")
