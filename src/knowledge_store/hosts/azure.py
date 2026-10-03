"""Azure glue: what the Function App's functions and the pipeline job do, kept apart from the
azure.functions decorators (deploy/azure/function/function_app.py) so it can be tested without them.

    portal()   GET/POST /api/...  the portal API (portal_api/handler.py), after verifying the token
    mcp()      POST /mcp          the knowledge tools over MCP (tools/mcp.py), behind API Management
    answer()   the chat queue     the asynchronous half of POST /api/chat
    drain()    the upload queue   the pipeline job empties it before sweeping (the job runs because
                                  the queue had messages; the sweep reads the lake, not them)

Everything authenticates as its managed identity (DefaultAzureCredential, with AZURE_CLIENT_ID
naming the user-assigned identity). The queues are in the lake's storage account:

    LAKE_QUEUE_URL   https://<account>.queue.core.windows.net
    CHAT_QUEUE       default chat
    UPLOAD_QUEUE     default uploads
"""

from __future__ import annotations

import json
import logging
import os

from .. import authn
from ..portal_api import handler
from ..tools import mcp as mcp_server

log = logging.getLogger("azure")

JSON = {"content-type": "application/json", "cache-control": "no-store"}


def _queue(name: str):
    from azure.identity import DefaultAzureCredential
    from azure.storage.queue import QueueClient
    return QueueClient(os.environ["LAKE_QUEUE_URL"], name, credential=DefaultAzureCredential())


def send_chat(job: dict, context=None) -> None:
    _queue(os.environ.get("CHAT_QUEUE", "chat")).send_message(json.dumps({"chat_job": job}))


def _claims(headers: dict) -> dict:
    return authn.verify(authn.bearer(headers.get("authorization")))


def _refuse(e: Exception) -> tuple[int, dict, str]:
    return 401, {**JSON, "www-authenticate": "Bearer"}, json.dumps({"error": str(e)[:200]})


def portal(method: str, path: str, query: dict, body: str | None, headers: dict) -> tuple[int, dict, str]:
    """headers with lower-case names. The event is the one API Gateway gives the Lambda."""
    try:
        claims = _claims(headers)
    except authn.Unauthorized as e:
        return _refuse(e)
    handler.dispatch = send_chat
    event = {"rawPath": path, "requestContext": {"http": {"method": method}, "authorizer": {"jwt": {"claims": claims}}},
             "queryStringParameters": query, "body": body}
    res = handler.handler(event, None)
    return res["statusCode"], res["headers"], res["body"]


def mcp(method: str, body: str | None, headers: dict) -> tuple[int, dict, str]:
    if method != "POST":
        return 405, {**JSON, "allow": "POST"}, json.dumps({"error": "this server answers POST only"})
    try:
        claims = _claims(headers)
    except authn.Unauthorized as e:
        return _refuse(e)
    try:
        message = json.loads(body or "")
    except ValueError:
        return 400, JSON, json.dumps({"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "parse error"}})
    out = mcp_server.handle(message, claims, handler.lake())
    if out is None:
        return 202, {}, ""
    return 200, JSON, json.dumps(out, default=str)


def answer(text: str) -> None:
    try:
        job = json.loads(text)["chat_job"]
    except (ValueError, KeyError, TypeError):
        log.error("dropped a chat message that is not a job")
        return
    handler.answer_job(job)


def drain(queue: str | None = None, limit: int = 10000) -> int:
    """Delete the upload notifications that started this run; the sweep finds the uploads itself."""
    q = _queue(queue or os.environ.get("UPLOAD_QUEUE", "uploads"))
    n = 0
    for m in q.receive_messages(messages_per_page=32, visibility_timeout=300):
        q.delete_message(m)
        n += 1
        if n >= limit:
            break
    return n
