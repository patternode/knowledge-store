"""AgentCore Gateway Lambda targets: read-only, fixed tools over the knowledge graph and passages.

Gateway calls this function with the tool's arguments as the event, and the tool's name in
context.client_context.custom["bedrockAgentCoreToolName"] as "<target>___<tool>".

Two toolsets, one per Lambda (TOOLSET), because they need different networks:

    graph      list_collections, describe_ontology, search_entities, list_entities, get_entity,
               neighbourhood, find_paths, describe_structured, lookup_rows, aggregate. With
               NEPTUNE_ENDPOINT set the entity tools query Neptune
               (graph/sparql.py), so this Lambda runs in the VPC beside it, with no route out.
    passages   search_passages, read_passages. Search goes to the Knowledge Base when
               KNOWLEDGE_BASE_ID is set (tools/passages.py), so this Lambda runs outside the VPC.

Without NEPTUNE_ENDPOINT the graph tools answer from the in-memory projection, and without
KNOWLEDGE_BASE_ID passage search is by keyword: the same tools for a local run, a test, or
another cloud. TOOLSET=all (the default) serves every tool from one function.

Scope. Gateway checks the caller's token, then calls this function with its own IAM role, so the
caller's identity does not reach here directly. The REQUEST interceptor (tools/interceptor.py)
derives it from the verified token and writes `caller_private` into every call, overwriting any
value the model supplied. Without the interceptor (a local run, a test) the argument is absent and
the tools serve public-scope content only.

There is deliberately no free-form query tool (SPARQL or Cypher): on a shared endpoint it is cheap
to misuse and hard to scope. The SPARQL behind each tool is fixed and built from the ontology.

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
from . import passages

log = logging.getLogger()
log.setLevel(logging.INFO)

# name -> (description, JSON Schema properties, required). Written to the Gateway's tool schemas by
# Terraform (infra/modules/agent) from tool_schema(), so the two cannot disagree.
TOOLS = {
    "list_collections": ("The collections (corpora) in this deployment, each with its own ontology.", {}, []),
    "describe_ontology": ("The released ontology of a collection, as its compact agent rendition: types, relations, "
                          "attributes and synonyms. Read it before querying a collection, and query in its terms.",
                          {"collection": {"type": "string"}}, ["collection"]),
    "search_entities": ("Find entities in the knowledge graph by name or synonym, optionally of one ontology type "
                        "(its subtypes included).",
                        {"collection": {"type": "string"}, "query": {"type": "string"},
                         "type": {"type": "string"}, "limit": {"type": "integer"}}, ["collection", "query"]),
    "list_entities": ("The best-connected entities of an ontology type (its subtypes included).",
                      {"collection": {"type": "string"}, "type": {"type": "string"}, "limit": {"type": "integer"}},
                      ["collection", "type"]),
    "get_entity": ("An entity's types, names, attributes and relations, each with the ids of the passages it is "
                   "stated in.",
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
    "search_passages": ("Search the source passages by what they say; returns each passage's text, id and document. "
                        "Use it for anything the graph does not hold, and to find the passage behind a fact.",
                        {"collection": {"type": "string"}, "query": {"type": "string"}, "limit": {"type": "integer"}},
                        ["collection", "query"]),
    "read_passages": ("The full text of passages by id, with the document each comes from. Read a passage before "
                      "citing it.",
                      {"collection": {"type": "string"}, "ids": {"type": "array", "items": {"type": "string"}}},
                      ["collection", "ids"]),
    "describe_structured": ("The mapped tables and named metrics of a collection: each type, its key, its columns, "
                            "its source and the snapshot it is bound to. Read it before a filter or a total.",
                            {"collection": {"type": "string"}}, ["collection"]),
    "lookup_rows": ("Rows of one mapped type. A filter is an attribute, an operator (eq, neq, lt, lte, gt, gte, prefix) "
                    "and a value. Each value comes back with its cell id. Pass cell_ids to re-read cells for a citation check.",
                    {"collection": {"type": "string"}, "type": {"type": "string"},
                     "filters": {"type": "array", "items": {"type": "object"}},
                     "limit": {"type": "integer"},
                     "cell_ids": {"type": "array", "items": {"type": "string"}}},
                    ["collection"]),
    "aggregate": ("A figure from a mapped table: a metric name, or a type with op (count, sum, min, max, avg), "
                  "an attribute, one optional group_by, and the same filters as lookup_rows. The figure is recomputed "
                  "from the snapshot.",
                  {"collection": {"type": "string"}, "metric": {"type": "string"}, "type": {"type": "string"},
                   "op": {"type": "string"}, "attribute": {"type": "string"}, "group_by": {"type": "string"},
                   "filters": {"type": "array", "items": {"type": "object"}}, "snapshot": {"type": "string"}},
                  ["collection"]),
}

TOOLSETS = {
    "graph": ["list_collections", "describe_ontology", "search_entities", "list_entities", "get_entity",
              "neighbourhood", "find_paths", "describe_structured", "lookup_rows", "aggregate"],
    "passages": ["search_passages", "read_passages"],
}
TOOLSETS["all"] = TOOLSETS["graph"] + TOOLSETS["passages"]

CALLER_ARG = {"caller_private": {"type": "boolean",
                                 "description": "set by the gateway from the caller's token; any value you send is replaced"}}


def tool_schema(toolset: str = "all") -> list[dict]:
    """A Gateway target's tool schema. caller_private is declared so that the interceptor's value
    is a declared input; the interceptor always sets it."""
    return [{"name": n, "description": TOOLS[n][0],
             "inputSchema": {"type": "object", "properties": {**TOOLS[n][1], **CALLER_ARG}, "required": TOOLS[n][2]}}
            for n in TOOLSETS[toolset]]


_lake = None


def lake():
    global _lake
    if _lake is None:
        _lake = S3Store(os.environ["LAKE_BUCKET"])
    return _lake


def graph_index(store, cid: str):
    """The collection's index: over Neptune when NEPTUNE_ENDPOINT is set, else in memory."""
    from ..graph import sparql
    client = sparql.client_from_env()
    return sparql.load(store, cid, client) if client else index.load(store, cid)


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
    if name in ("describe_structured", "lookup_rows", "aggregate"):
        from ..structured import query
        if name == "describe_structured":
            return query.describe(store)
        if name == "lookup_rows":
            return query.lookup_rows(store, args.get("type") or "", args.get("filters") or [],
                                     limit=int(args.get("limit") or query.ROW_CAP), private=private,
                                     cell_ids=args.get("cell_ids") or None)
        return query.aggregate(store, metric=args.get("metric") or "", type_name=args.get("type") or "",
                               op=args.get("op") or "", attribute=args.get("attribute") or "",
                               group_by=args.get("group_by") or "", filters=args.get("filters") or [],
                               private=private, snapshot=args.get("snapshot") or "")
    if name in TOOLSETS["passages"]:
        idx = index.load(store, cid)
        if name == "read_passages":
            return {"passages": passages.read(store, idx, args.get("ids") or [], private=private)}
        return passages.search(store, idx, cid, args.get("query", ""), private=private,
                               limit=min(int(args.get("limit") or 6), 12))
    idx = graph_index(store, cid)
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
    if name not in TOOLSETS[os.environ.get("TOOLSET", "all")]:
        return {"error": f"unknown tool {name!r}"}
    try:
        out = call(lake(), name, event or {})
    except Exception as e:  # a tool error goes back to the agent as data, not a failed invocation
        log.exception("tool %s failed", name)
        out = {"error": str(e)[:300]}
    log.info(json.dumps({"tool": name, "collection": (event or {}).get("collection"), "error": out.get("error")}))
    return out
