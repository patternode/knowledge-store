"""Questions over the knowledge graph: a Converse tool loop against the projection.

The system prompt is built from the profile and the live ontology, so nothing here names a
domain. The tools read the index only (entities, their facts, and the passages they cite), and
every answer cites passage ids, which the portal turns into links to the source text.

The model call goes to Bedrock (boto3's bedrock-runtime) or, with LLM_PROVIDER=anthropic, to the
Anthropic Messages API over HTTPS with the request converted by knowledge_store.llm, so the
Lambda needs no SDK beyond boto3.

Each model call and tool call is recorded as a step, with the ontology terms it touched
(knowledge_store.workbench), and reported through on_step as it happens. analyse() is the same loop
as the workbench's analyst: it explores, then reports what it would take to answer a question.
"""

from __future__ import annotations

import json
import os
import urllib.request

from .. import llm, workbench
from .index import Index

MAX_STEPS = 10
MAX_TOKENS = 2500

SYSTEM = """You answer questions about a document collection using its knowledge graph.

{profile}

The graph's ontology (types, relations and attributes):
{vocabulary}

Use the tools to find entities and their facts, to look up mapped tables, and to search the source passages.
A filter or a total over a mapped table goes to aggregate or lookup_rows, and the claim cites the cell
(`c:...`) or the metric (`m:...`). Passage quotes remain the citation for anything extraction produced.
Answer only from what the tools return. Cite passages as [p:<passage id>], cells as [c:<cell id>] and
metrics as [m:<metric id>]. If the graph, the tables and the passages do not
answer the question, say so plainly and say what is missing (a type, a relation, a table, or a document), which helps
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
    {"name": "describe_structured", "description": "The mapped tables and named metrics, with the snapshot each is bound to.",
     "input": {}, "required": []},
    {"name": "lookup_rows", "description": "Rows of one mapped type. filters are {attribute, op, value}; op is eq, neq, lt, lte, gt, gte or prefix. Each value has its cell id.",
     "input": {"type": {"type": "string"}, "filters": {"type": "array"}, "limit": {"type": "integer"}},
     "required": ["type"]},
    {"name": "aggregate", "description": "A figure: a metric name, or type plus op (count, sum, min, max, avg), an attribute, an optional group_by and filters.",
     "input": {"metric": {"type": "string"}, "type": {"type": "string"}, "op": {"type": "string"},
               "attribute": {"type": "string"}, "group_by": {"type": "string"}, "filters": {"type": "array"}},
     "required": []},
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
    if name in ("describe_structured", "lookup_rows", "aggregate"):
        from ..structured import query
        if name == "describe_structured":
            return query.describe(idx.lake)
        if name == "lookup_rows":
            return query.lookup_rows(idx.lake, args.get("type") or "", args.get("filters") or [],
                                     limit=min(int(args.get("limit") or query.ROW_CAP), 100), private=private,
                                     cell_ids=args.get("cell_ids") or None)
        return query.aggregate(idx.lake, metric=args.get("metric") or "", type_name=args.get("type") or "",
                               op=args.get("op") or "", attribute=args.get("attribute") or "",
                               group_by=args.get("group_by") or "", filters=args.get("filters") or [], private=private)
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


def spend_provider() -> str:
    """Who to price the call as. Bedrock unless LLM_PROVIDER says anthropic. Unset stays Bedrock,
    which is how the portal is deployed, and does not raise the way llm.provider() does."""
    return "anthropic" if os.environ.get("LLM_PROVIDER", "").strip().lower() == "anthropic" else "bedrock"


def _blank_usage() -> dict:
    return dict.fromkeys(workbench.USAGE_KEYS, 0)


def _add_usage(total: dict, usage: dict | None) -> None:
    for k in total:
        total[k] += int((usage or {}).get(k) or 0)


def _priced(rec: workbench.Recorder, model_id: str, usage: dict, reported: bool) -> dict | None:
    """The question's price. `reported` is whether any model call sent a usage object. A call that
    omits usage is not priced as zero."""
    return workbench.query_cost(rec.steps, model_id=model_id, usage=usage if reported else None, provider=spend_provider())


def ask(idx: Index, question: str, history: list[dict] | None, *, private: bool, model_id: str | None = None,
        brt=None, on_step=None) -> dict:
    brt = brt or client()
    rec = workbench.Recorder(on_step)
    model_id = model_id or os.environ.get("CHAT_MODEL_ID", "us.anthropic.claude-sonnet-5")
    system = [{"text": SYSTEM.format(profile=profile_text(idx), vocabulary=vocabulary(idx))},
              {"cachePoint": {"type": "default"}}]
    messages = []
    for turn in (history or [])[-6:]:
        if turn.get("q") and turn.get("a"):
            messages += [{"role": "user", "content": [{"text": turn["q"]}]},
                         {"role": "assistant", "content": [{"text": turn["a"]}]}]
    messages.append({"role": "user", "content": [{"text": question}]})
    trace, usage, provider, reported = [], _blank_usage(), spend_provider(), False
    rec.step("tool", f"Read the ontology (version {idx.version})")
    for _ in range(MAX_STEPS):
        rec.model_call()
        resp = brt.converse(modelId=model_id, system=system, messages=messages, toolConfig=tool_config(),
                            inferenceConfig={"maxTokens": MAX_TOKENS})
        call_usage = resp.get("usage") or {}
        reported = reported or bool(call_usage)
        _add_usage(usage, call_usage)
        rec.price_model(call_usage, model_id, provider)
        msg = resp["output"]["message"]
        messages.append(msg)
        uses = [b["toolUse"] for b in msg["content"] if "toolUse" in b]
        if not uses:
            answer = "".join(b.get("text", "") for b in msg["content"]).strip()
            cites = cited(idx, answer, private)
            rec.cite([c["id"] for c in cites])
            rec.step("done", f"Answered, citing {len(cites)} passage{'s' if len(cites) != 1 else ''}")
            return {"answer": answer, "citations": cites, "trace": trace, "usage": usage, "ontology_version": idx.version,
                    "steps": rec.steps, "ontology_hits": rec.hits(), "cost": _priced(rec, model_id, usage, reported)}
        results = []
        for tu in uses:
            out = run_tool(idx, tu["name"], tu.get("input") or {}, private)
            trace.append({"tool": tu["name"], "input": tu.get("input")})
            rec.tool(tu["name"], tu.get("input"), out)
            results.append({"toolResult": {"toolUseId": tu["toolUseId"],
                                           "content": [{"text": json.dumps(out, default=str)[:30000]}]}})
        messages.append({"role": "user", "content": results})
    rec.step("error", "Ran out of steps before finding an answer")
    return {"answer": "I ran out of steps before finding an answer. Try a narrower question.",
            "citations": [], "trace": trace, "usage": usage, "steps": rec.steps, "ontology_hits": rec.hits(),
            "cost": _priced(rec, model_id, usage, reported)}


REPORT_TOOL = {"toolSpec": {"name": "submit_report", "description": "Submit the report. Call it once, when you are done exploring.",
                            "inputSchema": {"json": workbench.REPORT_SCHEMA}}}


def analyse(idx: Index, question: str, about: dict | None, *, private: bool, model_id: str | None = None,
            brt=None, on_step=None) -> dict:
    """The workbench's analyst over the projection: explore with the chat's tools, then report
    what it would take to answer the question, through the submit_report tool."""
    brt = brt or client()
    rec = workbench.Recorder(on_step)
    model_id = model_id or os.environ.get("CHAT_MODEL_ID", "us.anthropic.claude-sonnet-5")
    system = [{"text": workbench.ANALYST.format(collection=profile_text(idx), version=idx.version, ontology=vocabulary(idx))},
              {"cachePoint": {"type": "default"}}]
    messages = [{"role": "user", "content": [{"text": workbench.analyst_prompt(question, about)}]}]
    config = tool_config()
    config["tools"].append(REPORT_TOOL)
    usage, provider, reported = _blank_usage(), spend_provider(), False
    rec.step("tool", f"Read the ontology (version {idx.version})")
    # No forced tool choice: the newest models refuse it. Near the step limit the analyst is told to report.
    for i in range(MAX_STEPS + 2):
        rec.model_call()
        resp = brt.converse(modelId=model_id, system=system, messages=messages, inferenceConfig={"maxTokens": 4000},
                            toolConfig=config)
        call_usage = resp.get("usage") or {}
        reported = reported or bool(call_usage)
        _add_usage(usage, call_usage)
        rec.price_model(call_usage, model_id, provider)
        msg = resp["output"]["message"]
        messages.append(msg)
        uses = [b["toolUse"] for b in msg["content"] if "toolUse" in b]
        report = next((tu.get("input") for tu in uses if tu["name"] == "submit_report"), None)
        if report is not None:
            report = workbench.clean_report(report)
            o = report["ontology"]
            rec.step("done", f"Reported: {report['verdict'].replace('_', ' ')}",
                     f"{len(o['classes'])} classes, {len(o['relations'])} relations, {len(o['attributes'])} attributes proposed")
            return {"mode": "gaps", "report": report, "ontology_version": idx.version, "steps": rec.steps,
                    "ontology_hits": rec.hits(), "usage": usage, "cost": _priced(rec, model_id, usage, reported)}
        if not uses:
            messages.append({"role": "user", "content": [{"text": "Submit the report with submit_report."}]})
            continue
        results = []
        for tu in uses:
            out = run_tool(idx, tu["name"], tu.get("input") or {}, private)
            rec.tool(tu["name"], tu.get("input"), out)
            results.append({"toolResult": {"toolUseId": tu["toolUseId"],
                                           "content": [{"text": json.dumps(out, default=str)[:30000]}]}})
        if i >= MAX_STEPS - 1:
            results.append({"text": "Stop exploring now and submit the report with submit_report."})
        messages.append({"role": "user", "content": results})
    rec.step("error", "The analyst did not submit a report")
    return {"error": "The analyst did not submit a report. Try again, or ask a narrower question.", "steps": rec.steps,
            "usage": usage, "cost": _priced(rec, model_id, usage, reported)}


def cited(idx: Index, answer: str, private: bool) -> list[dict]:
    """The sources an answer named. A passage is [p:<id>]. A cell is [c:<cell id>], and the cell
    id already begins with c:, so the marker is [c:c:...]. A metric is [m:<metric id>] the same way."""
    import re
    out = []
    seen = set()
    for kind, rest in re.findall(r"\[([pcm]):([^\]\s]+)\]", answer):
        if kind == "p":
            ident = rest
        else:
            ident = rest if rest.startswith(f"{kind}:") else f"{kind}:{rest}"
        if ident in seen:
            continue
        seen.add(ident)
        if kind == "p":
            if ident in idx.passages and idx.visible(idx.passages[ident], private):
                out.append(idx.passage_view(ident))
        elif kind == "c":
            from ..structured import query
            found = query.lookup_rows(idx.lake, "", cell_ids=[ident], private=private).get("cells") or []
            if not found:
                continue
            cell = found[0]
            out.append({"id": ident, "kind": "cell", "name": cell.get("table"),
                        "title": f"{cell.get('column')} = {cell.get('value')}",
                        "text": f"{cell.get('column')}: {cell.get('value')}",
                        "quotes": [str(cell.get("value"))], "row": cell.get("row") or []})
        else:
            out.append({"id": ident, "kind": "metric", "title": ident, "text": "", "quotes": []})
    return out
