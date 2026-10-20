"""The knowledge graph's read tools: one implementation for every surface that asks.

The portal's fallback chat, the in-process agent and the Gateway's MCP tools all call run_tool,
so the tools cannot drift apart. Each tool reads the projection (an Index) and the mapped tables,
and filters by scope. A failure goes back to the caller as data.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from knowledge_store.knowledge_graph.adapters.index import Index

TOOLS = [
    {"name": "search_entities", "description": "Find entities by name, optionally of one type (subtypes included).",
     "input": {"query": {"type": "string"}, "type": {"type": ["string", "null"]}, "limit": {"type": "integer"}},
     "required": ["query"]},
    {"name": "list_entities", "description": "List the best-connected entities of a type.",
     "input": {"type": {"type": "string"}, "limit": {"type": "integer"}}, "required": ["type"]},
    {"name": "get_entity", "description": "An entity's types, names, attributes and relations, each with the passages it is stated in.",
     "input": {"id": {"type": "string"}}, "required": ["id"]},
    {"name": "search_passages", "description": "Keyword search over the source passages; returns text with passage ids.",
     "input": {"query": {"type": "string"}, "limit": {"type": "integer"}}, "required": ["query"]},
    {"name": "read_passages", "description": "The full text of passages by id.",
     "input": {"ids": {"type": "array", "items": {"type": "string"}}}, "required": ["ids"]},
    {"name": "describe_structured", "description": "The mapped tables and named metrics, with the snapshot each is bound to.",
     "input": {}, "required": []},
    {"name": "lookup_rows", "description": "Rows of one mapped type. filters are {attribute, op, value}; op is eq, neq, lt, lte, gt, gte or prefix. Each value has its cell id.",
     "input": {"type": {"type": "string"}, "filters": {"type": "array", "items": {"$ref": "#/$defs/filter"}},
               "limit": {"type": "integer"}},
     "required": ["type"]},
    {"name": "aggregate", "description": "A figure: a metric name, or type plus op (count, sum, min, max, avg), an attribute, an optional group_by and filters.",
     "input": {"metric": {"type": "string"}, "type": {"type": "string"}, "op": {"type": "string"},
               "attribute": {"type": "string"}, "group_by": {"type": "string"},
               "filters": {"type": "array", "items": {"$ref": "#/$defs/filter"}}},
     "required": []},
]

FILTER = {"type": "object", "properties": {"attribute": {"type": "string"}, "op": {"type": "string"},
                                           "value": {"type": "string"}}, "required": ["attribute", "value"]}


def tool_config() -> dict:
    def schema(t):
        props = json.loads(json.dumps(t["input"]).replace('{"$ref": "#/$defs/filter"}', json.dumps(FILTER)))
        return {"type": "object", "properties": props, "required": t["required"]}
    return {"tools": [{"toolSpec": {"name": t["name"], "description": t["description"],
                                    "inputSchema": {"json": schema(t)}}} for t in TOOLS]}


def vocabulary(idx: Index, private: bool = False) -> str:
    o = idx.ontology_view(private)
    lines = []
    for c in o["classes"]:
        par = f" (a kind of {', '.join(c['parents'])})" if c["parents"] else ""
        lines.append(f"- type {c['name']}{par}: {c['definition']} [{c['count']} in graph]")
    for r in o["relations"]:
        lines.append(f"- relation {r['name']}: {'|'.join(r['domain']) or 'any'} -> {'|'.join(r['range']) or 'any'}: {r['definition']}")
    for a in o["attributes"]:
        lines.append(f"- attribute {a['name']} of {'|'.join(a['domain']) or 'any'} ({a['datatype']}): {a['definition']}")
    return "\n".join(lines)


def profile_text(idx: Index) -> str:
    p = idx.summary["profile"]
    s = f"Collection: {p['name']}\n{p['description']}"
    if p.get("key_terms"):
        s += "\nKey terms: " + ", ".join(p["key_terms"])
    return s


def run_tool(idx: Index, name: str, args: dict, private: bool) -> dict:
    """One tool call. A failure goes back to the model as data, as the Gateway's tools do, so one
    malformed argument costs a tool call rather than the whole answer."""
    try:
        return _run_tool(idx, name, args if isinstance(args, dict) else {}, private)
    except Exception as e:  # noqa: BLE001
        return {"error": f"{name} failed: {type(e).__name__}: {str(e)[:200]}"}


def _limit(value, default: int, top: int) -> int:
    try:
        return max(1, min(int(value or default), top))
    except (TypeError, ValueError):
        return default


def _run_tool(idx: Index, name: str, args: dict, private: bool) -> dict:
    if name == "search_entities":
        return idx.search_entities(args.get("query", ""), args.get("type"), private=private,
                                   limit=_limit(args.get("limit"), 15, 40))
    if name == "list_entities":
        return idx.search_entities("", args.get("type"), private=private, limit=_limit(args.get("limit"), 20, 50))
    if name == "get_entity":
        e = idx.entities.get(args.get("id", ""))
        if not e or not idx.visible(e, private):
            return {"error": f"no entity {args.get('id')!r}; use search_entities for its id"}
        v = idx.entity_view(e, private)
        label = {i: idx.entities[i]["label"] for r in v["out"] + v["in"] for i in (r.get("o"), r.get("s"))
                 if i in idx.entities and idx.visible(idx.entities[i], private)}
        return {**v, "out": [{**r, "o_label": label.get(r["o"])} for r in v["out"][:60]],
                "in": [{**r, "s_label": label.get(r["s"])} for r in v["in"][:60]], "passages": v["passages"][:30]}
    if name == "search_passages":
        return {"passages": idx.search_passages(args.get("query", ""), private=private,
                                                limit=_limit(args.get("limit"), 6, 12))}
    if name == "read_passages":
        out = [idx.passage_view(p) for p in (args.get("ids") or [])[:10]
               if p in idx.passages and idx.visible(idx.passages[p], private)]
        return {"passages": out}
    if name in ("describe_structured", "lookup_rows", "aggregate"):
        from knowledge_store.knowledge_graph import table_query as query
        if name == "describe_structured":
            return query.describe(idx.lake, private=private)
        if name == "lookup_rows":
            return query.lookup_rows(idx.lake, args.get("type") or "", args.get("filters") or [],
                                     limit=args.get("limit") or query.ROW_CAP, private=private,
                                     cell_ids=args.get("cell_ids") or None)
        return query.aggregate(idx.lake, metric=args.get("metric") or "", type_name=args.get("type") or "",
                               op=args.get("op") or "", attribute=args.get("attribute") or "",
                               group_by=args.get("group_by") or "", filters=args.get("filters") or [], private=private)
    return {"error": f"unknown tool {name}"}
