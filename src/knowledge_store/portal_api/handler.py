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
    GET  /api/document?doc=          a link to open a source document (its URL, or a short-lived link)
    POST /api/chat {question, history}   -> {id}; answered asynchronously
    GET  /api/chat?id=               -> {status, answer, citations, trace}

Every route but /api/collections takes ?c=<collection id> (default: the first collection).

API Gateway validates the Cognito JWT before the Lambda runs; the handler reads the caller's
id and groups from the claims (knowledge_store.claims). Members of the group named by
PRIVATE_GROUP see private-scope content. With SITE_GRANT_ISSUER set, people sign in on a host
website instead, which frames the portal: API Gateway lets requests through, and the handler
verifies the site's grant (header X-Site-Grant, knowledge_store.site_grant) on every request,
its roles deciding who may read and who may read private-scope content. A question is limited per caller per day
(DAILY_QUESTIONS), counted with a conditional write in the chat state (state.py: DynamoDB, or
MongoDB), so the limit holds across concurrent requests.

With AGENT_RUNTIME_ARN set, the question goes to the chat agent on AgentCore Runtime with the
person's own access token (agent_client.py), and the answer is the agent's: grounded claims with
their sources. A person signed in through the website has no token the agent accepts, so the
portal asks as one of its two service clients, the public or the private one, by the person's
access (agent_client.service_token). Without it, the portal's own tool loop answers (chat.py), as on other clouds.

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

from .. import collections, layout, site_grant
from ..claims import private_reader, subject
from ..config import load_profile
from ..store import S3Store, store_from_uri
from . import agent_client, chat, index, state as chat_state

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


# How a question is handed to the asynchronous half. Another host replaces it, for example with a
# queue message whose consumer answers it with answer_job().
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
    """Who is asking and whether they may read private-scope content. Refused (site_grant) when
    sign-in is through the website and the request carries no grant this lab accepts."""
    if site_grant.enabled():
        h = {k.lower(): v for k, v in (event.get("headers") or {}).items()}
        who = site_grant.caller((h.get("x-site-grant") or "").strip())
        return who["sub"], who["private"]
    claims = ((event.get("requestContext") or {}).get("authorizer") or {}).get("jwt", {}).get("claims", {})
    return subject(claims), private_reader(claims)


def bearer(event: dict) -> str:
    h = {k.lower(): v for k, v in (event.get("headers") or {}).items()}
    v = h.get("authorization", "")
    return v.split(" ", 1)[1] if v.lower().startswith("bearer ") else v


def document_link(lk, doc_id: str, private: bool) -> dict | None:
    """Where a person can open a source document: its own URL when it came from the web, else a
    short-lived link to the copy in the lake. None if there is no such document in their scope."""
    from ..pipeline.refine import load_doc
    if not doc_id or "/" in doc_id or not lk.exists(layout.doc_key(doc_id)):
        return None
    doc = load_doc(lk, doc_id)
    if not (private or doc.get("scope", "public") == "public"):
        return None
    out = {"doc": doc_id, "title": doc.get("title") or doc.get("name"), "name": doc.get("name")}
    uri = doc.get("source_uri") or ""
    if uri.startswith(("https://", "http://")):
        return {**out, "url": uri}
    meta_key = layout.bronze_meta_key(doc["source"], doc_id)
    root = getattr(lk, "whole", lk)
    if not lk.exists(meta_key) or not hasattr(root, "s3"):
        return out
    meta = json.loads(lk.get(meta_key))
    key = getattr(lk, "prefix", "") + layout.bronze_content_key(doc["source"], doc_id, meta.get("ext", ""))
    name = (doc.get("name") or doc_id).replace('"', "")
    url = root.s3.generate_presigned_url("get_object", ExpiresIn=600, Params={
        "Bucket": root.bucket, "Key": key, "ResponseContentDisposition": f'inline; filename="{name}"'})
    return {**out, "url": url}


def _json(lake_, key, default=None):
    return json.loads(lake_.get(key)) if lake_.exists(key) else default


def take_quota(sub: str) -> bool:
    return state().take_quota(sub, dt.date.today().isoformat(), int(os.environ.get("DAILY_QUESTIONS", "30")))


def answer_job(job: dict) -> None:
    """The asynchronous half of POST /api/chat: the chat agent on AgentCore Runtime, as the person
    asking, when AGENT_RUNTIME_ARN is set; otherwise the portal's own tool loop (chat.py)."""
    cid = job.get("collection", collections.DEFAULT_ID)
    try:
        if agent_client.configured():
            token = job.pop("token", "") or agent_client.service_token(job["private"])
            out = agent_client.ask(token, {"question": job["question"], "collection": cid,
                                           "history": job.get("history")})
            if out.get("error") and not out.get("answer"):
                raise RuntimeError(out["error"])
        else:
            idx = index.load(collections.scoped(lake(), cid), cid)
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
    try:
        sub, private = caller(event)
    except site_grant.Refused as e:
        return reply(e.status, {"error": str(e)})
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
        if path == "/document":
            link = document_link(lk, qs.get("doc", ""), private)
            return reply(200, link) if link else reply(404, {"error": "no such document"})
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
            if agent_client.configured() and not site_grant.enabled():
                job["token"] = bearer(event)  # the agent acts as this person: it gets their token, never stored
            state().put_chat(job["id"], sub, {"status": "pending"})
            dispatch(job, context)
            return reply(202, {"id": job["id"]})
        return reply(404, {"error": f"no route {method} {path}"})
    except Exception as e:
        log.exception("request failed")
        return reply(500, {"error": str(e)[:300]})
