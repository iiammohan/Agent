from datetime import date, timedelta

from futureyou import tools
from helpers import fresh_store, seed_entries

TODAY = date(2026, 9, 28)


def test_entries_recent_and_search():
    with fresh_store() as s:
        seed_entries(s, 40, end=TODAY)
        tools.add_entry(s, "the sky is clear today", 4, TODAY)
        recent = tools.recent_entries(s, 30, TODAY)
        assert len(recent) == 32  # inclusive 30-day window = 31 seeded days, plus today's extra
        out = tools.search_entries_tool(s, "SKY")
        assert "1 match" in out and "sky is clear" in out
        assert "no entries mention" in tools.search_entries_tool(s, "zebra")


def test_goals_roundtrip_and_update():
    with fresh_store() as s:
        msg = tools.update_goal_tool(s, "guitar", wish="play weekly", obstacle="phone", plan="if after dinner, then guitar first")
        assert "created" in msg
        assert "no changes" in tools.update_goal_tool(s, "Guitar")  # case-insensitive match, nothing changed
        tools.update_goal_tool(s, "guitar", log_obstacle="scrolled instead")
        gs = tools.goals(s)
        assert len(gs) == 1
        assert gs[0]["plan"].startswith("if after dinner")
        assert len(gs[0]["log"]) == 1 and "scrolled" in gs[0]["log"][0]
        text = tools.get_goals_tool(s)
        assert "obstacle hits: 1" in text


def test_remember_caps_lines():
    with fresh_store() as s:
        from futureyou import config
        for i in range(config.MEMORY_MAX_LINES + 5):
            tools.remember_tool(s, f"fact {i}", "pattern")
        lines = [l for l in s.read_text("memory.md").splitlines() if l.strip()]
        assert len(lines) == config.MEMORY_MAX_LINES
        assert lines[-1].endswith("fact %d" % (config.MEMORY_MAX_LINES + 4))
        assert "fact 0" not in s.read_text("memory.md")


def test_one_thing_set_checkin_history():
    with fresh_store() as s:
        d0 = TODAY - timedelta(days=3)
        tools.set_one_thing_tool(s, "open the case", "guitar", today=d0)
        tools.set_one_thing_tool(s, "open the case again", "guitar", today=d0)  # same-day overwrite
        assert len(tools.actions(s)) == 1
        assert tools.actions(s)[0]["action"] == "open the case again"
        # not due before its day
        assert tools.pending_checkin(s, today=d0) is None
        pending = tools.pending_checkin(s, today=d0 + timedelta(days=1))
        assert pending and pending["action"] == "open the case again"
        tools.record_checkin(s, pending["for_date"], "done")
        assert tools.pending_checkin(s, today=TODAY) is None
        tools.set_one_thing_tool(s, "walk", None, today=TODAY - timedelta(days=1))
        tools.record_checkin(s, TODAY.isoformat(), "not")
        hist = tools.get_one_thing_history_tool(s, 14)
        assert "done 1/2 asked" in hist and "done-streak 0" in hist


def test_unasked_older_actions_become_unknown():
    with fresh_store() as s:
        tools.set_one_thing_tool(s, "a", today=TODAY - timedelta(days=5))
        tools.set_one_thing_tool(s, "b", today=TODAY - timedelta(days=1))
        pending = tools.pending_checkin(s, today=TODAY)
        assert pending["action"] == "b"  # most recent due one is asked
        tools.record_checkin(s, pending["for_date"], "partly")
        results = {r["action"]: r["result"] for r in tools.actions(s)}
        assert results == {"a": "unknown", "b": "partly"}


def test_stats_streak_and_due_flags():
    with fresh_store() as s:
        seed_entries(s, 10, end=TODAY)
        st = tools.compute_stats(s, TODAY)
        assert st["entries"] == 10 and st["streak"] == 10
        assert not st["chapter_due"] and not st["review_due"] and not st["letter_due"]
    with fresh_store() as s:
        seed_entries(s, 100, end=TODAY)
        st = tools.compute_stats(s, TODAY)
        assert st["chapter_due"] and st["review_due"] and st["letter_due"]
        s.write_text("book", "chapter-01.md", text="x")
        s.write_text("reviews", f"{TODAY.isoformat()}-review.md", text="x")
        s.write_text("letters", f"{TODAY.isoformat()}-from-future.md", text="x")
        st = tools.compute_stats(s, TODAY)
        assert not st["chapter_due"] and not st["review_due"] and not st["letter_due"]


def test_streak_breaks_on_gap():
    with fresh_store() as s:
        seed_entries(s, 6, end=TODAY, gap_every=4)
        st = tools.compute_stats(s, TODAY)
        assert 0 < st["streak"] < 6


def test_build_tools_onboard_only_has_write_self():
    with fresh_store() as s:
        names = {t.name for t in tools.build_tools(s, "today")}
        assert "write_self" not in names and "set_one_thing" in names
        assert "write_self" in {t.name for t in tools.build_tools(s, "onboard")}
        for t in tools.build_tools(s, "onboard"):
            spec = t.spec()
            assert spec["input_schema"]["type"] == "object"
            assert spec["input_schema"]["additionalProperties"] is False


def test_write_self_writes_profile():
    with fresh_store() as s:
        tools.write_self_tool(s, "Mo", 30, "walks daily", "scrolls", "health", "dry")
        assert "## Hoped-for self" in s.read_text("self.md")
        assert s.read_json("profile.json")["name"] == "Mo"
