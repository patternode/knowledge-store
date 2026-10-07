"""The knowledge tools as an MCP server over Streamable HTTP, for hosts with no MCP gateway of
their own (Azure Functions behind API Management, Cloud Run).

Stateless: every request is one JSON-RPC message answered with one JSON response, which the
Streamable HTTP transport allows, so no session or event stream is kept and any instance can
answer any request. The tools are the gateway's (tools/gateway.py), the same functions the
portal's chat uses.

Scope comes from the caller's verified token, never from the arguments: caller_private is
overwritten on every call, as the AgentCore interceptor does, and it is not in the listed schema.
"""

from __future__ import annotations

import json
import logging

from ..claims import private_caller
from . import gateway

log = logging.getLogger("mcp")

VERSIONS = ("2025-06-18", "2025-03-26", "2024-11-05")
SERVER = {"name": "knowledge-store", "version": "0.1.0"}


def tools() -> list[dict]:
    return [{"name": n, "description": d, "inputSchema": {"type": "object", "properties": p, "required": r}}
            for n, (d, p, r) in gateway.TOOLS.items()]


def _error(mid, code: int, message: str) -> dict:
    return {"jsonrpc": "2.0", "id": mid, "error": {"code": code, "message": message}}


def handle(message, claims: dict, lake) -> dict | None:
    """One JSON-RPC message in, its response out (None for a notification)."""
    if not isinstance(message, dict) or message.get("jsonrpc") != "2.0" or "method" not in message:
        return _error(None, -32600, "not a JSON-RPC 2.0 request")
    mid, method, params = message.get("id"), message["method"], message.get("params") or {}
    if "id" not in message:
        return None  # notifications (initialized, cancelled) need no answer
    if method == "initialize":
        asked = params.get("protocolVersion")
        return {"jsonrpc": "2.0", "id": mid, "result": {
            "protocolVersion": asked if asked in VERSIONS else VERSIONS[0],
            "capabilities": {"tools": {"listChanged": False}}, "serverInfo": SERVER,
            "instructions": "Call list_collections, then describe_ontology for a collection, before other tools. "
                            "Cite the passage ids of every fact you report."}}
    if method == "ping":
        return {"jsonrpc": "2.0", "id": mid, "result": {}}
    if method == "tools/list":
        return {"jsonrpc": "2.0", "id": mid, "result": {"tools": tools()}}
    if method == "tools/call":
        name = params.get("name")
        if name not in gateway.TOOLS:
            return _error(mid, -32602, f"unknown tool {name!r}")
        args = dict(params.get("arguments") or {})
        args["caller_private"] = private_caller(claims)
        try:
            out = gateway.call(lake, name, args)
        except Exception as e:  # a tool error goes back to the agent as data
            log.exception("tool %s failed", name)
            out = {"error": str(e)[:300]}
        log.info(json.dumps({"tool": name, "collection": args.get("collection"), "error": out.get("error")}))
        return {"jsonrpc": "2.0", "id": mid, "result": {
            "content": [{"type": "text", "text": json.dumps(out, default=str)}],
            "structuredContent": out, "isError": "error" in out}}
    return _error(mid, -32601, f"no method {method!r}")
