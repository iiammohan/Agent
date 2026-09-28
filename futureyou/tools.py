"""The agent's hands. Every tool is a plain function over the Store, described
by a JSON schema the model sees. Adding a capability means adding a tool
here, never a longer prompt.

Tools return strings (the model reads them), keep results small, and never
raise past the loop: the loop turns exceptions into error results.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, timedelta

from futureyou import config
from futureyou.storage import Store


@dataclass
class Tool:
    name: str
    description: str
    input_schema: dict
    fn: Callable[..., str]

    def spec(self) -> dict:
        return {"name": self.name, "description": self.description, "input_schema": self.input_schema}


def _schema(props: dict | None = None, required: list[str] | None = None) -> dict:
    return {"type": "object", "properties": props or {}, "required": required or [], "additionalProperties": False}


# ---------------------------------------------------------------------------
# Entries
# ---------------------------------------------------------------------------

def entries(store: Store) -> list[dict]:
    return store.read_jsonl("entries.jsonl")


def add_entry(store: Store, text: str, mood: int | None = None, day: date | None = None) -> dict:
    rec = {"date": (day or date.today()).isoformat(), "text": text.strip(), "mood": mood}
    store.append_jsonl("entries.jsonl", rec)
    return rec


def format_entries(rows: list[dict]) -> str:
    if not rows:
        return "(no entries yet)"
    lines = []
    for r in rows:
        mood = f" [mood {r['mood']}]" if r.get("mood") else ""
        lines.append(f"{r['date']}{mood}: {r['text']}")
    return "\n".join(lines)


def recent_entries(store: Store, days: int = config.RECENT_ENTRY_DAYS, today: date | None = None) -> list[dict]:
    today = today or date.today()
    cutoff = (today - timedelta(days=days)).isoformat()
    return [r for r in entries(store) if r["date"] >= cutoff]


def read_entries_tool(store: Store, days: int = 30) -> str:
    return format_entries(recent_entries(store, int(days)))


def search_entries_tool(store: Store, query: str, limit: int = 10) -> str:
    q = query.lower().strip()
    hits = [r for r in entries(store) if q in r["text"].lower()]
    if not hits:
        return f"no entries mention '{query}'"
    hits = hits[-int(limit):]  # most recent matches
    return f"{len(hits)} match(es) for '{query}':\n" + format_entries(hits)


# ---------------------------------------------------------------------------
# Self and profile
# ---------------------------------------------------------------------------

def get_self_tool(store: Store) -> str:
    return store.read_text("self.md") or "(no self.md yet; run onboarding)"


def write_self_tool(store: Store, name: str, age: int, hoped_for_self: str, feared_self: str, values: str, voice: str) -> str:
    text = (
        f"# {name}, {age}\n\n"
        f"## Hoped-for self\n\n{hoped_for_self.strip()}\n\n"
        f"## Feared self\n\n{feared_self.strip()}\n\n"
        f"## Values\n\n{values.strip()}\n\n"
        f"## Voice\n\n{voice.strip()}\n"
    )
    store.write_text("self.md", text=text)
    profile = store.read_json("profile.json", default={}) or {}
    profile.update({"name": name, "age": int(age)})
    profile.setdefault("created", date.today().isoformat())
    store.write_json("profile.json", data=profile)
    return "self.md and profile written"


# ---------------------------------------------------------------------------
# Goals (WOOP), stored as goals.md
# ---------------------------------------------------------------------------

GOAL_FIELDS = ("Status", "Wish", "Outcome", "Obstacle", "Plan")


def parse_goals(text: str) -> list[dict]:
    goals: list[dict] = []
    cur: dict | None = None
    for line in text.splitlines():
        m = re.match(r"^##\s+(.+?)\s*$", line)
        if m:
            cur = {"name": m.group(1), "log": []}
            goals.append(cur)
            continue
        if cur is None:
            continue
        m = re.match(r"^-\s+(\w+):\s*(.*)$", line)
        if m and m.group(1) in GOAL_FIELDS:
            cur[m.group(1).lower()] = m.group(2).strip()
        elif re.match(r"^\s+-\s+\d{4}-\d{2}-\d{2}:", line):
            cur["log"].append(line.strip()[2:])
    return goals


def render_goals(goals: list[dict]) -> str:
    out = ["# Goals (WOOP)\n"]
    for g in goals:
        out.append(f"## {g['name']}")
        for f in GOAL_FIELDS:
            out.append(f"- {f}: {g.get(f.lower(), '')}")
        out.append("- Obstacle log:")
        for entry in g.get("log", []):
            out.append(f"  - {entry}")
        out.append("")
    return "\n".join(out)


def goals(store: Store) -> list[dict]:
    return parse_goals(store.read_text("goals.md"))


def get_goals_tool(store: Store) -> str:
    gs = goals(store)
    if not gs:
        return "(no goals yet)"
    lines = []
    for g in gs:
        lines.append(f"## {g['name']} [{g.get('status', 'active')}]")
        for f in ("wish", "outcome", "obstacle", "plan"):
            lines.append(f"  {f}: {g.get(f, '')}")
        if g["log"]:
            lines.append(f"  obstacle hits: {len(g['log'])}, last: {g['log'][-1]}")
    return "\n".join(lines)


def update_goal_tool(store: Store, name: str, wish: str | None = None, outcome: str | None = None,
                     obstacle: str | None = None, plan: str | None = None, status: str | None = None,
                     log_obstacle: str | None = None) -> str:
    gs = goals(store)
    g = next((x for x in gs if x["name"].lower() == name.strip().lower()), None)
    created = g is None
    if created:
        g = {"name": name.strip(), "status": "active", "log": []}
        gs.append(g)
    changed = []
    for key, val in (("wish", wish), ("outcome", outcome), ("obstacle", obstacle), ("plan", plan), ("status", status)):
        if val is not None and val != g.get(key):
            g[key] = val.strip()
            changed.append(key)
    if log_obstacle:
        g["log"].append(f"{date.today().isoformat()}: {log_obstacle.strip()}")
        changed.append("log")
    store.write_text("goals.md", text=render_goals(gs))
    verb = "created" if created else "updated"
    return f"goal '{g['name']}' {verb}" + (f" ({', '.join(changed)})" if changed else " (no changes)")


# ---------------------------------------------------------------------------
# Memory
# ---------------------------------------------------------------------------

def remember_tool(store: Store, fact: str, kind: str = "pattern") -> str:
    lines = [l for l in store.read_text("memory.md").splitlines() if l.strip()]
    lines.append(f"- {date.today().isoformat()} [{kind}] {fact.strip()}")
    note = ""
    if len(lines) > config.MEMORY_MAX_LINES:
        lines = lines[-config.MEMORY_MAX_LINES:]
        note = f" (memory at its {config.MEMORY_MAX_LINES}-line cap; oldest line dropped)"
    store.write_text("memory.md", text="\n".join(lines) + "\n")
    return "remembered" + note


# ---------------------------------------------------------------------------
# The one thing (actions.jsonl)
# ---------------------------------------------------------------------------

def actions(store: Store) -> list[dict]:
    return store.read_jsonl("actions.jsonl")


def set_one_thing_tool(store: Store, action: str, goal: str | None = None, today: date | None = None) -> str:
    today = today or date.today()
    for_date = (today + timedelta(days=1)).isoformat()
    rows = actions(store)
    rows = [r for r in rows if r["for_date"] != for_date]  # one per day; same-day overwrite
    rows.append({"for_date": for_date, "set_on": today.isoformat(), "action": action.strip(),
                 "goal": goal, "result": None})
    store.write_jsonl("actions.jsonl", rows)
    return f"one thing set for {for_date}"


def pending_checkin(store: Store, today: date | None = None) -> dict | None:
    """The most recent unanswered action whose day has arrived, if any."""
    today = (today or date.today()).isoformat()
    due = [r for r in actions(store) if r["result"] is None and r["for_date"] <= today]
    return due[-1] if due else None


def record_checkin(store: Store, for_date: str, result: str) -> None:
    rows = actions(store)
    for r in rows:
        if r["for_date"] == for_date:
            r["result"] = result
        elif r["result"] is None and r["for_date"] < for_date:
            r["result"] = "unknown"  # older ones that were never asked about
    store.write_jsonl("actions.jsonl", rows)


def one_thing_history(store: Store, days: int = 14, today: date | None = None) -> list[dict]:
    today = today or date.today()
    cutoff = (today - timedelta(days=int(days))).isoformat()
    return [r for r in actions(store) if r["for_date"] >= cutoff]


def get_one_thing_history_tool(store: Store, days: int = 14) -> str:
    rows = one_thing_history(store, days)
    if not rows:
        return "(no one-thing record yet)"
    lines = [f"{r['for_date']}: {r['action']} -> {r['result'] or 'not yet asked'}" for r in rows]
    done = sum(1 for r in rows if r["result"] == "done")
    asked = sum(1 for r in rows if r["result"] in ("done", "not", "partly"))
    streak = 0
    for r in reversed([r for r in rows if r["result"] in ("done", "not", "partly")]):
        if r["result"] == "done":
            streak += 1
        else:
            break
    lines.append(f"done {done}/{asked} asked; current done-streak {streak}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Stats (deterministic; no model involved)
# ---------------------------------------------------------------------------

def compute_stats(store: Store, today: date | None = None) -> dict:
    today = today or date.today()
    rows = entries(store)
    days = sorted({r["date"] for r in rows})
    streak = 0
    cursor = today
    dayset = set(days)
    if today.isoformat() not in dayset:
        cursor = today - timedelta(days=1)
    while cursor.isoformat() in dayset:
        streak += 1
        cursor -= timedelta(days=1)

    acts = [r for r in one_thing_history(store, 30, today) if r["result"] in ("done", "not", "partly")]
    done = sum(1 for r in acts if r["result"] == "done")

    chapters = len(store.list_dir("book"))
    letters = [n for n in store.list_dir("letters") if n.endswith("-from-future.md")]
    reviews = store.list_dir("reviews")

    def days_since(names: list[str]) -> int | None:
        if not names:
            return None
        last = names[-1][:10]
        try:
            return (today - date.fromisoformat(last)).days
        except ValueError:
            return None

    since_letter = days_since(letters)
    since_review = days_since(reviews)
    n = len(rows)
    return {
        "entries": n,
        "days_logged": len(days),
        "streak": streak,
        "one_thing_done": done,
        "one_thing_asked": len(acts),
        "goals": [(g["name"], g.get("status", "active"), len(g["log"])) for g in goals(store)],
        "chapters": chapters,
        "chapter_due": n // config.ENTRIES_PER_CHAPTER > chapters,
        "letter_due": n >= 30 and (since_letter is None or since_letter >= config.LETTER_EVERY_DAYS),
        "review_due": n >= 14 and (since_review is None or since_review >= config.REVIEW_EVERY_DAYS),
    }


def format_stats(s: dict) -> str:
    lines = [
        f"entries: {s['entries']} over {s['days_logged']} days; current streak {s['streak']} days",
        f"one thing (last 30 days): {s['one_thing_done']} done of {s['one_thing_asked']} asked",
        f"chapters written: {s['chapters']}" + (" (a new one is due)" if s["chapter_due"] else ""),
    ]
    if s["goals"]:
        lines.append("goals: " + "; ".join(f"{n} [{st}] {hits} obstacle hits" for n, st, hits in s["goals"]))
    if s["letter_due"]:
        lines.append("a letter exchange is due")
    if s["review_due"]:
        lines.append("a monthly review is due")
    return "\n".join(lines)


def stats_tool(store: Store) -> str:
    return format_stats(compute_stats(store))


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

def build_tools(store: Store, task: str) -> list[Tool]:
    """Tools for a task. Onboarding gets `write_self`; nothing else does."""
    s = store
    common = [
        Tool("read_entries", "Recent daily entries, oldest first, with dates.",
             _schema({"days": {"type": "integer", "description": "How many days back (default 30)."}}),
             lambda days=30: read_entries_tool(s, days)),
        Tool("search_entries", "Find past entries containing a word or phrase (case-insensitive). Use it when today touches something they've written about before.",
             _schema({"query": {"type": "string"}, "limit": {"type": "integer", "description": "Max matches, most recent first (default 10)."}}, ["query"]),
             lambda query, limit=10: search_entries_tool(s, query, limit)),
        Tool("get_self", "The hoped-for self, feared self, values and voice from onboarding.",
             _schema(), lambda: get_self_tool(s)),
        Tool("get_goals", "The WOOP goals (Wish, Outcome, Obstacle, Plan) with obstacle counts.",
             _schema(), lambda: get_goals_tool(s)),
        Tool("update_goal", "Create or update a WOOP goal. Only pass the fields that change. Use log_obstacle to record that the obstacle showed up today.",
             _schema({
                 "name": {"type": "string"}, "wish": {"type": "string"}, "outcome": {"type": "string"},
                 "obstacle": {"type": "string"}, "plan": {"type": "string", "description": "An if-then sentence."},
                 "status": {"type": "string", "enum": ["active", "paused", "done"]},
                 "log_obstacle": {"type": "string", "description": "What got in the way today, if it did."},
             }, ["name"]),
             lambda name, **kw: update_goal_tool(s, name, **kw)),
        Tool("remember", "Keep one dated fact for future conversations. Use sparingly: people, patterns, wins, struggles.",
             _schema({"fact": {"type": "string"}, "kind": {"type": "string", "enum": ["person", "pattern", "win", "struggle"]}}, ["fact"]),
             lambda fact, kind="pattern": remember_tool(s, fact, kind)),
        Tool("set_one_thing", "Log the one small thing for tomorrow. Call it once, right before you finish.",
             _schema({"action": {"type": "string", "description": "If-then phrasing, under 15 minutes."},
                      "goal": {"type": "string", "description": "Goal name it serves, if any."}}, ["action"]),
             lambda action, goal=None: set_one_thing_tool(s, action, goal)),
        Tool("get_one_thing_history", "Recent one-thing record with done/not/partly, to size the next one.",
             _schema({"days": {"type": "integer", "description": "Default 14."}}),
             lambda days=14: get_one_thing_history_tool(s, days)),
        Tool("stats", "Counts, streak, one-thing completion and what's due.", _schema(), lambda: stats_tool(s)),
    ]
    if task == "onboard":
        common.append(Tool(
            "write_self",
            "Write self.md and the profile at the end of onboarding. Be detailed and concrete; use their words.",
            _schema({
                "name": {"type": "string"}, "age": {"type": "integer"},
                "hoped_for_self": {"type": "string", "description": "Present tense, specific, 150-400 words."},
                "feared_self": {"type": "string", "description": "50-150 words."},
                "values": {"type": "string"}, "voice": {"type": "string", "description": "How they talk, 2-3 notes."},
            }, ["name", "age", "hoped_for_self", "feared_self", "values", "voice"]),
            lambda **kw: write_self_tool(s, **kw),
        ))
    return common
