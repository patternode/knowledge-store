"""AgentCore Gateway Lambda target: read-only, fixed tools over the projection.

Gateway calls this function with the tool's arguments as the event, and the tool's name in
context.client_context.custom["bedrockAgentCoreToolName"] as "<target>___<tool>".

Scope. Gateway checks the caller's token, then calls this function with its own IAM role, so the
caller's identity does not reach here directly. The REQUEST interceptor (tools/interceptor.py)
derives it from the verified token and writes `caller_private` into every call, overwriting any
value the model supplied; the Cedar policy on the Gateway checks the same claims before the call
reaches this function. Without the interceptor (a local run, a test) the argument is absent and
the tools serve public-scope content only.

There is deliberately no free-form query tool (SPARQL or Cypher): on a shared endpoint it is cheap
to misuse and hard to scope.

Standard library and boto3 only, so Terraform packages it from source like the portal API.
"""

from __future__ import annotations

import json
import logging
import os

from .. import collections, layout
from ..config import load_profile
from ..portal_api import chat, index
from ..store import S3Store

log = logging.getLogger()
log.setLevel(logging.INFO)

# name -> (description, JSON Schema properties, required). Written to the Gateway's tool schema by
# Terraform (infra/modules/agent) from tool_schema(), so the two cannot disagree.
TOOLS = {
    "list_collections": ("The collections (corpora) in this deployment, each with its own ontology.", {}, []),
    "describe_ontology": ("The released ontology of a collection, as its compact agent rendition: types, relations, "
                          "attributes and synonyms. Read it before querying a collection.",
                          {"collection": {"type": "string"}}, ["collection"]),
    "search_entities": ("Find entities by name, optionally of one type (subtypes included).",
                        {"collection": {"type": "string"}, "query": {"type": "string"},
                         "type": {"type": "string"}, "limit": {"type": "integer"}}, ["collection", "query"]),
    "list_entities": ("The best-connected entities of a type.",
                      {"collection": {"type": "string"}, "type": {"type": "string"}, "limit": {"type": "integer"}},
                      ["collection", "type"]),
    "get_entity": ("An entity's types, names, attributes and relations, each with the passages it is stated in.",
                   {"collection": {"type": "string"}, "id": {"type": "string"}}, ["collection", "id"]),
    "neighbourhood": ("The entities within 1 to 3 relations of one entity (default 1), nearest and best connected "
                      "first, and the relations among them.",
                      {"collection": {"type": "string"}, "id": {"type": "string"}, "hops": {"type": "integer"},
                       "limit": {"type": "integer"}},
                      ["collection", "id"]),
    "find_paths": ("How two entities are connected: every shortest chain of relations between them, up to max_hops "
                   "(1 to 4, default 3) long, each relation with its direction. Cite the passages of each relation "
                   "(get_entity) before stating it.",
                   {"collection": {"type": "string"}, "from": {"type": "string"}, "to": {"type": "string"},
                    "max_hops": {"type": "integer"}, "limit": {"type": "integer"}},
                   ["collection", "from", "to"]),
    "search_passages": ("Keyword search over the source passages; returns text with passage ids.",
                        {"collection": {"type": "string"}, "query": {"type": "string"}, "limit": {"type": "integer"}},
                        ["collection", "query"]),
    "read_passages": ("The full text of passages by id, with the title of the document each comes from.",
                      {"collection": {"type": "string"}, "ids": {"type": "array", "items": {"type": "string"}}},
                      ["collection", "ids"]),
}


CALLER_ARG = {"caller_private": {"type": "boolean",
                                 "description": "set by the gateway from the caller's token; any value you send is replaced"}}


def tool_schema() -> list[dict]:
    """The Gateway's tool schema. caller_private is declared so the Cedar policy can refer to it
    (a policy may only name declared inputs); the interceptor always sets it."""
    return [{"name": n, "description": d,
             "inputSchema": {"type": "object", "properties": {**p, **CALLER_ARG}, "required": r}}
            for n, (d, p, r) in TOOLS.items()]


_lake = None


def lake():
    global _lake
    if _lake is None:
        _lake = S3Store(os.environ["LAKE_BUCKET"])
    return _lake


def call(root, name: str, args: dict) -> dict:
    private = args.pop("caller_private", False) is True
    if name == "list_collections":
        out = []
        for cid in collections.ids(root):
            s = collections.scoped(root, cid)
            p = load_profile(s)
            active = json.loads(s.get(layout.ONTOLOGY_ACTIVE))["version"] if s.exists(layout.ONTOLOGY_ACTIVE) else None
            out.append({"id": cid, "name": p.name, "description": p.description, "ontology_version": active})
        return {"collections": out}
    cid = args.get("collection") or ""
    if cid not in collections.ids(root):
        return {"error": f"no collection {cid!r}; call list_collections"}
    store = collections.scoped(root, cid)
    if name == "describe_ontology":
        if not store.exists(layout.ONTOLOGY_ACTIVE):
            return {"error": f"collection {cid!r} has no released ontology yet"}
        v = json.loads(store.get(layout.ONTOLOGY_ACTIVE))["version"]
        key = f"{layout.ontology_version_prefix(v)}/renditions/agent/ontology.md"
        return {"collection": cid, "version": v, "ontology": store.get(key).decode()}
    idx = index.load(store, cid)
    if idx is None:
        return {"error": f"collection {cid!r} has no knowledge graph yet"}
    if name == "neighbourhood":
        return idx.neighbourhood(args.get("id") or "", hops=int(args.get("hops") or 1), private=private,
                                 limit=min(int(args.get("limit") or 40), 100))
    if name == "find_paths":
        return idx.paths(args.get("from") or "", args.get("to") or "", max_hops=int(args.get("max_hops") or 3),
                         private=private, limit=int(args.get("limit") or 10))
    return {"ontology_version": idx.version, **chat.run_tool(idx, name, args, private=private)}


def tool_name(context) -> str:
    try:
        full = context.client_context.custom["bedrockAgentCoreToolName"]
    except (AttributeError, KeyError, TypeError):
        full = ""
    return full.split("___", 1)[-1]


def lambda_handler(event, context):
    name = tool_name(context) or (event or {}).pop("__tool", "")
    if name not in TOOLS:
        return {"error": f"unknown tool {name!r}"}
    try:
        out = call(lake(), name, event or {})
    except Exception as e:  # a tool error goes back to the agent as data, not a failed invocation
        log.exception("tool %s failed", name)
        out = {"error": str(e)[:300]}
    log.info(json.dumps({"tool": name, "collection": (event or {}).get("collection"), "error": out.get("error")}))
    return out
