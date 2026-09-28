"""The one place that talks to the model.

Everything above this file works with plain dicts in the Messages API shape
(`{"role": ..., "content": [blocks]}`), so the agent loop, the tools and the
tests never import the SDK. `AnthropicClient` wraps the official SDK;
`MockClient` replays scripted responses for tests and `--mock` runs.

Response shape returned by every client:

    {"content": [ {"type": "text", "text": ...} | {"type": "tool_use", "id", "name", "input"} | ... ],
     "stop_reason": "end_turn" | "tool_use" | "max_tokens" | "refusal" | "pause_turn",
     "usage": {...}}
"""

from __future__ import annotations

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


class AnthropicClient:
    """Official SDK. Adaptive thinking on; effort per task; streaming for long output."""

    def __init__(self, model: str = config.MODEL):
        try:
            import anthropic  # imported here so the rest of the package works without it
        except ImportError as e:  # pragma: no cover - depends on the environment
            raise LLMError("The anthropic package is not installed. Run: pip install anthropic") from e
        self._anthropic = anthropic
        self._client = anthropic.Anthropic()
        self.model = model

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


def get_client(mock: bool = False, mock_responses: list[dict] | None = None) -> LLMClient:
    if mock:
        return MockClient(mock_responses or [])
    return AnthropicClient()
