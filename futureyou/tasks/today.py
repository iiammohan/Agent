"""The daily run: check in on yesterday's one thing, take one sentence,
let Future You answer."""

from __future__ import annotations

from datetime import date

from futureyou import config, context, safety, tools
from futureyou.loop import run_agent

CHECKIN_ANSWERS = {"y": "done", "yes": "done", "d": "done", "done": "done",
                   "n": "not", "no": "not", "not": "not",
                   "p": "partly", "partly": "partly", "half": "partly"}


def checkin(store, ask, say, today: date | None = None) -> str | None:
    """Ask about the pending one thing, if any. Returns the recorded result."""
    pending = tools.pending_checkin(store, today)
    if not pending:
        return None
    say(f"Yesterday's one thing: {pending['action']}")
    while True:
        raw = ask("Did you do it? (yes / no / partly) ").strip().lower()
        result = CHECKIN_ANSWERS.get(raw)
        if result:
            break
        say("Just yes, no or partly.")
    tools.record_checkin(store, pending["for_date"], result)
    return result


def run(store, client, *, text: str | None = None, mood: int | None = None, ask=input, say=print,
        trace=None, today: date | None = None) -> str | None:
    today = today or date.today()
    result = checkin(store, ask, say, today)

    if text is None:
        text = ask("One sentence about today: ").strip()
    if not text:
        say("Nothing written, nothing saved.")
        return None
    tools.add_entry(store, text, mood, today)

    if safety.is_crisis(text):
        say(safety.MESSAGE)
        return None

    checkin_line = f"<checkin>\nyesterday's one thing: {result}\n</checkin>\n\n" if result else ""
    user = f"{context.data_blocks(store, today)}\n\n{checkin_line}<today>\n{text}\n</today>"
    reply, _ = run_agent(
        client,
        system=context.system_blocks(store, "today", today),
        messages=[{"role": "user", "content": user}],
        tools=tools.build_tools(store, "today"),
        effort=config.EFFORT["today"], max_tokens=config.MAX_TOKENS["today"], trace=trace,
    )
    say("")
    say(reply)
    _announce_due(store, say, today)
    return reply


def _announce_due(store, say, today: date) -> None:
    s = tools.compute_stats(store, today)
    notes = []
    if s["chapter_due"]:
        notes.append("A new chapter is due: run `futureyou chapter`.")
    if s["letter_due"]:
        notes.append("It's been a while since you wrote a letter: `futureyou letter`.")
    if s["review_due"]:
        notes.append("A monthly review is due: `futureyou review`.")
    if notes:
        say("")
        for n in notes:
            say(n)
