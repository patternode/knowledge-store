"""AgentCore Gateway REQUEST interceptor: carry the caller's scope into every tool call.

Gateway has already verified the caller's token (its JWT authorizer runs first), then calls this
function with the request, headers included. It reads the token's claims and writes one argument,
`caller_private`, into the tool call, overwriting whatever the model or the caller put there, so
the tools can serve private-scope content to exactly the callers entitled to it:

    a person       their Cognito access token carries cognito:groups; private if in PRIVATE_GROUP
    an application its client-credentials token carries scope; private if it holds <api>/tools.private

The tools trust only this argument, and only a real boolean true: a call that arrives without
the interceptor (a local run, a test) serves public-scope content.

The token's signature is not re-checked here because Gateway checked it; the claims are only
decoded. Standard library only. The claim names are configuration (knowledge_store.claims).
"""

from __future__ import annotations

import base64
import json

from ..claims import private_caller

ARG = "caller_private"


def claims_of(authorization: str | None) -> dict:
    if not authorization:
        return {}
    token = authorization.split(" ", 1)[1] if authorization.lower().startswith("bearer ") else authorization
    try:
        payload = token.split(".")[1]
        return json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))
    except (IndexError, ValueError):
        return {}


def is_private(claims: dict) -> bool:
    return private_caller(claims)


def lambda_handler(event, context):
    req = (event.get("mcp") or {}).get("gatewayRequest") or {}
    headers = {k.lower(): v for k, v in (req.get("headers") or {}).items()}
    body = req.get("body") or {}
    if isinstance(body, str):
        body = json.loads(body)
    if body.get("method") == "tools/call":
        params = body.setdefault("params", {})
        args = params.setdefault("arguments", {})
        args[ARG] = is_private(claims_of(headers.get("authorization")))
    return {"interceptorOutputVersion": "1.0",
            "mcp": {"transformedGatewayRequest": {"body": body}}}
