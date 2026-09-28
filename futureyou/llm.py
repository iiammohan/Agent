"""The one place that talks to a model.

Everything above this file works with plain dicts in the Messages API shape
(`{"role": ..., "content": [blocks]}`), so the agent loop, the tools and the
tests never import a provider SDK. Two providers are implemented:

    AnthropicClient   the official SDK, Claude models direct
    OpenRouterClient  OpenRouter's chat-completions API, any model they list
                      (standard library only; translates message shapes)
    MockClient        scripted responses for tests and --mock runs

Response shape returned by every client:

    {"content": [ {"type": "text", "text": ...} | {"type": "tool_use", "id", "name", "input"} | ... ],
     "stop_reason": "end_turn" | "tool_use" | "max_tokens" | "refusal" | "pause_turn",
     "usage": {...}}
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Protocol

from futureyou import config


class LLMError(Exception):
    """A model call failed in a way the user should hear about in one line."""


class LLMClient(Protocol):
    def create(
        self,
        *,
        system: list[dict],
        messages: list[dict],
        tools: list[dict],
        effort: str,
        max_tokens: int,
        stream: bool = False,
    ) -> dict: ...


# ---------------------------------------------------------------------------
# Anthropic, direct
# ---------------------------------------------------------------------------

class AnthropicClient:
    """Official SDK. Adaptive thinking on; effort per task; streaming for long output."""

    def __init__(self, model: str | None = None):
        try:
            import anthropic  # imported here so the rest of the package works without it
        except ImportError as e:  # pragma: no cover - depends on the environment
            raise LLMError("The anthropic package is not installed. Run: pip install anthropic") from e
        self._anthropic = anthropic
        self._client = anthropic.Anthropic()
        self.model = model or config.MODEL

    def create(self, *, system, messages, tools, effort, max_tokens, stream=False) -> dict:
        a = self._anthropic
        kwargs = dict(
            model=self.model,
            max_tokens=max_tokens,
            system=system,
            messages=messages,
            thinking={"type": "adaptive"},
            output_config={"effort": effort},
        )
        if tools:
            kwargs["tools"] = tools
        try:
            if stream:
                with self._client.messages.stream(**kwargs) as s:
                    msg = s.get_final_message()
            else:
                msg = self._client.messages.create(**kwargs)
        except a.AuthenticationError as e:
            raise LLMError("Invalid or missing API key. Set ANTHROPIC_API_KEY or run `ant auth login`.") from e
        except a.RateLimitError as e:
            raise LLMError("Rate limited by the API. Wait a minute and try again.") from e
        except a.APIStatusError as e:
            raise LLMError(f"API error {e.status_code}: {e.message}") from e
        except a.APIConnectionError as e:
            raise LLMError("Could not reach the API. Check your connection.") from e
        return msg.to_dict()


# ---------------------------------------------------------------------------
# OpenRouter (chat-completions shape, any model)
# ---------------------------------------------------------------------------

def to_chat_messages(system: list[dict], messages: list[dict]) -> list[dict]:
    """Messages-API shape -> chat-completions shape."""
    out: list[dict] = []
    sys_text = "\n\n".join(b["text"] for b in system if b.get("type") == "text")
    if sys_text:
        out.append({"role": "system", "content": sys_text})
    for m in messages:
        role, content = m["role"], m["content"]
        if isinstance(content, str):
            out.append({"role": role, "content": content})
            continue
        if role == "assistant":
            text = "\n".join(b.get("text", "") for b in content if b.get("type") == "text").strip()
            calls = [
                {"id": b["id"], "type": "function",
                 "function": {"name": b["name"], "arguments": json.dumps(b.get("input") or {})}}
                for b in content if b.get("type") == "tool_use"
            ]
            msg: dict = {"role": "assistant", "content": text or None}
            if calls:
                msg["tool_calls"] = calls
            out.append(msg)
        else:  # user turn: tool results and/or text blocks
            for b in content:
                if b.get("type") == "tool_result":
                    body = b["content"]
                    if b.get("is_error"):
                        body = "ERROR: " + body
                    out.append({"role": "tool", "tool_call_id": b["tool_use_id"], "content": body})
                elif b.get("type") == "text":
                    out.append({"role": "user", "content": b["text"]})
    return out


def to_chat_tool(spec: dict) -> dict:
    return {"type": "function", "function": {
        "name": spec["name"], "description": spec["description"], "parameters": spec["input_schema"]}}


_STOP = {"tool_calls": "tool_use", "length": "max_tokens", "content_filter": "refusal"}


def from_chat_response(data: dict) -> dict:
    """chat-completions response -> Messages-API shape."""
    if "error" in data and not data.get("choices"):
        err = data["error"]
        raise LLMError(f"OpenRouter error: {err.get('message', err) if isinstance(err, dict) else err}")
    choice = data["choices"][0]
    msg = choice.get("message") or {}
    content: list[dict] = []
    if msg.get("content"):
        content.append({"type": "text", "text": msg["content"]})
    for i, call in enumerate(msg.get("tool_calls") or []):
        fn = call.get("function") or {}
        try:
            args = json.loads(fn.get("arguments") or "{}")
        except json.JSONDecodeError:
            args = {"_unparseable_arguments": fn.get("arguments")}
        content.append({"type": "tool_use", "id": call.get("id") or f"call_{i}", "name": fn.get("name", ""), "input": args})
    stop = _STOP.get(choice.get("finish_reason"), "end_turn")
    if any(b["type"] == "tool_use" for b in content):
        stop = "tool_use"
    return {"content": content, "stop_reason": stop, "usage": data.get("usage", {})}


class OpenRouterClient:
    """Any model on OpenRouter, via its chat-completions endpoint. Tool calling
    uses the OpenAI function-calling shape, which OpenRouter normalises across
    providers; `reasoning.effort` is passed and ignored by models without it."""

    def __init__(self, model: str | None = None, api_key: str | None = None, base_url: str | None = None):
        self.model = model or config.OPENROUTER_MODEL
        self.api_key = api_key or os.environ.get("OPENROUTER_API_KEY")
        if not self.api_key:
            raise LLMError("OPENROUTER_API_KEY is not set.")
        base = (base_url or os.environ.get("OPENROUTER_BASE_URL") or config.OPENROUTER_BASE_URL).rstrip("/")
        self.url = base + "/chat/completions"

    def create(self, *, system, messages, tools, effort, max_tokens, stream=False) -> dict:
        payload: dict = {
            "model": self.model,
            "max_tokens": max_tokens,
            "messages": to_chat_messages(system, messages),
        }
        if tools:
            payload["tools"] = [to_chat_tool(t) for t in tools]
        if effort in ("low", "medium", "high"):
            payload["reasoning"] = {"effort": effort}
        return from_chat_response(self._post(payload))

    def _post(self, payload: dict) -> dict:
        req = urllib.request.Request(
            self.url, data=json.dumps(payload).encode("utf-8"), method="POST",
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json",
                     "HTTP-Referer": "https://github.com/iiammohan/Agent", "X-Title": "Future You"},
        )
        try:
            with urllib.request.urlopen(req, timeout=600) as r:
                return json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace")[:300]
            if e.code == 401:
                raise LLMError("OpenRouter rejected the key (401). Check OPENROUTER_API_KEY.") from e
            if e.code == 429:
                raise LLMError("OpenRouter rate limit (429). Wait a minute and try again.") from e
            raise LLMError(f"OpenRouter error {e.code}: {body}") from e
        except urllib.error.URLError as e:
            raise LLMError(f"Could not reach OpenRouter: {e.reason}") from e


# ---------------------------------------------------------------------------
# Mock
# ---------------------------------------------------------------------------

class MockClient:
    """Replays a scripted list of responses. Each `create` pops the next one and
    records the request, so tests can assert on what the loop sent."""

    def __init__(self, responses: list[dict]):
        self.responses = list(responses)
        self.calls: list[dict] = []

    def create(self, *, system, messages, tools, effort, max_tokens, stream=False) -> dict:
        self.calls.append(
            {"system": system, "messages": [dict(m) for m in messages], "tools": tools,
             "effort": effort, "max_tokens": max_tokens, "stream": stream}
        )
        if not self.responses:
            raise LLMError("MockClient ran out of scripted responses")
        return self.responses.pop(0)


# -- helpers for building scripted responses (used by tests and --mock) -----

def text_response(text: str, stop_reason: str = "end_turn") -> dict:
    return {"content": [{"type": "text", "text": text}], "stop_reason": stop_reason, "usage": {}}


def tool_response(*calls: tuple[str, dict], text: str | None = None) -> dict:
    content: list[dict] = []
    if text:
        content.append({"type": "text", "text": text})
    for i, (name, args) in enumerate(calls):
        content.append({"type": "tool_use", "id": f"toolu_mock_{i}", "name": name, "input": args})
    return {"content": content, "stop_reason": "tool_use", "usage": {}}


# ---------------------------------------------------------------------------
# Selection
# ---------------------------------------------------------------------------

def resolve_provider(provider: str | None = None) -> str:
    """Explicit flag, then FUTUREYOU_PROVIDER, then: OpenRouter if only its key
    is set, otherwise Anthropic."""
    p = provider or os.environ.get("FUTUREYOU_PROVIDER")
    if p:
        return p.lower()
    if os.environ.get("OPENROUTER_API_KEY") and not os.environ.get("ANTHROPIC_API_KEY"):
        return "openrouter"
    return "anthropic"


def get_client(mock: bool = False, mock_responses: list[dict] | None = None,
               provider: str | None = None, model: str | None = None) -> LLMClient:
    if mock:
        return MockClient(mock_responses or [])
    p = resolve_provider(provider)
    if p == "openrouter":
        return OpenRouterClient(model)
    if p == "anthropic":
        return AnthropicClient(model)
    raise LLMError(f"unknown provider '{p}' (use anthropic or openrouter)")
