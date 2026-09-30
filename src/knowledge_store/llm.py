"""The model provider: Bedrock or the Anthropic API, one for every model call.

Every caller builds a Bedrock Converse request and reads a Converse response.
runtime_client() returns what they call `converse` on: the Bedrock runtime
client, or, with LLM_PROVIDER=anthropic, AnthropicConverse, which sends the same
request to the Anthropic Messages API and answers in Converse form. Callers
change only where they build their client.

There is no default. LLM_PROVIDER must be set, so a run can never fall back to one
provider while the lab is switched to the other. Deployed jobs, the proxy and the
agent get it from Terraform (llm_provider in terraform.tfvars); the CLI
exports the same value for local commands.

The API key comes from ANTHROPIC_API_KEY, or else from the Secrets Manager secret
named by ANTHROPIC_API_KEY_SECRET (how the deployed jobs, proxy and agent get it).
"""

from __future__ import annotations

import json
import logging
import os
import re
from functools import lru_cache

log = logging.getLogger("llm")

BEDROCK, ANTHROPIC = "bedrock", "anthropic"

# us.anthropic.claude-sonnet-4-5-20250929-v1:0 -> claude-sonnet-4-5-20250929
_BEDROCK_ID = re.compile(r"^(?:(?:us|eu|apac|jp|au|global)\.)?anthropic\.(?P<name>.+?)(?:-v\d+(?::\d+)?)?$")

_STOP_REASONS = {"end_turn": "end_turn", "tool_use": "tool_use", "max_tokens": "max_tokens",
                 "stop_sequence": "stop_sequence", "refusal": "content_filtered",
                 "pause_turn": "end_turn", "model_context_window_exceeded": "max_tokens"}


def provider() -> str:
    p = (os.environ.get("LLM_PROVIDER") or "").strip().lower()
    if not p:
        raise RuntimeError("LLM_PROVIDER is not set. Run through the pipeline task, which takes it from "
                           "llm_provider in terraform.tfvars, or export the same value.")
    if p not in (BEDROCK, ANTHROPIC):
        raise ValueError(f"LLM_PROVIDER must be {BEDROCK} or {ANTHROPIC}, not {p!r}")
    return p


def model_name(model_id: str) -> str:
    """The Anthropic API name for a model id. A Bedrock model or inference profile id
    is mapped to the same model, so existing Bedrock defaults keep working."""
    m = _BEDROCK_ID.match(model_id or "")
    return m.group("name") if m else model_id


# claude-opus-4-8, claude-sonnet-4-5-20250929, claude-opus-5, claude-fable-5-1
_MODEL = re.compile(r"^claude-(?P<family>[a-z]+)-(?P<major>\d+)(?:-(?P<minor>\d{1,2}))?(?:-\d{8})?$")


def _version(name: str) -> tuple[str, int, int] | None:
    m = _MODEL.match(name)
    return (m["family"], int(m["major"]), int(m["minor"] or 0)) if m else None


def rejects_sampling(name: str) -> bool:
    """Claude Opus 4.7 and later, Sonnet 5 and later, and Fable/Mythos reject temperature,
    top_p and top_k with a 400. Unknown names are left alone."""
    v = _version(name)
    if not v:
        return False
    family, major, minor = v
    return family in ("fable", "mythos") or major >= 5 or (family == "opus" and (major, minor) >= (4, 7))


def rejects_forced_tool(name: str) -> bool:
    """Claude Opus 5.5 and later, and Fable/Mythos 5.1 and later, reject tool_choice
    "tool" and "any" with a 400."""
    v = _version(name)
    if not v:
        return False
    family, major, minor = v
    return (family == "opus" and (major, minor) >= (5, 5)) or (
        family in ("fable", "mythos") and (major, minor) >= (5, 1))


def thinks_by_default(name: str) -> bool:
    """Claude Opus 5 and Sonnet 5 run adaptive thinking when `thinking` is omitted, and
    accept {"type": "disabled"} (Opus 5 only at effort high or below, the default)."""
    v = _version(name)
    return bool(v) and v[0] in ("opus", "sonnet") and v[1] >= 5


def runtime_client(read_timeout: int = 300, max_attempts: int = 2):
    """The client callers call `converse` on, for the configured provider. Every call is
    recorded in the call ledger (knowledge_store.ledger)."""
    from .ledger import LedgerClient
    if provider() == ANTHROPIC:
        return LedgerClient(AnthropicConverse(api_key(), timeout=read_timeout, max_retries=max_attempts), ANTHROPIC)
    import boto3
    from botocore.config import Config
    return LedgerClient(boto3.client("bedrock-runtime", config=Config(read_timeout=read_timeout,
                                                                      retries={"max_attempts": max_attempts})), BEDROCK)


@lru_cache(maxsize=1)
def api_key() -> str:
    key = os.environ.get("ANTHROPIC_API_KEY")
    if key:
        return key
    secret = os.environ.get("ANTHROPIC_API_KEY_SECRET")
    if not secret:
        raise RuntimeError("LLM_PROVIDER=anthropic needs ANTHROPIC_API_KEY or ANTHROPIC_API_KEY_SECRET")
    import boto3
    return boto3.client("secretsmanager").get_secret_value(SecretId=secret)["SecretString"].strip()


class ThrottlingException(Exception):
    """Raised for Anthropic rate limits and overload, named so that the callers'
    Bedrock retry loops (which match "Throttl") treat it as throttling."""


# --- request: Converse -> Messages ---------------------------------------------------


def _cache(blocks: list[dict]) -> None:
    if blocks:
        blocks[-1]["cache_control"] = {"type": "ephemeral"}


def _tool_result_content(content: list[dict]) -> list[dict]:
    import json
    out = []
    for c in content or []:
        if "text" in c:
            out.append({"type": "text", "text": c["text"]})
        elif "json" in c:
            out.append({"type": "text", "text": json.dumps(c["json"], default=str)})
    return out


def _content(blocks: list[dict]) -> list[dict]:
    out: list[dict] = []
    for b in blocks:
        if "text" in b:
            out.append({"type": "text", "text": b["text"]})
        elif "toolUse" in b:
            tu = b["toolUse"]
            out.append({"type": "tool_use", "id": tu["toolUseId"], "name": tu["name"], "input": tu.get("input") or {}})
        elif "toolResult" in b:
            tr = b["toolResult"]
            block = {"type": "tool_result", "tool_use_id": tr["toolUseId"],
                     "content": _tool_result_content(tr.get("content"))}
            if tr.get("status") == "error":
                block["is_error"] = True
            out.append(block)
        elif "cachePoint" in b:
            _cache(out)
        # reasoningContent and other Bedrock-only blocks are dropped
    return out


def _tool_choice(choice: dict | None) -> dict | None:
    if not choice:
        return None
    if "tool" in choice:
        return {"type": "tool", "name": choice["tool"]["name"]}
    if "any" in choice:
        return {"type": "any"}
    return {"type": "auto"}


def to_messages_request(modelId: str, messages: list[dict], system: list[dict] | None = None,
                        toolConfig: dict | None = None, inferenceConfig: dict | None = None,
                        **ignored) -> dict:
    """A Converse request as Messages API parameters. guardrailConfig and other
    Bedrock-only fields are dropped: the Anthropic path has no Bedrock guardrail."""
    if ignored:
        log.debug("dropped Bedrock-only request fields: %s", sorted(ignored))
    inf = inferenceConfig or {}
    req: dict = {"model": model_name(modelId), "max_tokens": inf.get("maxTokens", 4096),
                 "messages": [{"role": m["role"], "content": _content(m["content"])} for m in messages]}
    sys_blocks: list[dict] = []
    for b in system or []:
        if "text" in b:
            sys_blocks.append({"type": "text", "text": b["text"]})
        elif "cachePoint" in b:
            _cache(sys_blocks)
    if sys_blocks:
        req["system"] = sys_blocks
    if rejects_sampling(req["model"]):
        pass  # the callers' temperature 0 is for older models; newer ones take no sampling settings
    elif "temperature" in inf:
        req["temperature"] = inf["temperature"]
    elif "topP" in inf:
        req["top_p"] = inf["topP"]
    if inf.get("stopSequences"):
        req["stop_sequences"] = inf["stopSequences"]
    if toolConfig:
        tools: list[dict] = []
        for t in toolConfig.get("tools", []):
            if "toolSpec" in t:
                spec = t["toolSpec"]
                tools.append({"name": spec["name"], "description": spec.get("description", ""),
                              "input_schema": spec["inputSchema"]["json"]})
            elif "cachePoint" in t:
                _cache(tools)
        req["tools"] = tools
        choice = _tool_choice(toolConfig.get("toolChoice"))
        if choice:
            req["tool_choice"] = choice
        if choice and choice["type"] in ("tool", "any"):
            if rejects_forced_tool(req["model"]):
                raise ValueError(f"{req['model']} does not take forced tool use, which this caller needs; "
                                 "use Claude Opus 5 or Sonnet 5")
            # These models think by default. A forced tool call leaves nothing to think about, and
            # the API runs it without thinking anyway (checked on Sonnet 5, 2026-09-27); saying so
            # keeps the request from depending on that default.
            if thinks_by_default(req["model"]):
                req["thinking"] = {"type": "disabled"}
    return req


# --- response: Messages -> Converse ----------------------------------------------------


def to_converse_response(msg) -> dict:
    content = []
    for b in msg.content:
        if b.type == "text":
            content.append({"text": b.text})
        elif b.type == "tool_use":
            content.append({"toolUse": {"toolUseId": b.id, "name": b.name, "input": b.input}})
    u = msg.usage
    usage = {"inputTokens": u.input_tokens, "outputTokens": u.output_tokens,
             "cacheReadInputTokens": getattr(u, "cache_read_input_tokens", None) or 0,
             "cacheWriteInputTokens": getattr(u, "cache_creation_input_tokens", None) or 0}
    usage["totalTokens"] = sum(usage.values())
    return {"output": {"message": {"role": "assistant", "content": content}},
            "stopReason": _STOP_REASONS.get(msg.stop_reason, msg.stop_reason or "end_turn"),
            "usage": usage}


class AnthropicConverse:
    """The Converse operation, served by the Anthropic Messages API."""

    def __init__(self, api_key: str, *, timeout: float = 300, max_retries: int = 2, client=None):
        if client is None:
            import anthropic
            client = anthropic.Anthropic(api_key=api_key, timeout=timeout, max_retries=max_retries)
        self.client = client

    def converse(self, **kwargs) -> dict:
        import anthropic
        req = to_messages_request(**kwargs)
        try:
            # Streamed, because a long extraction (32k output tokens) outlasts a plain request.
            with self.client.messages.stream(**req) as stream:
                msg = stream.get_final_message()
        except anthropic.RateLimitError as e:
            raise ThrottlingException(str(e)) from e
        except anthropic.APIStatusError as e:
            if e.status_code in (429, 503, 529):
                raise ThrottlingException(str(e)) from e
            raise
        return to_converse_response(msg)


def strands_model(model_id: str, temperature: float = 0, max_tokens: int | None = None):
    """The Strands model for the agent, for the configured provider. `max_tokens` caps each model
    call's output (the chat's per-question limits); without it Anthropic gets 8000."""
    if provider() == ANTHROPIC:
        from strands.models.anthropic import AnthropicModel
        name = model_name(model_id)
        return AnthropicModel(client_args={"api_key": api_key()}, model_id=name, max_tokens=max_tokens or 8000,
                              params={} if rejects_sampling(name) else {"temperature": temperature})
    from strands.models import BedrockModel
    return BedrockModel(model_id=model_id, temperature=temperature, **({"max_tokens": max_tokens} if max_tokens else {}))


def decode_tool_input(value, schema: dict):
    """A tool call's input with JSON-encoded strings decoded where the schema wants an array or an
    object. Models sometimes send a nested array as a string holding its JSON; left as is, code
    that iterates it walks the characters. Anything that does not decode is left for the caller's
    own checks."""
    want = schema.get("type") if isinstance(schema, dict) else None
    if isinstance(value, str) and want in ("array", "object"):
        try:
            decoded = json.loads(value)
        except ValueError:
            return value
        if isinstance(decoded, list if want == "array" else dict):
            value = decoded
    if isinstance(value, dict) and want == "object":
        props = schema.get("properties") or {}
        return {k: decode_tool_input(v, props.get(k, {})) for k, v in value.items()}
    if isinstance(value, list) and want == "array":
        return [decode_tool_input(v, schema.get("items") or {}) for v in value]
    return value
