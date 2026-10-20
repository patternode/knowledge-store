"""The ModelClient port: Bedrock's Converse shape, served by Bedrock or by the Anthropic API
through AnthropicConverse. Offline: the Anthropic SDK client is a fake."""

from types import SimpleNamespace

import pytest

from knowledge_store.platform_services.adapters import llm

anthropic = pytest.importorskip("anthropic", reason="the agent extra is not installed")


# --- provider --------------------------------------------------------------------------


def test_there_is_no_default_provider(monkeypatch):
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    with pytest.raises(RuntimeError, match="LLM_PROVIDER"):
        llm.provider()


def test_the_provider_is_read_in_any_case(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", " Bedrock ")
    assert llm.provider() == "bedrock"


def test_bedrock_runtime_client_is_wrapped_in_the_ledger(monkeypatch):
    pytest.importorskip("boto3")
    monkeypatch.setenv("LLM_PROVIDER", "bedrock")
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")
    c = llm.runtime_client()
    assert c._provider == "bedrock" and hasattr(c, "converse")


def test_sdk_client_refuses_a_provider_without_the_messages_api():
    with pytest.raises(ValueError):
        llm.sdk_client("bedrock")


def test_api_key_needs_a_key_or_a_secret(monkeypatch):
    llm.api_key.cache_clear()
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY_SECRET", raising=False)
    try:
        with pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY"):
            llm.api_key()
    finally:
        llm.api_key.cache_clear()


def test_api_key_comes_from_the_environment_first(monkeypatch):
    llm.api_key.cache_clear()
    monkeypatch.setenv("ANTHROPIC_API_KEY", "k1")
    try:
        assert llm.api_key() == "k1"
    finally:
        llm.api_key.cache_clear()


# --- model names -------------------------------------------------------------------------


@pytest.mark.parametrize("bedrock,name", [
    ("us.anthropic.claude-sonnet-4-5-20250929-v1:0", "claude-sonnet-4-5-20250929"),
    ("anthropic.claude-haiku-4-5", "claude-haiku-4-5"),
    ("global.anthropic.claude-opus-5-v2", "claude-opus-5"),
    ("claude-opus-5", "claude-opus-5"),
    ("", ""),
])
def test_a_bedrock_id_maps_to_the_api_name(bedrock, name):
    assert llm.model_name(bedrock) == name


@pytest.mark.parametrize("name,expected", [("claude-opus-4-6", False), ("claude-opus-4-7", True), ("claude-sonnet-4-5", False), ("claude-sonnet-5", True), ("claude-fable-5-1", True), ("gpt-4", False)])
def test_which_models_reject_sampling_settings(name, expected):
    assert llm.rejects_sampling(name) is expected


@pytest.mark.parametrize("name,expected", [("claude-opus-5", False), ("claude-opus-5-5", True), ("claude-fable-5", False), ("claude-fable-5-1", True), ("claude-sonnet-5", False), ("unknown", False)])
def test_which_models_reject_forced_tool_use(name, expected):
    assert llm.rejects_forced_tool(name) is expected


@pytest.mark.parametrize("name,expected", [("claude-opus-5", True), ("claude-sonnet-5", True), ("claude-opus-4-8", False), ("claude-haiku-4-5", False), ("x", False)])
def test_which_models_think_by_default(name, expected):
    assert llm.thinks_by_default(name) is expected


# --- request translation -------------------------------------------------------------------

def _tool(name="record"):
    return {"toolSpec": {"name": name, "description": "d", "inputSchema": {"json": {"type": "object"}}}}


def test_a_converse_request_becomes_a_messages_request():
    req = llm.to_messages_request(
        modelId="us.anthropic.claude-sonnet-4-5-20250929-v1:0",
        messages=[{"role": "user", "content": [{"text": "hi"}, {"cachePoint": {}}]}],
        system=[{"text": "be brief"}, {"cachePoint": {}}],
        inferenceConfig={"maxTokens": 100, "temperature": 0, "stopSequences": ["END"]},
        guardrailConfig={"x": 1})
    assert req["model"] == "claude-sonnet-4-5-20250929" and req["max_tokens"] == 100
    assert req["messages"][0]["content"] == [{"type": "text", "text": "hi", "cache_control": {"type": "ephemeral"}}]
    assert req["system"] == [{"type": "text", "text": "be brief", "cache_control": {"type": "ephemeral"}}]
    assert req["temperature"] == 0 and req["stop_sequences"] == ["END"]
    assert "guardrailConfig" not in req


def test_max_tokens_defaults_to_4096():
    assert llm.to_messages_request(modelId="claude-haiku-4-5", messages=[])["max_tokens"] == 4096


def test_top_p_is_sent_when_there_is_no_temperature():
    req = llm.to_messages_request(modelId="claude-haiku-4-5", messages=[], inferenceConfig={"topP": 0.9})
    assert req["top_p"] == 0.9 and "temperature" not in req


def test_sampling_settings_are_dropped_for_models_that_reject_them():
    req = llm.to_messages_request(modelId="claude-sonnet-5", messages=[], inferenceConfig={"temperature": 0})
    assert "temperature" not in req


def test_tool_use_and_tool_results_translate():
    msgs = [{"role": "assistant", "content": [{"toolUse": {"toolUseId": "t1", "name": "f", "input": {"a": 1}}}, {"reasoningContent": {}}]},
            {"role": "user", "content": [{"toolResult": {"toolUseId": "t1", "status": "error", "content": [{"text": "bad"}, {"json": {"k": 2}}]}}]}]
    req = llm.to_messages_request(modelId="claude-haiku-4-5", messages=msgs)
    assert req["messages"][0]["content"] == [{"type": "tool_use", "id": "t1", "name": "f", "input": {"a": 1}}]
    assert req["messages"][1]["content"] == [{"type": "tool_result", "tool_use_id": "t1", "is_error": True,
                                              "content": [{"type": "text", "text": "bad"}, {"type": "text", "text": '{"k": 2}'}]}]


def test_tools_and_an_auto_choice_translate():
    req = llm.to_messages_request(modelId="claude-haiku-4-5", messages=[], toolConfig={"tools": [_tool(), {"cachePoint": {}}], "toolChoice": {"auto": {}}})
    assert req["tools"] == [{"name": "record", "description": "d", "input_schema": {"type": "object"}, "cache_control": {"type": "ephemeral"}}]
    assert req["tool_choice"] == {"type": "auto"}


def test_a_forced_tool_disables_thinking_on_models_that_think_by_default():
    req = llm.to_messages_request(modelId="claude-sonnet-5", messages=[], toolConfig={"tools": [_tool()], "toolChoice": {"tool": {"name": "record"}}})
    assert req["tool_choice"] == {"type": "tool", "name": "record"} and req["thinking"] == {"type": "disabled"}


def test_any_tool_choice_translates():
    req = llm.to_messages_request(modelId="claude-haiku-4-5", messages=[], toolConfig={"tools": [_tool()], "toolChoice": {"any": {}}})
    assert req["tool_choice"] == {"type": "any"} and "thinking" not in req


def test_a_forced_tool_on_a_model_that_rejects_it_is_refused():
    with pytest.raises(ValueError, match="forced tool use"):
        llm.to_messages_request(modelId="claude-opus-5-5", messages=[], toolConfig={"tools": [_tool()], "toolChoice": {"any": {}}})


def test_no_tool_choice_sends_none():
    req = llm.to_messages_request(modelId="claude-haiku-4-5", messages=[], toolConfig={"tools": [_tool()]})
    assert "tool_choice" not in req


# --- response translation ------------------------------------------------------------------


def _msg(stop="tool_use", cache_read=5, cache_write=None):
    return SimpleNamespace(
        content=[SimpleNamespace(type="text", text="ok"), SimpleNamespace(type="tool_use", id="t", name="f", input={"a": 1}), SimpleNamespace(type="thinking")],
        usage=SimpleNamespace(input_tokens=10, output_tokens=4, cache_read_input_tokens=cache_read, cache_creation_input_tokens=cache_write),
        stop_reason=stop)


def test_a_messages_response_becomes_a_converse_response():
    r = llm.to_converse_response(_msg())
    assert r["output"]["message"]["content"] == [{"text": "ok"}, {"toolUse": {"toolUseId": "t", "name": "f", "input": {"a": 1}}}]
    assert r["stopReason"] == "tool_use"
    assert r["usage"] == {"inputTokens": 10, "outputTokens": 4, "cacheReadInputTokens": 5, "cacheWriteInputTokens": 0, "totalTokens": 19}


@pytest.mark.parametrize("stop,converse", [("refusal", "content_filtered"), ("pause_turn", "end_turn"), ("model_context_window_exceeded", "max_tokens"), (None, "end_turn"), ("novel", "novel")])
def test_stop_reasons_map_to_converse_names(stop, converse):
    assert llm.to_converse_response(_msg(stop))["stopReason"] == converse


class _Stream:
    def __init__(self, msg=None, error=None):
        self.msg, self.error = msg, error

    def __enter__(self):
        if self.error:
            raise self.error
        return self

    def __exit__(self, *a):
        return False

    def get_final_message(self):
        return self.msg


class _SDK:
    def __init__(self, stream):
        self.sent = None
        self.messages = SimpleNamespace(stream=self._stream)
        self._s = stream

    def _stream(self, **req):
        self.sent = req
        return self._s


def test_anthropic_converse_streams_the_translated_request():
    sdk = _SDK(_Stream(_msg("end_turn")))
    r = llm.AnthropicConverse(client=sdk).converse(modelId="claude-haiku-4-5", messages=[{"role": "user", "content": [{"text": "q"}]}])
    assert sdk.sent["model"] == "claude-haiku-4-5" and r["stopReason"] == "end_turn"


def _status_error(code):
    import httpx

    resp = httpx.Response(code, request=httpx.Request("POST", "https://api.anthropic.com"))
    return anthropic.APIStatusError("boom", response=resp, body=None)


@pytest.mark.parametrize("code", [429, 503, 529])
def test_overload_and_rate_limits_are_throttling(code):
    sdk = _SDK(_Stream(error=_status_error(code)))
    with pytest.raises(llm.ThrottlingException):
        llm.AnthropicConverse(client=sdk).converse(modelId="claude-haiku-4-5", messages=[])


def test_other_api_errors_pass_through():
    sdk = _SDK(_Stream(error=_status_error(400)))
    with pytest.raises(anthropic.APIStatusError):
        llm.AnthropicConverse(client=sdk).converse(modelId="claude-haiku-4-5", messages=[])


# --- tool input --------------------------------------------------------------------------------


def test_a_json_string_where_an_array_is_wanted_is_decoded():
    assert llm.decode_tool_input('[1, 2]', {"type": "array"}) == [1, 2]


def test_nested_strings_are_decoded_by_the_schema():
    schema = {"type": "object", "properties": {"rows": {"type": "array", "items": {"type": "object", "properties": {"tags": {"type": "array"}}}}}}
    value = {"rows": '[{"tags": "[\\"a\\"]"}]', "other": "[1]"}
    assert llm.decode_tool_input(value, schema) == {"rows": [{"tags": ["a"]}], "other": "[1]"}


def test_a_string_that_is_not_json_is_left_alone():
    assert llm.decode_tool_input("not json", {"type": "array"}) == "not json"


def test_json_of_the_wrong_shape_is_left_alone():
    assert llm.decode_tool_input('{"a": 1}', {"type": "array"}) == '{"a": 1}'


def test_a_value_without_a_schema_is_left_alone():
    assert llm.decode_tool_input("[1]", None) == "[1]"
