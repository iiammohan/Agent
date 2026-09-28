"""Letter exchange: you write to Future You, Future You writes back.
Both letters are saved under letters/."""

from __future__ import annotations

from datetime import date

from futureyou import config, context, safety, tools
from futureyou.loop import run_agent


def read_multiline(ask, say) -> str:
    say("Write your letter. Finish with an empty line.")
    lines = []
    while True:
        try:
            line = ask("")
        except EOFError:
            break
        if not line.strip():
            break
        lines.append(line)
    return "\n".join(lines).strip()


def run(store, client, *, text: str | None = None, ask=input, say=print, trace=None,
        today: date | None = None) -> str | None:
    today = today or date.today()
    letter = text if text is not None else read_multiline(ask, say)
    if not letter:
        say("No letter, nothing saved.")
        return None
    stamp = today.isoformat()
    store.write_text("letters", f"{stamp}-to-future.md", text=letter + "\n")
    if safety.is_crisis(letter):
        say(safety.MESSAGE)
        return None

    user = f"{context.data_blocks(store, today)}\n\n<letter>\n{letter}\n</letter>"
    reply, _ = run_agent(
        client, system=context.system_blocks(store, "letter", today),
        messages=[{"role": "user", "content": user}], tools=tools.build_tools(store, "letter"),
        effort=config.EFFORT["letter"], max_tokens=config.MAX_TOKENS["letter"], trace=trace,
    )
    store.write_text("letters", f"{stamp}-from-future.md", text=reply + "\n")
    say("")
    say(reply)
    say(f"\nSaved to letters/{stamp}-from-future.md")
    return reply
