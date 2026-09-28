"""The Historian: every 100 entries become a chapter, each in a different
author's voice. No tools here; the chapter is the model's text, streamed."""

from __future__ import annotations

from datetime import date

from futureyou import config, context, tools
from futureyou.loop import run_agent
from futureyou.prompts import AUTHORS, render


def next_chapter(store) -> tuple[int, list[dict], bool]:
    """(number, entries for it, complete?) for the next chapter to write."""
    rows = tools.entries(store)
    n = len(store.list_dir("book")) + 1
    size = config.ENTRIES_PER_CHAPTER
    chunk = rows[(n - 1) * size: n * size]
    return n, chunk, len(chunk) == size


def run(store, client, *, force: bool = False, say=print, trace=None, today: date | None = None) -> str | None:
    n, chunk, complete = next_chapter(store)
    if not chunk:
        say("No entries for a new chapter yet.")
        return None
    if not complete and not force:
        need = config.ENTRIES_PER_CHAPTER - len(chunk)
        say(f"Chapter {n} needs {need} more entries. Use --force to write it from what's there.")
        return None

    author, style = AUTHORS[(n - 1) % len(AUTHORS)]
    name = context.profile(store)["name"]
    system = [{"type": "text", "text": render("system_historian.md", number=n, author=author, style=style, name=name)}]
    user = "<entries>\n" + tools.format_entries(chunk) + "\n</entries>"
    say(f"Writing chapter {n} in the voice of {author}...")
    text, _ = run_agent(
        client, system=system, messages=[{"role": "user", "content": user}], tools=[],
        effort=config.EFFORT["chapter"], max_tokens=config.MAX_TOKENS["chapter"], stream=True, trace=trace,
    )
    span = f"{chunk[0]['date']} to {chunk[-1]['date']}"
    header = f"<!-- chapter {n} | {author} | entries {span} | written {(today or date.today()).isoformat()} -->\n\n"
    fname = f"chapter-{n:02d}.md"
    store.write_text("book", fname, text=header + text.strip() + "\n")
    say("")
    say(text)
    say(f"\nSaved to book/{fname}")
    return text
