"""Serve the portal and its API locally, over a local lake, without AWS sign-in.

    python -m knowledge_store.portal_api.local --lake ./build/lake --portal ./portal [--port 8765]

Every caller is treated as a private-scope user. Chat needs model access (LLM_PROVIDER and
credentials); everything else reads the projection only. Answers are kept in memory.
"""

from __future__ import annotations

import argparse
import json
import mimetypes
import threading
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from . import handler
from ..store import LocalStore
from .state import MemoryState


class _Ctx:
    function_name = "local"


def serve(lake_dir: str, portal_dir: str, port: int) -> None:
    handler._lake = LocalStore(lake_dir)
    handler._state = MemoryState()
    portal = Path(portal_dir).resolve()

    def run_job(job):
        threading.Thread(target=handler.answer_job, args=(job,), daemon=True).start()

    class H(BaseHTTPRequestHandler):
        def _api(self, method: str):
            u = urlparse(self.path)
            length = int(self.headers.get("content-length") or 0)
            body = self.rfile.read(length).decode() if length else None
            event = {"rawPath": u.path, "requestContext": {"http": {"method": method},
                     "authorizer": {"jwt": {"claims": {"sub": "local", "cognito:groups": "[private-readers]"}}}},
                     "queryStringParameters": {k: v[0] for k, v in parse_qs(u.query).items()}, "body": body}
            if method == "POST" and u.path == "/api/chat":
                q = json.loads(body or "{}")
                cid = (parse_qs(u.query).get("c") or [None])[0] or handler.collections.ids(handler.lake())[0]
                job = {"id": uuid.uuid4().hex, "sub": "local", "private": True, "question": q.get("question", ""),
                       "collection": cid,
                       "history": q.get("history") or []}
                handler.state().put_chat(job["id"], "local", {"status": "pending"})
                run_job(job)
                res = {"statusCode": 202, "headers": {"content-type": "application/json"}, "body": json.dumps({"id": job["id"]})}
            else:
                res = handler.handler(event, _Ctx())
            self.send_response(res["statusCode"])
            for k, v in res["headers"].items():
                self.send_header(k, v)
            self.send_header("access-control-allow-origin", "*")
            self.end_headers()
            self.wfile.write(res["body"].encode())

        def do_GET(self):
            if self.path.startswith("/api/"):
                return self._api("GET")
            rel = urlparse(self.path).path.lstrip("/") or "index.html"
            if rel == "config.json":
                data = json.dumps({"mode": "local", "apiBase": "/api"}).encode()
            else:
                f = (portal / rel).resolve()
                if portal not in f.parents or not f.is_file():
                    self.send_error(404)
                    return
                data = f.read_bytes()
            self.send_response(200)
            self.send_header("content-type", mimetypes.guess_type(rel)[0] or "application/octet-stream")
            self.end_headers()
            self.wfile.write(data)

        def do_POST(self):
            return self._api("POST")

        def log_message(self, *a):
            pass

    print(f"portal on http://localhost:{port}/  (lake {lake_dir})")
    ThreadingHTTPServer(("127.0.0.1", port), H).serve_forever()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--lake", required=True)
    ap.add_argument("--portal", default=str(Path(__file__).resolve().parents[3] / "portal"))
    ap.add_argument("--port", type=int, default=8765)
    a = ap.parse_args()
    serve(a.lake, a.portal, a.port)


if __name__ == "__main__":
    main()
