"""The agent loop, written out by hand so you can see every step.

    messages = [user turn]
    loop:
        response = model(system, messages, tools)
        append the assistant turn (all of its content blocks, unchanged)
        if it asked for tools:
            run each tool locally
            append ONE user turn holding every tool_result
            continue
        return its text

That is the whole idea of an agent: the model decides, your code acts, the
result goes back, repeat. Everything else here is bookkeeping: result size
limits, error results instead of exceptions, and a cap on steps.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass

from futureyou import config
from futureyou.tools import Tool


class AgentError(Exception):
    pass


@dataclass
class Step:
    """One tool call, for the --trace view."""
    n: int
    tool: str
    args: dict
    result_chars: int
    is_error: bool

    def __str__(self) -> str:
        flag = " (error)" if self.is_error else ""
        args = json.dumps(self.args, ensure_ascii=False)
        if len(args) > 120:
            args = args[:117] + "..."
        return f"  step {self.n}: {self.tool}({args}) -> {self.result_chars} chars{flag}"


Trace = Callable[[Step], None] | None


def run_agent(
    client,
    *,
    system: list[dict],
    messages: list[dict],
    tools: list[Tool],
    effort: str = "medium",
    max_tokens: int = 4096,
    max_steps: int = config.MAX_AGENT_STEPS,
    stream: bool = False,
    trace: Trace = None,
) -> tuple[str, list[dict]]:
    """Run until the model answers with text. Returns (text, full message list).

    `messages` is appended to in place, so callers that hold a multi-turn
    conversation (onboarding) can keep passing the same list.
    """
    by_name = {t.name: t for t in tools}
    specs = [t.spec() for t in tools]
    n = 0

    for _ in range(max_steps):
        response = client.create(
            system=system, messages=messages, tools=specs,
            effort=effort, max_tokens=max_tokens, stream=stream,
        )
        content = response["content"]
        stop = response.get("stop_reason")
        messages.append({"role": "assistant", "content": content})

        if stop == "tool_use":
            results = []
            for block in content:
                if block.get("type") != "tool_use":
                    continue
                n += 1
                out, is_error = _execute(by_name, block["name"], block.get("input") or {})
                if trace:
                    trace(Step(n, block["name"], block.get("input") or {}, len(out), is_error))
                result = {"type": "tool_result", "tool_use_id": block["id"], "content": out}
                if is_error:
                    result["is_error"] = True
                results.append(result)
            # All results for one assistant turn go back in a single user turn.
            messages.append({"role": "user", "content": results})
            continue

        if stop == "pause_turn":
            # Server-side pause; sending the same conversation back resumes it.
            continue

        text = _text_of(content).strip()
        if stop == "max_tokens":
            text += "\n\n[The reply was cut short at the length limit.]"
        elif stop == "refusal":
            text = "Future You would rather not answer that one. Try putting it another way tomorrow."
        return text, messages

    raise AgentError(f"gave up after {max_steps} model calls without a final answer")


def _execute(by_name: dict[str, Tool], name: str, args: dict) -> tuple[str, bool]:
    tool = by_name.get(name)
    if tool is None:
        return f"unknown tool: {name}", True
    try:
        out = tool.fn(**args)
    except TypeError as e:  # wrong arguments; tell the model, don't crash
        return f"bad arguments for {name}: {e}", True
    except Exception as e:  # noqa: BLE001 - any tool failure becomes an error result
        return f"{name} failed: {e}", True
    out = str(out)
    limit = config.MAX_TOOL_RESULT_CHARS
    if len(out) > limit:
        out = out[:limit] + f"\n[truncated; {len(out) - limit} more characters]"
    return out, False


def _text_of(content: list[dict]) -> str:
    return "\n".join(b.get("text", "") for b in content if b.get("type") == "text")
