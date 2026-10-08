"""Questions over the knowledge graph: a Converse tool loop against the projection.

The system prompt is built from the profile and the live ontology, so nothing here names a
domain. The tools read the index only (entities, their facts, and the passages they cite), and
every answer cites passage ids, which the portal turns into links to the source text.

The model call goes to Bedrock (boto3's bedrock-runtime) or, with LLM_PROVIDER=anthropic, to the
Anthropic Messages API over HTTPS with the request converted by knowledge_store.llm, so the
Lambda needs no SDK beyond boto3.
"""

from __future__ import annotations

import json
import os
import urllib.request

from .. import llm
from .index import Index

MAX_STEPS = 10
MAX_TOKENS = 2500

SYSTEM = """You answer questions about a document collection using its knowledge graph.

{profile}

The graph's ontology (types, relations and attributes):
{vocabulary}

Use the tools to find entities and their facts, and to search the source passages. Answer only from what
the tools return. Cite the passages behind each claim as [p:<passage id>]. If the graph and passages do not
answer the question, say so plainly and say what is missing (a type, a relation, or a document), which helps
the ontology improve. Be concise."""

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
]


def tool_config() -> dict:
    return {"tools": [{"toolSpec": {"name": t["name"], "description": t["description"],
                                    "inputSchema": {"json": {"type": "object", "properties": t["input"],
                                                             "required": t["required"]}}}} for t in TOOLS]}


def vocabulary(idx: Index) -> str:
    o = idx.ontology
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
    if name == "search_entities":
        return idx.search_entities(args.get("query", ""), args.get("type"), private=private,
                                   limit=min(int(args.get("limit") or 15), 40))
    if name == "list_entities":
        return idx.search_entities("", args.get("type"), private=private, limit=min(int(args.get("limit") or 20), 50))
    if name == "get_entity":
        e = idx.entities.get(args.get("id", ""))
        if not e or not idx.visible(e, private):
            return {"error": f"no entity {args.get('id')!r}; use search_entities for its id"}
        v = idx.entity_view(e, private)
        label = {i: idx.entities[i]["label"] for r in v["out"] + v["in"] for i in (r.get("o"), r.get("s")) if i in idx.entities}
        return {**v, "out": [{**r, "o_label": label.get(r["o"])} for r in v["out"][:60]],
                "in": [{**r, "s_label": label.get(r["s"])} for r in v["in"][:60]], "passages": v["passages"][:30]}
    if name == "search_passages":
        return {"passages": idx.search_passages(args.get("query", ""), private=private,
                                                limit=min(int(args.get("limit") or 6), 12))}
    if name == "read_passages":
        out = [idx.passage_view(p) for p in (args.get("ids") or [])[:10]
               if p in idx.passages and idx.visible(idx.passages[p], private)]
        return {"passages": out}
    return {"error": f"unknown tool {name}"}


class _Anthropic:
    """Converse over the Anthropic Messages API, with urllib (no SDK in the Lambda)."""

    def __init__(self, key: str):
        self.key = key

    def converse(self, **kw) -> dict:
        req = llm.to_messages_request(**kw)
        r = urllib.request.Request("https://api.anthropic.com/v1/messages", data=json.dumps(req).encode(),
                                   headers={"x-api-key": self.key, "anthropic-version": "2023-06-01",
                                            "content-type": "application/json"})
        with urllib.request.urlopen(r, timeout=120) as resp:
            m = json.loads(resp.read())
        content = []
        for b in m["content"]:
            if b["type"] == "text":
                content.append({"text": b["text"]})
            elif b["type"] == "tool_use":
                content.append({"toolUse": {"toolUseId": b["id"], "name": b["name"], "input": b["input"]}})
        u = m.get("usage", {})
        return {"output": {"message": {"role": "assistant", "content": content}},
                "stopReason": llm._STOP_REASONS.get(m.get("stop_reason"), "end_turn"),
                "usage": {"inputTokens": u.get("input_tokens", 0), "outputTokens": u.get("output_tokens", 0)}}


def client():
    p = llm.provider()
    if p == llm.ANTHROPIC:
        return _Anthropic(llm.api_key())
    import boto3
    from botocore.config import Config
    return boto3.client("bedrock-runtime", config=Config(read_timeout=120, retries={"max_attempts": 3}))


def ask(idx: Index, question: str, history: list[dict] | None, *, private: bool, model_id: str | None = None,
        brt=None) -> dict:
    brt = brt or client()
    model_id = model_id or os.environ.get("CHAT_MODEL_ID", "us.anthropic.claude-sonnet-5")
    system = [{"text": SYSTEM.format(profile=profile_text(idx), vocabulary=vocabulary(idx))},
              {"cachePoint": {"type": "default"}}]
    messages = []
    for turn in (history or [])[-6:]:
        if turn.get("q") and turn.get("a"):
            messages += [{"role": "user", "content": [{"text": turn["q"]}]},
                         {"role": "assistant", "content": [{"text": turn["a"]}]}]
    messages.append({"role": "user", "content": [{"text": question}]})
    trace, usage = [], {"inputTokens": 0, "outputTokens": 0}
    for _ in range(MAX_STEPS):
        resp = brt.converse(modelId=model_id, system=system, messages=messages, toolConfig=tool_config(),
                            inferenceConfig={"maxTokens": MAX_TOKENS})
        for k in usage:
            usage[k] += resp.get("usage", {}).get(k, 0)
        msg = resp["output"]["message"]
        messages.append(msg)
        uses = [b["toolUse"] for b in msg["content"] if "toolUse" in b]
        if not uses:
            answer = "".join(b.get("text", "") for b in msg["content"]).strip()
            return {"answer": answer, "citations": cited(idx, answer, private), "trace": trace, "usage": usage}
        results = []
        for tu in uses:
            out = run_tool(idx, tu["name"], tu.get("input") or {}, private)
            trace.append({"tool": tu["name"], "input": tu.get("input")})
            results.append({"toolResult": {"toolUseId": tu["toolUseId"],
                                           "content": [{"text": json.dumps(out, default=str)[:30000]}]}})
        messages.append({"role": "user", "content": results})
    return {"answer": "I ran out of steps before finding an answer. Try a narrower question.",
            "citations": [], "trace": trace, "usage": usage}


def cited(idx: Index, answer: str, private: bool) -> list[dict]:
    import re
    ids = list(dict.fromkeys(re.findall(r"\[p:([^\]\s]+)\]", answer)))
    return [idx.passage_view(p) for p in ids if p in idx.passages and idx.visible(idx.passages[p], private)]
