"""End-to-end task runs against the mock client. Input and output are
captured through the ask/say hooks, so nothing touches the terminal."""

from datetime import date, timedelta

from futureyou import tools
from futureyou.llm import MockClient, text_response, tool_response
from futureyou.tasks import ask as ask_task
from futureyou.tasks import chapter, letter, onboard, review, today
from helpers import fresh_store, seed_entries, write_self

TODAY = date(2026, 9, 28)


class IO:
    def __init__(self, answers=()):
        self.answers = list(answers)
        self.out = []

    def ask(self, prompt=""):
        self.out.append(prompt)
        return self.answers.pop(0) if self.answers else ""

    def say(self, text=""):
        self.out.append(str(text))

    def text(self):
        return "\n".join(self.out)


def test_today_saves_entry_runs_agent_and_logs_one_thing():
    with fresh_store() as s:
        write_self(s)
        seed_entries(s, 5, end=TODAY - timedelta(days=1))
        client = MockClient([
            tool_response(("search_entries", {"query": "entry"}), ("set_one_thing", {"action": "walk", "goal": None})),
            text_response("I remember \"entry 3\".\n\nOne thing: walk."),
        ])
        io = IO()
        reply = today.run(s, client, text="sky is clear", mood=4, ask=io.ask, say=io.say, today=TODAY)
        assert "One thing: walk." in reply
        assert tools.entries(s)[-1] == {"date": TODAY.isoformat(), "text": "sky is clear", "mood": 4}
        assert tools.actions(s)[0]["for_date"] == (TODAY + timedelta(days=1)).isoformat()
        # the request carried self, goals (system) and the entry (user), tagged as data
        sys_text = "".join(b["text"] for b in client.calls[0]["system"])
        assert "<self>" in sys_text and "Hoped-for self" in sys_text and "<goals>" in sys_text
        assert client.calls[0]["system"][-1]["cache_control"] == {"type": "ephemeral"}
        user = client.calls[0]["messages"][0]["content"]
        assert "<today>\nsky is clear\n</today>" in user and "<recent_entries>" in user
        assert "<checkin>" not in user  # nothing was pending


def test_today_asks_about_pending_one_thing_first():
    with fresh_store() as s:
        write_self(s)
        tools.set_one_thing_tool(s, "open the case", today=TODAY - timedelta(days=1))
        client = MockClient([text_response("fine.\n\nOne thing: x")])
        io = IO(answers=["maybe", "partly"])
        today.run(s, client, text="ok day", ask=io.ask, say=io.say, today=TODAY)
        assert "Did you do it?" in io.text() and "Just yes, no or partly." in io.text()
        assert tools.actions(s)[0]["result"] == "partly"
        assert "<checkin>\nyesterday's one thing: partly" in client.calls[0]["messages"][0]["content"]


def test_today_skips_checkin_when_nothing_pending_and_stops_on_crisis():
    with fresh_store() as s:
        client = MockClient([text_response("should not be called")])
        io = IO()
        out = today.run(s, client, text="I want to kill myself", ask=io.ask, say=io.say, today=TODAY)
        assert out is None
        assert "Did you do it?" not in io.text()
        assert "findahelpline.com" in io.text()
        assert client.calls == []  # nothing sent to the model
        assert tools.entries(s)[-1]["text"] == "I want to kill myself"  # but the entry is kept


def test_today_empty_sentence_saves_nothing():
    with fresh_store() as s:
        client = MockClient([])
        io = IO(answers=["   "])
        assert today.run(s, client, ask=io.ask, say=io.say, today=TODAY) is None
        assert tools.entries(s) == []


def test_today_announces_due_chapter():
    with fresh_store() as s:
        write_self(s)
        seed_entries(s, 99, end=TODAY - timedelta(days=1))
        client = MockClient([text_response("ok\n\nOne thing: y")])
        io = IO()
        today.run(s, client, text="hundredth", ask=io.ask, say=io.say, today=TODAY)
        assert "futureyou chapter" in io.text()


def test_onboard_conversation_until_done_mark():
    with fresh_store() as s:
        client = MockClient([
            text_response("What's your name and age?"),
            text_response("Where are you in ten years?"),
            tool_response(("write_self", {"name": "Mo", "age": 30, "hoped_for_self": "h", "feared_self": "f", "values": "v", "voice": "w"}),
                          ("update_goal", {"name": "guitar", "wish": "play", "plan": "if x then y"})),
            text_response("Lovely. See you tomorrow.\n\nONBOARDING COMPLETE"),
        ])
        io = IO(answers=["Mo, 30", "playing guitar on a porch"])
        assert onboard.run(s, client, ask=io.ask, say=io.say, today=TODAY) is True
        assert "ONBOARDING COMPLETE" not in io.text() and "See you tomorrow" in io.text()
        assert s.read_json("profile.json")["name"] == "Mo"
        assert tools.goals(s)[0]["name"] == "guitar"
        # the conversation accumulated: user, assistant, user, assistant, user, assistant(tool), user(result), assistant
        roles = [m["role"] for m in client.calls[-1]["messages"]]
        assert roles[:3] == ["user", "assistant", "user"]


def test_onboard_refuses_overwrite_without_consent():
    with fresh_store() as s:
        write_self(s)
        client = MockClient([])
        io = IO(answers=["no"])
        assert onboard.run(s, client, ask=io.ask, say=io.say) is False
        assert client.calls == []


def test_ask_and_letter_save_and_reply():
    with fresh_store() as s:
        write_self(s)
        client = MockClient([text_response("You said \"walks every morning\".\n\nOne thing: z")])
        io = IO()
        assert "walks" in ask_task.run(s, client, "should I move?", say=io.say, today=TODAY)
        assert "<question>" in client.calls[0]["messages"][0]["content"]
        assert "ask_instructions" not in client.calls[0]["system"][0]["text"]  # rendered, not the filename
        assert "The younger you has a question" in client.calls[0]["system"][0]["text"]

        client = MockClient([text_response("Dear you,\n...\n\nOne thing: q")])
        io = IO()
        letter.run(s, client, text="Dear future me, I'm scared about the job.", say=io.say, today=TODAY)
        names = s.list_dir("letters")
        assert names == [f"{TODAY.isoformat()}-from-future.md", f"{TODAY.isoformat()}-to-future.md"]
        assert "scared about the job" in s.read_text("letters", names[1])


def test_letter_multiline_input_ends_on_blank_line():
    io = IO(answers=["line one", "line two", "", "ignored"])
    assert letter.read_multiline(io.ask, io.say) == "line one\nline two"


def test_chapter_needs_100_unless_forced_and_rotates_authors():
    with fresh_store() as s:
        write_self(s)
        seed_entries(s, 30, end=TODAY)
        io = IO()
        assert chapter.run(s, MockClient([]), say=io.say, today=TODAY) is None
        assert "needs 70 more" in io.text()
        client = MockClient([text_response("# Ch\n\ntext\n\n---\n\nafterword")])
        io = IO()
        chapter.run(s, client, force=True, say=io.say, today=TODAY)
        assert s.list_dir("book") == ["chapter-01.md"]
        body = s.read_text("book", "chapter-01.md")
        assert "Hemingway" in body and "<!-- chapter 1" in body
        assert client.calls[0]["stream"] is True and client.calls[0]["tools"] == []
        assert "Hemingway" in client.calls[0]["system"][0]["text"]
    with fresh_store() as s:
        seed_entries(s, 200, end=TODAY)
        s.write_text("book", "chapter-01.md", text="x")
        n, chunk, complete = chapter.next_chapter(s)
        assert n == 2 and complete and chunk[0]["text"].startswith("entry 101 ")
        client = MockClient([text_response("# Two")])
        chapter.run(s, client, say=IO().say, today=TODAY)
        assert "Austen" in client.calls[0]["system"][0]["text"]


def test_review_saves_stats_and_paragraph():
    with fresh_store() as s:
        write_self(s)
        seed_entries(s, 20, end=TODAY)
        client = MockClient([text_response("Mondays are flat.")])
        io = IO()
        text = review.run(s, client, say=io.say, today=TODAY)
        assert "entries: 20" in text and "Mondays are flat." in text
        assert s.list_dir("reviews") == [f"{TODAY.isoformat()}-review.md"]
        assert "<stats>" in client.calls[0]["messages"][0]["content"]
