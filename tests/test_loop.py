from futureyou import config
from futureyou.llm import LLMError, MockClient, text_response, tool_response
from futureyou.loop import AgentError, Step, run_agent
from futureyou.tools import Tool, _schema


def echo_tool(fails=False):
    def fn(q):
        if fails:
            raise RuntimeError("boom")
        return f"echo:{q}"
    return Tool("echo", "echoes", _schema({"q": {"type": "string"}}, ["q"]), fn)


def big_tool():
    return Tool("big", "big", _schema(), lambda: "x" * (config.MAX_TOOL_RESULT_CHARS + 50))


def test_plain_text_answer():
    client = MockClient([text_response("hello")])
    text, messages = run_agent(client, system=[], messages=[{"role": "user", "content": "hi"}], tools=[echo_tool()])
    assert text == "hello"
    assert [m["role"] for m in messages] == ["user", "assistant"]
    assert client.calls[0]["tools"][0]["name"] == "echo"


def test_tool_roundtrip_appends_result_then_answers():
    client = MockClient([tool_response(("echo", {"q": "a"})), text_response("done")])
    text, messages = run_agent(client, system=[], messages=[{"role": "user", "content": "go"}], tools=[echo_tool()])
    assert text == "done"
    assert [m["role"] for m in messages] == ["user", "assistant", "user", "assistant"]
    result = messages[2]["content"][0]
    assert result["type"] == "tool_result" and result["content"] == "echo:a" and "is_error" not in result
    # the second request carried the full history
    assert len(client.calls[1]["messages"]) == 3


def test_parallel_calls_return_in_one_user_message():
    client = MockClient([tool_response(("echo", {"q": "1"}), ("echo", {"q": "2"})), text_response("ok")])
    _, messages = run_agent(client, system=[], messages=[{"role": "user", "content": "go"}], tools=[echo_tool()])
    results = messages[2]["content"]
    assert len(results) == 2 and {r["content"] for r in results} == {"echo:1", "echo:2"}
    assert [r["tool_use_id"] for r in results] == ["toolu_mock_0", "toolu_mock_1"]


def test_tool_error_becomes_error_result_not_exception():
    client = MockClient([tool_response(("echo", {"q": "a"})), text_response("recovered")])
    text, messages = run_agent(client, system=[], messages=[{"role": "user", "content": "go"}], tools=[echo_tool(fails=True)])
    assert text == "recovered"
    result = messages[2]["content"][0]
    assert result["is_error"] is True and "boom" in result["content"]


def test_unknown_tool_and_bad_args_are_error_results():
    client = MockClient([tool_response(("nope", {}), ("echo", {"wrong": 1})), text_response("ok")])
    _, messages = run_agent(client, system=[], messages=[{"role": "user", "content": "go"}], tools=[echo_tool()])
    results = messages[2]["content"]
    assert all(r["is_error"] for r in results)
    assert "unknown tool" in results[0]["content"] and "bad arguments" in results[1]["content"]


def test_large_results_are_truncated():
    client = MockClient([tool_response(("big", {})), text_response("ok")])
    _, messages = run_agent(client, system=[], messages=[{"role": "user", "content": "go"}], tools=[big_tool()])
    content = messages[2]["content"][0]["content"]
    assert "[truncated; 50 more characters]" in content
    assert len(content) < config.MAX_TOOL_RESULT_CHARS + 100


def test_step_cap_raises():
    client = MockClient([tool_response(("echo", {"q": "x"}))] * 5)
    try:
        run_agent(client, system=[], messages=[{"role": "user", "content": "go"}], tools=[echo_tool()], max_steps=3)
    except AgentError as e:
        assert "3 model calls" in str(e)
    else:
        raise AssertionError("expected AgentError")


def test_max_tokens_and_refusal_stop_reasons():
    client = MockClient([text_response("half a thought", stop_reason="max_tokens")])
    text, _ = run_agent(client, system=[], messages=[{"role": "user", "content": "go"}], tools=[])
    assert text.startswith("half a thought") and "cut short" in text
    client = MockClient([text_response("", stop_reason="refusal")])
    text, _ = run_agent(client, system=[], messages=[{"role": "user", "content": "go"}], tools=[])
    assert "rather not" in text


def test_pause_turn_resends():
    client = MockClient([{"content": [{"type": "text", "text": "..."}], "stop_reason": "pause_turn", "usage": {}},
                         text_response("final")])
    text, _ = run_agent(client, system=[], messages=[{"role": "user", "content": "go"}], tools=[])
    assert text == "final" and len(client.calls) == 2


def test_trace_receives_steps():
    seen = []
    client = MockClient([tool_response(("echo", {"q": "a"})), text_response("ok")])
    run_agent(client, system=[], messages=[{"role": "user", "content": "go"}], tools=[echo_tool()], trace=seen.append)
    assert len(seen) == 1 and isinstance(seen[0], Step)
    assert "echo(" in str(seen[0]) and seen[0].result_chars == len("echo:a")


def test_mock_client_runs_dry():
    client = MockClient([])
    try:
        run_agent(client, system=[], messages=[{"role": "user", "content": "go"}], tools=[])
    except LLMError:
        pass
    else:
        raise AssertionError("expected LLMError")
