"""Answerers: Knowledge Store's agent in process, or its chat API as a signed-in person.

In process runs the same agent code against a lake with the tools in process
(answering's answer_locally): the graph from Neptune when NEPTUNE_ENDPOINT is set, else from
the projection; passages from the Knowledge Base when KNOWLEDGE_BASE_ID is set, else by keyword.
It calls the model with your credentials. Against the API, each question counts against that
person's daily quota.
"""

from __future__ import annotations

import json
import time
import urllib.parse
import urllib.request

from knowledge_store.evaluation.domain.sets import Question


class InProcessAnswerer:
    def __init__(self, lake_uri: str, collection: str, model_id: str | None):
        from knowledge_store.platform_services import store_from_uri
        self.root, self.collection, self.model_id = store_from_uri(lake_uri), collection, model_id

    def __call__(self, q: Question) -> dict:
        from knowledge_store.answering import answer_locally
        return answer_locally(self.root, self.collection, q.question, private=q.private, model_id=self.model_id)


class HttpAnswerer:
    def __init__(self, url: str, token: str, collection: str, timeout_s: int = 300, poll_s: float = 3):
        base = url.rstrip("/")
        # The token goes with every call: https, or plain http only to this machine (the local server).
        host = urllib.parse.urlsplit(base).hostname or ""
        if not (base.startswith("https://") or (base.startswith("http://") and host in ("localhost", "127.0.0.1", "::1"))):
            raise ValueError(f"the chat API must be an https:// URL (or http://localhost): {url!r}")
        self.base, self.token, self.collection, self.timeout_s, self.poll_s = base, token, collection, timeout_s, poll_s

    def _call(self, method: str, path: str, body: dict | None = None) -> dict:
        req = urllib.request.Request(self.base + path, method=method, data=json.dumps(body).encode() if body else None,
                                     headers={"Authorization": f"Bearer {self.token}", "content-type": "application/json"})
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read())

    def __call__(self, q: Question) -> dict:
        job = self._call("POST", f"/api/chat?c={self.collection}", {"question": q.question})
        deadline = time.monotonic() + self.timeout_s
        while time.monotonic() < deadline:
            time.sleep(self.poll_s)
            r = self._call("GET", f"/api/chat?c={self.collection}&id={job['id']}")
            if r.get("status") == "done":
                return r
            if r.get("status") == "failed":
                return {"error": r.get("error") or "failed", "abstained": True}
        return {"error": "timed out", "abstained": True}
