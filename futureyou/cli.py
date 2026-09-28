"""Command line entry point.

    futureyou                one sentence about today (the default)
    futureyou onboard        the fifteen-minute setup conversation
    futureyou ask "..."      ask Future You something
    futureyou letter         write a letter, get one back
    futureyou chapter        write the next biography chapter (every 100 entries)
    futureyou review         monthly review
    futureyou stats          numbers only, no model call
    futureyou export         zip your data
    futureyou delete-all     remove everything
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from futureyou import config, tools
from futureyou.llm import LLMError, get_client, text_response, tool_response
from futureyou.loop import AgentError
from futureyou.storage import Store


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="futureyou", description="One sentence a day, answered by the person you're becoming.")
    p.add_argument("--trace", action="store_true", help="show each tool call the agent makes")
    p.add_argument("--mock", action="store_true", help="use a scripted model (no API key needed)")
    p.add_argument("--provider", choices=["anthropic", "openrouter"], help="which API to call (default: from environment)")
    p.add_argument("--model", help="model id for the provider, e.g. claude-opus-5 or openai/gpt-5")
    sub = p.add_subparsers(dest="command")

    t = sub.add_parser("today", help="one sentence about today (default)")
    t.add_argument("text", nargs="?", help="the sentence; prompts if omitted")
    t.add_argument("--mood", type=int, choices=range(1, 6), help="optional 1-5")

    sub.add_parser("onboard", help="set up Future You (about fifteen minutes)")
    sub.add_parser("refresh-self", help="redo the onboarding conversation")

    a = sub.add_parser("ask", help="ask Future You a question")
    a.add_argument("question")

    l = sub.add_parser("letter", help="write a letter to Future You and get one back")
    l.add_argument("--file", help="read the letter from a file instead of typing it")

    c = sub.add_parser("chapter", help="write the next chapter of the book")
    c.add_argument("--force", action="store_true", help="write it even with fewer than 100 entries")

    sub.add_parser("review", help="monthly review")
    sub.add_parser("stats", help="numbers only")
    sub.add_parser("export", help="zip everything in your data directory")
    sub.add_parser("delete-all", help="delete all your data")
    return p


def _mock_responses(command: str) -> list[dict]:
    """A believable scripted run, so the product can be seen without a key."""
    if command == "chapter":
        return [text_response("# A Small Clear Sky\n\nThe days were short and the sentences were shorter.\n\n---\n\nYou wrote every day. Most of it was weather. The weather was you.")]
    if command == "review":
        return [text_response("Reading the month back, the flat days cluster on Mondays; you wrote 'nothing much' three Mondays running. When Monday evening comes, put the shoes by the door before you sit down.")]
    if command == "onboard":
        return [text_response("What's your first name, and how old are you?"),
                tool_response(("write_self", {"name": "Mo", "age": 30, "hoped_for_self": "Walks every morning. Plays guitar on Tuesdays.", "feared_self": "Always tired, always scrolling.", "values": "health, making things", "voice": "short, dry, warm"}),
                              ("update_goal", {"name": "guitar", "wish": "play guitar weekly", "outcome": "one song by December", "obstacle": "evenings vanish into the phone", "plan": "if it's after dinner on Tuesday, then the guitar comes out before the phone"})),
                text_response("That's enough to begin. I'll be here tomorrow.\n\nONBOARDING COMPLETE")]
    return [
        tool_response(("search_entries", {"query": "sky"}), ("get_one_thing_history", {"days": 14})),
        tool_response(("set_one_thing", {"action": "when you finish dinner, open the guitar case; that's all", "goal": "guitar"})),
        text_response("I remember days like this one. A few weeks ago you wrote \"grey again, no energy\", and today it's a clear sky; you always did feel the weather in your chest. The clear ones were never the hard part. What I'd tell you is that the guitar didn't happen on the good days, it happened on the ordinary Tuesdays when you opened the case before you opened anything else.\n\nOne thing: when you finish dinner, open the guitar case; that's all."),
    ]


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    command = args.command or "today"
    store = Store(config.home())
    store.init()

    trace = (lambda step: print(step, file=sys.stderr)) if args.trace else None

    if command == "stats":
        print(tools.format_stats(tools.compute_stats(store)))
        return 0
    if command == "export":
        from futureyou.tasks import export
        export.export(store)
        return 0
    if command == "delete-all":
        from futureyou.tasks import export
        return 0 if export.delete_all(store) else 1

    try:
        client = get_client(mock=args.mock, mock_responses=_mock_responses(command),
                            provider=args.provider, model=args.model)
        if command == "today":
            from futureyou.tasks import today
            if not store.read_text("self.md").strip():
                print("No self.md yet. Run `futureyou onboard` first (or continue without it).")
            today.run(store, client, text=args.text, mood=args.mood, trace=trace)
        elif command in ("onboard", "refresh-self"):
            from futureyou.tasks import onboard
            onboard.run(store, client, trace=trace)
        elif command == "ask":
            from futureyou.tasks import ask
            ask.run(store, client, args.question, trace=trace)
        elif command == "letter":
            from futureyou.tasks import letter
            text = Path(args.file).read_text(encoding="utf-8") if args.file else None
            letter.run(store, client, text=text, trace=trace)
        elif command == "chapter":
            from futureyou.tasks import chapter
            chapter.run(store, client, force=args.force, trace=trace)
        elif command == "review":
            from futureyou.tasks import review
            review.run(store, client, trace=trace)
    except (LLMError, AgentError) as e:
        print(f"futureyou: {e}", file=sys.stderr)
        return 1
    except (KeyboardInterrupt, EOFError):
        print()
        return 130
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
