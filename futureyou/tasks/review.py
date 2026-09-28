"""Monthly review: numbers computed by code, one paragraph by Future You."""

from __future__ import annotations

from datetime import date

from futureyou import config, context, tools
from futureyou.loop import run_agent


def run(store, client, *, say=print, trace=None, today: date | None = None) -> str:
    today = today or date.today()
    stats = tools.format_stats(tools.compute_stats(store, today))
    history = tools.get_one_thing_history_tool(store, 30)
    user = (f"{context.data_blocks(store, today)}\n\n<stats>\n{stats}\n</stats>\n\n"
            f"<one_thing_record>\n{history}\n</one_thing_record>")
    paragraph, _ = run_agent(
        client, system=context.system_blocks(store, "review", today),
        messages=[{"role": "user", "content": user}], tools=tools.build_tools(store, "review"),
        effort=config.EFFORT["review"], max_tokens=config.MAX_TOKENS["review"], trace=trace,
    )
    text = f"# Review, {today.strftime('%B %Y')}\n\n{stats}\n\n{paragraph.strip()}\n"
    fname = f"{today.isoformat()}-review.md"
    store.write_text("reviews", fname, text=text)
    say(text)
    say(f"Saved to reviews/{fname}")
    return text
