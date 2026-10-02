"""The portal API Lambda.

    GET  /api/collections            the collections, with name, description and pipeline stage
    GET  /api/status                 pipeline stage and counts (works before any ontology exists)
    GET  /api/summary                profile, versions, counts, top candidates
    GET  /api/ontology               the active ontology's terms, with counts
    GET  /api/entities?q=&type=&limit=&offset=
    GET  /api/entity?id=
    GET  /api/passage?id=
    GET  /api/graph?type=&focus=&limit=
    GET  /api/neighbourhood?id=&hops=&limit=
    GET  /api/paths?from=&to=&hops=&limit=
    GET  /api/drafts                 discovery and revision drafts awaiting curation
    POST /api/chat {question, history}   -> {id}; answered asynchronously
    GET  /api/chat?id=               -> {status, answer, citations, trace}

Every route but /api/collections takes ?c=<collection id> (default: the first collection).

API Gateway validates the Cognito JWT before the Lambda runs; the handler reads the caller's
id and groups from the claims (knowledge_store.claims). Members of the group named by
PRIVATE_GROUP see private-scope content. A question is limited per caller per day
(DAILY_QUESTIONS), counted with a conditional write in the chat state (state.py: DynamoDB, or
the MongoDB API on Azure and Google Cloud), so the limit holds across concurrent requests.

API Gateway gives an integration 30 seconds, less than a multi-step tool loop can take, so POST
/api/chat stores the question and invokes this function again asynchronously to answer it; the
page polls GET /api/chat.
"""

from __future__ import annotations

import datetime as dt
import json
import logging
import os
import uuid

from .. import collections, layout
from ..claims import private_reader, subject
from ..config import load_profile
from ..store import S3Store, store_from_uri
from . import chat, index, state as chat_state

log = logging.getLogger()
log.setLevel(logging.INFO)

_lake = None
_state = None


def lake():
    global _lake
    if _lake is None:
        _lake = store_from_uri(os.environ["LAKE_URI"]) if os.environ.get("LAKE_URI") else S3Store(os.environ["LAKE_BUCKET"])
    return _lake


def _invoke_self(job: dict, context) -> None:
    """On Lambda: answer asynchronously by invoking this function again."""
    import boto3
    boto3.client("lambda").invoke(FunctionName=context.function_name, InvocationType="Event",
                                  Payload=json.dumps({"chat_job": job}).encode())


# How a question is handed to the asynchronous half. Another host replaces it: on Azure a queue
# message that a queue-triggered function answers with answer_job().
dispatch = _invoke_self


def state() -> chat_state.ChatState:
    global _state
    if _state is None:
        _state = chat_state.from_env()
    return _state


def reply(status: int, body) -> dict:
    return {"statusCode": status, "headers": {"content-type": "application/json", "cache-control": "no-store"},
            "body": json.dumps(body, default=str)}


def caller(event: dict) -> tuple[str, bool]:
    claims = ((event.get("requestContext") or {}).get("authorizer") or {}).get("jwt", {}).get("claims", {})
    return subject(claims), private_reader(claims)


def _json(lake_, key, default=None):
    return json.loads(lake_.get(key)) if lake_.exists(key) else default


def take_quota(sub: str) -> bool:
    return state().take_quota(sub, dt.date.today().isoformat(), int(os.environ.get("DAILY_QUESTIONS", "30")))


def answer_job(job: dict) -> None:
    """The asynchronous half of POST /api/chat."""
    cid = job.get("collection", collections.DEFAULT_ID)
    idx = index.load(collections.scoped(lake(), cid), cid)
    try:
        if idx is None:
            raise RuntimeError("the knowledge graph is not built yet")
        out = chat.ask(idx, job["question"], job.get("history"), private=job["private"])
        item = {"status": "done", **out}
    except Exception as e:
        log.exception("chat failed")
        item = {"status": "failed", "error": str(e)[:500]}
    state().put_chat(job["id"], job["sub"], item)


def handler(event, context):
    if "chat_job" in event:  # self-invocation
        answer_job(event["chat_job"])
        return {"ok": True}
    method = event.get("requestContext", {}).get("http", {}).get("method", "GET")
    path = event.get("rawPath") or event.get("requestContext", {}).get("http", {}).get("path", "")
    path = path[len("/api"):] if path.startswith("/api") else path
    qs = event.get("queryStringParameters") or {}
    sub, private = caller(event)
    root = lake()
    try:
        cids = collections.ids(root)
        if path == "/collections":
            out = []
            for c in cids:
                s = collections.scoped(root, c)
                p = load_profile(s)
                st = _json(s, layout.STATUS, {"stage": "never_run"})
                out.append({"id": c, "name": p.name, "description": p.description, "stage": st.get("stage"),
                            "active_version": st.get("active_version")})
            return reply(200, {"collections": out, "private": private})
        cid = qs.get("c") or cids[0]
        if cid not in cids:
            return reply(404, {"error": f"no collection {cid!r}"})
        lk = collections.scoped(root, cid)
        if path == "/status":
            status = _json(lk, layout.STATUS, {"stage": "never_run"})
            return reply(200, {**status, "private": private})
        # Draft reports quote documents verbatim (discovery examples, candidate evidence), and a
        # sample can include private documents, so drafts are for private-scope readers (curators).
        if path in ("/drafts", "/draft") and not private:
            return reply(403, {"error": "Ontology drafts are shown to curators (the private-readers group)."})
        if path == "/drafts":
            out = []
            for key in lk.list(layout.ONTOLOGY_DRAFTS + "/"):
                if key.endswith("/report.json"):
                    r = json.loads(lk.get(key))
                    out.append({k: r.get(k) for k in ("draft_id", "kind", "counts", "stability_jaccard", "rejected",
                                                      "proposed_version", "diff", "required_bump", "base", "warning")}
                               | {"ontology_ttl_key": key.replace("report.json", "ontology.ttl")})
            return reply(200, {"drafts": sorted(out, key=lambda d: d["draft_id"], reverse=True)})
        if path == "/draft":
            key = f"{layout.ONTOLOGY_DRAFTS}/{qs.get('id', '')}/ontology.ttl"
            if not qs.get("id") or "/" in qs["id"] or not lk.exists(key):
                return reply(404, {"error": "no such draft"})
            return reply(200, {"id": qs["id"], "ttl": lk.get(key).decode()})
        if path == "/chat" and method == "GET":
            item = state().get_chat(qs.get("id", ""))
            if not item or item.get("sub") != sub:
                return reply(404, {"error": "no such question"})
            return reply(200, item["body"])
        idx = index.load(lk, cid)
        if idx is None:
            return reply(409, {"error": "The knowledge graph is not built yet.",
                               "status": _json(lk, layout.STATUS, {"stage": "never_run"})})
        if path == "/summary":
            return reply(200, idx.summary_view(private) | {"private": private})
        if path == "/ontology":
            return reply(200, idx.ontology)
        if path == "/entities":
            return reply(200, idx.search_entities(qs.get("q", ""), qs.get("type") or None, private=private,
                                                  limit=min(int(qs.get("limit", 50)), 200),
                                                  offset=int(qs.get("offset", 0))))
        if path == "/entity":
            e = idx.entities.get(qs.get("id", ""))
            if not e or not idx.visible(e, private):
                return reply(404, {"error": "no such entity"})
            v = idx.entity_view(e, private)
            refs = {i for r in v["out"] + v["in"] for i in (r.get("o"), r.get("s")) if i}
            return reply(200, {**v, "labels": {i: idx.entities[i]["label"] for i in refs if i in idx.entities},
                               "passage_text": {p: idx.passage_view(p) for p in v["passages"][:40]},
                               "doc_info": {d: idx.docs.get(d) for d in v["docs"]}})
        if path == "/passage":
            p = idx.passages.get(qs.get("id", ""))
            if not p or not idx.visible(p, private):
                return reply(404, {"error": "no such passage"})
            return reply(200, idx.passage_view(qs["id"]))
        if path == "/graph":
            return reply(200, idx.graph(qs.get("type") or None, private=private, focus=qs.get("focus") or None,
                                        limit=min(int(qs.get("limit", 150)), 400)))
        if path == "/neighbourhood":
            return reply(200, idx.neighbourhood(qs.get("id", ""), hops=int(qs.get("hops", 1)), private=private,
                                                limit=min(int(qs.get("limit", 150)), 200)))
        if path == "/paths":
            return reply(200, idx.paths(qs.get("from", ""), qs.get("to", ""), max_hops=int(qs.get("hops", 3)),
                                        private=private, limit=int(qs.get("limit", 10))))
        if path == "/chat" and method == "POST":
            body = json.loads(event.get("body") or "{}")
            q = str(body.get("question") or "").strip()
            if not q or len(q) > 2000:
                return reply(400, {"error": "ask a question of up to 2000 characters"})
            if not take_quota(sub):
                return reply(429, {"error": "You have reached today's question limit."})
            job = {"id": uuid.uuid4().hex, "sub": sub, "private": private, "question": q, "collection": cid,
                   "history": [h for h in (body.get("history") or [])[-6:] if isinstance(h, dict)]}
            state().put_chat(job["id"], sub, {"status": "pending"})
            dispatch(job, context)
            return reply(202, {"id": job["id"]})
        return reply(404, {"error": f"no route {method} {path}"})
    except Exception as e:
        log.exception("request failed")
        return reply(500, {"error": str(e)[:300]})
