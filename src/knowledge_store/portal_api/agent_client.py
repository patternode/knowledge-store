"""Ask the chat agent on AgentCore Runtime, as the person asking.

The Runtime authorises inbound calls with the person's own Cognito access token (OAuth bearer),
and the agent presents the same token to AgentCore Gateway, so every tool call runs in that
person's scope.

A person signed in through a host website (knowledge_store.site_grant) has no such token. For
them the portal asks as one of two service clients (OAuth client credentials): the public one,
whose token carries tools.public, or the private one, which also carries tools.private. The
Gateway scopes each tool call by those scopes as it would by a person's groups.

    AGENT_RUNTIME_ARN         the agent runtime
    AGENT_RUNTIME_QUALIFIER   the endpoint (default DEFAULT)
    SERVICE_CLIENTS_SECRET    a Secrets Manager secret: {"token_endpoint", "public": {"id", "secret"},
                              "private": {"id", "secret"}}, for sign-in through the website

Standard library and boto3 (in the Lambda runtime).
"""

from __future__ import annotations

import base64
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid


_clients: dict = {}
_tokens: dict[str, tuple[float, str]] = {}


def _service_clients() -> dict:
    if not _clients:
        import boto3
        _clients.update(json.loads(boto3.client("secretsmanager").get_secret_value(
            SecretId=os.environ["SERVICE_CLIENTS_SECRET"])["SecretString"]))
    return _clients


def service_token(private: bool, now: float | None = None) -> str:
    """An access token for the public or the private service client, reused until a minute
    before it expires."""
    which = "private" if private else "public"
    now = time.time() if now is None else now
    hit = _tokens.get(which)
    if hit and hit[0] - 60 > now:
        return hit[1]
    c = _service_clients()
    basic = base64.b64encode(f"{c[which]['id']}:{c[which]['secret']}".encode()).decode()
    req = urllib.request.Request(c["token_endpoint"], data=b"grant_type=client_credentials", method="POST", headers={
        "Authorization": f"Basic {basic}", "Content-Type": "application/x-www-form-urlencoded"})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            out = json.loads(r.read())
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"service sign-in {e.code}: {e.read()[:200].decode(errors='replace')}") from e
    _tokens[which] = (now + int(out.get("expires_in", 3600)), out["access_token"])
    return out["access_token"]


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
