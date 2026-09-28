"""Builds what the model sees: the system prefix (stable, cached) and the
per-run data blocks (recent, tagged as data)."""

from __future__ import annotations

from datetime import date

from futureyou import config, tools
from futureyou.prompts import render
from futureyou.storage import Store

FUTURE_AGE = 70


def profile(store: Store) -> dict:
    p = store.read_json("profile.json", default={}) or {}
    p.setdefault("name", "you")
    p.setdefault("age", 30)
    return p


def system_blocks(store: Store, task: str, today: date | None = None) -> list[dict]:
    """Persona + self + goals. `cache_control` on the last block caches the
    whole prefix; it only changes when self.md or goals.md change."""
    today = today or date.today()
    p = profile(store)
    persona = render(
        "system_future_you.md",
        name=p["name"], age=p["age"], future_age=max(FUTURE_AGE, int(p["age"]) + 20), today=today.isoformat(),
    )
    if task in ("letter", "ask", "review"):
        persona += "\n\n# This run\n\n" + render(f"{task}_instructions.md")
    return [
        {"type": "text", "text": persona},
        {"type": "text", "text": "<self>\n" + (store.read_text("self.md") or "(not yet written)") + "\n</self>"},
        {"type": "text", "text": "<goals>\n" + tools.get_goals_tool(store) + "\n</goals>",
         "cache_control": {"type": "ephemeral"}},
    ]


def data_blocks(store: Store, today: date | None = None) -> str:
    memory = store.read_text("memory.md").strip() or "(nothing kept yet)"
    recent = tools.format_entries(tools.recent_entries(store, config.RECENT_ENTRY_DAYS, today))
    return f"<memory>\n{memory}\n</memory>\n\n<recent_entries>\n{recent}\n</recent_entries>"
