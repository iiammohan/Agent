"""Onboarding: a Best Possible Self conversation that writes self.md,
profile.json and the first WOOP goals."""

from __future__ import annotations

from datetime import date

from futureyou import config, tools
from futureyou.loop import run_agent
from futureyou.prompts import render

DONE_MARK = "ONBOARDING COMPLETE"
MAX_TURNS = 16


def run(store, client, *, ask=input, say=print, trace=None, today: date | None = None) -> bool:
    today = today or date.today()
    if store.read_text("self.md").strip():
        answer = ask("You already have a self.md. Redo onboarding and overwrite it? (yes/no) ").strip().lower()
        if answer not in ("y", "yes"):
            say("Kept as is.")
            return False

    system = [{"type": "text", "text": render("system_onboarding.md", today=today.isoformat()),
               "cache_control": {"type": "ephemeral"}}]
    messages: list[dict] = [{"role": "user", "content": "Let's begin."}]
    say("This takes about fifteen minutes. Answer in your own words; there are no wrong answers.\n")

    for _ in range(MAX_TURNS):
        reply, messages = run_agent(
            client, system=system, messages=messages, tools=tools.build_tools(store, "onboard"),
            effort=config.EFFORT["onboard"], max_tokens=config.MAX_TOKENS["onboard"], trace=trace,
        )
        if DONE_MARK in reply:
            say(reply.replace(DONE_MARK, "").strip())
            say("\nDone. Tomorrow, run `futureyou` and write one sentence.")
            return True
        say(reply)
        answer = ask("> ").strip()
        if not answer:
            say("Stopping here. Run `futureyou onboard` again any time to finish.")
            return False
        messages.append({"role": "user", "content": answer})

    say("That's enough for today; run `futureyou onboard` again to finish.")
    return bool(store.read_text("self.md").strip())
