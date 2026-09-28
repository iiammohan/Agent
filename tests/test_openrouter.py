"""The OpenRouter client: shape translation both ways, and a full agent
round-trip through a fake HTTP layer. No network."""

import json
import os

from futureyou import llm
from futureyou.llm import LLMError, OpenRouterClient, from_chat_response, to_chat_messages, to_chat_tool
from futureyou.loop import run_agent
from futureyou.tools import Tool, _schema


class FakeOpenRouter(OpenRouterClient):
    """Same client, HTTP replaced by a scripted list of raw API responses."""

    def __init__(self, raw_responses, model="test/model"):
        super().__init__(model=model, api_key="sk-or-test")
        self.raw = list(raw_responses)
        self.payloads = []

    def _post(self, payload):
        self.payloads.append(payload)
        return self.raw.pop(0)


def chat_text(text, finish="stop"):
    return {"choices": [{"message": {"role": "assistant", "content": text}, "finish_reason": finish}],
            "usage": {"prompt_tokens": 1, "completion_tokens": 1}}


def chat_tool_call(name, args, call_id="call_1", text=None):
    return {"choices": [{"message": {"role": "assistant", "content": text,
                                     "tool_calls": [{"id": call_id, "type": "function",
                                                     "function": {"name": name, "arguments": json.dumps(args)}}]},
                         "finish_reason": "tool_calls"}], "usage": {}}


def test_system_blocks_become_one_system_message():
    out = to_chat_messages([{"type": "text", "text": "A"}, {"type": "text", "text": "B", "cache_control": {"type": "ephemeral"}}],
                           [{"role": "user", "content": "hi"}])
    assert out == [{"role": "system", "content": "A\n\nB"}, {"role": "user", "content": "hi"}]


def test_assistant_tool_use_and_results_translate():
    messages = [
        {"role": "user", "content": "go"},
        {"role": "assistant", "content": [{"type": "text", "text": "looking"},
                                          {"type": "tool_use", "id": "c1", "name": "echo", "input": {"q": "a"}}]},
        {"role": "user", "content": [{"type": "tool_result", "tool_use_id": "c1", "content": "echo:a"},
                                     {"type": "tool_result", "tool_use_id": "c2", "content": "boom", "is_error": True}]},
    ]
    out = to_chat_messages([], messages)
    assert out[1]["role"] == "assistant" and out[1]["content"] == "looking"
    assert out[1]["tool_calls"][0]["function"] == {"name": "echo", "arguments": '{"q": "a"}'}
    assert out[2] == {"role": "tool", "tool_call_id": "c1", "content": "echo:a"}
    assert out[3] == {"role": "tool", "tool_call_id": "c2", "content": "ERROR: boom"}
    # an assistant turn with only tool calls has null content, as the chat API expects
    only_calls = to_chat_messages([], [{"role": "assistant", "content": [{"type": "tool_use", "id": "x", "name": "n", "input": {}}]}])
    assert only_calls[0]["content"] is None


def test_tool_spec_translates():
    spec = Tool("echo", "echoes", _schema({"q": {"type": "string"}}, ["q"]), lambda q: q).spec()
    t = to_chat_tool(spec)
    assert t["type"] == "function" and t["function"]["name"] == "echo"
    assert t["function"]["parameters"]["required"] == ["q"]


def test_response_translation_stop_reasons_and_bad_json():
    r = from_chat_response(chat_text("hello"))
    assert r["content"] == [{"type": "text", "text": "hello"}] and r["stop_reason"] == "end_turn"
    assert from_chat_response(chat_text("x", finish="length"))["stop_reason"] == "max_tokens"
    assert from_chat_response(chat_text("x", finish="content_filter"))["stop_reason"] == "refusal"
    r = from_chat_response(chat_tool_call("echo", {"q": "1"}, text="thinking"))
    assert r["stop_reason"] == "tool_use"
    assert r["content"][0] == {"type": "text", "text": "thinking"}
    assert r["content"][1] == {"type": "tool_use", "id": "call_1", "name": "echo", "input": {"q": "1"}}
    bad = {"choices": [{"message": {"tool_calls": [{"id": "c", "function": {"name": "echo", "arguments": "{not json"}}]},
                        "finish_reason": "tool_calls"}]}
    r = from_chat_response(bad)
    assert "_unparseable_arguments" in r["content"][0]["input"]
    try:
        from_chat_response({"error": {"message": "no such model"}})
    except LLMError as e:
        assert "no such model" in str(e)
    else:
        raise AssertionError("expected LLMError")


def test_full_round_trip_through_the_loop():
    client = FakeOpenRouter([chat_tool_call("echo", {"q": "a"}), chat_text("done")])
    tool = Tool("echo", "echoes", _schema({"q": {"type": "string"}}, ["q"]), lambda q: f"echo:{q}")
    text, messages = run_agent(client, system=[{"type": "text", "text": "sys"}],
                               messages=[{"role": "user", "content": "go"}], tools=[tool], effort="medium", max_tokens=100)
    assert text == "done"
    first, second = client.payloads
    assert first["model"] == "test/model" and first["max_tokens"] == 100
    assert first["reasoning"] == {"effort": "medium"}
    assert first["tools"][0]["function"]["name"] == "echo"
    assert first["messages"][0] == {"role": "system", "content": "sys"}
    # the second request carried the assistant tool call and the tool result in chat shape
    roles = [m["role"] for m in second["messages"]]
    assert roles == ["system", "user", "assistant", "tool"]
    assert second["messages"][3] == {"role": "tool", "tool_call_id": "call_1", "content": "echo:a"}
    # unparseable arguments become an error result, not a crash
    client = FakeOpenRouter([{"choices": [{"message": {"tool_calls": [{"id": "c", "function": {"name": "echo", "arguments": "oops"}}]},
                                           "finish_reason": "tool_calls"}]}, chat_text("recovered")])
    text, messages = run_agent(client, system=[], messages=[{"role": "user", "content": "go"}], tools=[tool])
    assert text == "recovered" and messages[2]["content"][0]["is_error"] is True


def test_provider_resolution_and_missing_key():
    saved = {k: os.environ.pop(k, None) for k in ("FUTUREYOU_PROVIDER", "OPENROUTER_API_KEY", "ANTHROPIC_API_KEY")}
    try:
        assert llm.resolve_provider() == "anthropic"
        os.environ["OPENROUTER_API_KEY"] = "sk-or-x"
        assert llm.resolve_provider() == "openrouter"
        os.environ["ANTHROPIC_API_KEY"] = "sk-ant-x"
        assert llm.resolve_provider() == "anthropic"  # both set: Anthropic unless told otherwise
        os.environ["FUTUREYOU_PROVIDER"] = "openrouter"
        assert llm.resolve_provider() == "openrouter"
        assert llm.resolve_provider("anthropic") == "anthropic"  # explicit flag wins
        del os.environ["OPENROUTER_API_KEY"]
        try:
            OpenRouterClient("m")
        except LLMError as e:
            assert "OPENROUTER_API_KEY" in str(e)
        else:
            raise AssertionError("expected LLMError")
        try:
            llm.get_client(provider="nope")
        except LLMError as e:
            assert "unknown provider" in str(e)
        else:
            raise AssertionError("expected LLMError")
    finally:
        for k, v in saved.items():
            os.environ.pop(k, None)
            if v is not None:
                os.environ[k] = v
