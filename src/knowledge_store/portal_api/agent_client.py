"""Ask the chat agent on AgentCore Runtime, as the person asking.

The Runtime authorises inbound calls with the person's own Cognito access token (OAuth bearer),
and the agent presents the same token to AgentCore Gateway, so every tool call runs in that
person's scope. Nothing here holds a credential of its own.

    AGENT_RUNTIME_ARN         the agent runtime
    AGENT_RUNTIME_QUALIFIER   the endpoint (default DEFAULT)

Standard library only.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
import uuid


def configured() -> bool:
    return bool(os.environ.get("AGENT_RUNTIME_ARN"))


def invocation_url(arn: str, qualifier: str) -> str:
    region = arn.split(":")[3]
    return (f"https://bedrock-agentcore.{region}.amazonaws.com/runtimes/{urllib.parse.quote(arn, safe='')}"
            f"/invocations?qualifier={urllib.parse.quote(qualifier)}")


def ask(token: str, payload: dict, session_id: str | None = None, timeout: int = 600) -> dict:
    arn = os.environ["AGENT_RUNTIME_ARN"]
    url = invocation_url(arn, os.environ.get("AGENT_RUNTIME_QUALIFIER", "DEFAULT"))
    # AgentCore wants a session id of at least 33 characters
    session = (session_id or f"chat-{uuid.uuid4().hex}").ljust(33, "0")
    req = urllib.request.Request(url, data=json.dumps(payload).encode(), method="POST", headers={
        "Authorization": f"Bearer {token}", "Content-Type": "application/json", "Accept": "application/json",
        "X-Amzn-Bedrock-AgentCore-Runtime-Session-Id": session})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            body = r.read()
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"agent {e.code}: {e.read()[:300].decode(errors='replace')}") from e
    out = json.loads(body)
    if isinstance(out, str):  # some runtimes return the result JSON-encoded twice
        out = json.loads(out)
    return out
