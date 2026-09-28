"""Ask Future You a question."""

from __future__ import annotations

from datetime import date

from futureyou import config, context, safety, tools
from futureyou.loop import run_agent


def run(store, client, question: str, *, say=print, trace=None, today: date | None = None) -> str | None:
    if safety.is_crisis(question):
        say(safety.MESSAGE)
        return None
    user = f"{context.data_blocks(store, today)}\n\n<question>\n{question.strip()}\n</question>"
    reply, _ = run_agent(
        client, system=context.system_blocks(store, "ask", today),
        messages=[{"role": "user", "content": user}], tools=tools.build_tools(store, "ask"),
        effort=config.EFFORT["ask"], max_tokens=config.MAX_TOKENS["ask"], trace=trace,
    )
    say(reply)
    return reply
