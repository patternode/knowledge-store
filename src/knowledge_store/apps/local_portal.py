"""Serve the portal and its API locally, over a local lake, without AWS sign-in.

    python -m knowledge_store.apps.local_portal --lake ./build/lake --portal ./portal [--port 8765]

Every caller is treated as a private-scope user, so the server listens on 127.0.0.1 only and
answers only requests addressed to it by a loopback name (a Host of localhost, 127.0.0.1 or [::1]
with its port: DNS rebinding is refused), sends no CORS header (other websites cannot read its
replies), and refuses a POST whose Origin is another site's. Chat needs model access (LLM_PROVIDER
and credentials); everything else reads the projection only. Answers are kept in memory.
"""

from __future__ import annotations

import argparse
import json
import mimetypes
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from knowledge_store.access.adapters import portal as handler
from knowledge_store.platform_services.adapters.store import LocalStore
from knowledge_store.access.adapters.state import MemoryState


class _Ctx:
    function_name = "local"


LOOPBACK = ("localhost", "127.0.0.1", "[::1]")


def allowed_hosts(port: int) -> set[str]:
    return {f"{h}:{port}" for h in LOOPBACK}


def refusal(method: str, host: str | None, origin: str | None, port: int, content_type: str | None = None) -> str | None:
    """Why a request to the local server is refused, or None. Its Host must name this server by a
    loopback name; a state-changing request with an Origin must come from one of those too, and
    must be JSON (a form or text/plain POST is what a page elsewhere can send without a preflight)."""
    hosts = allowed_hosts(port)
    if (host or "").strip().lower() not in hosts:
        return "this server answers only on localhost"
    if method not in ("GET", "HEAD", "OPTIONS") and origin is not None \
            and origin.strip().lower() not in {f"http://{h}" for h in hosts}:
        return "cross-origin requests are refused"
    if method not in ("GET", "HEAD", "OPTIONS") and not (content_type or "").lower().startswith("application/json"):
        return "send JSON (content-type application/json)"
    return None


def serve(lake_dir: str, portal_dir: str, port: int) -> None:
    handler._lake = LocalStore(lake_dir)
    handler._state = MemoryState()
    portal = Path(portal_dir).resolve()

    # questions are answered in a thread here, rather than by the Lambda invoking itself
    handler.dispatch = lambda job, _ctx: threading.Thread(target=handler.answer_job, args=(job,), daemon=True).start()

    class H(BaseHTTPRequestHandler):
        def _refused(self, method: str) -> bool:
            why = refusal(method, self.headers.get("host"), self.headers.get("origin"), port, self.headers.get("content-type"))
            if why:
                data = json.dumps({"error": why}).encode()
                self.send_response(403)
                self.send_header("content-type", "application/json")
                self.send_header("content-length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
            return bool(why)

        def _api(self, method: str):
            u = urlparse(self.path)
            length = int(self.headers.get("content-length") or 0)
            body = self.rfile.read(length).decode() if length else None
            event = {"rawPath": u.path, "requestContext": {"http": {"method": method},
                     "authorizer": {"jwt": {"claims": {"sub": "local", "cognito:groups": "[private-readers]"}}}},
                     "queryStringParameters": {k: v[0] for k, v in parse_qs(u.query).items()}, "body": body}
            res = handler.handler(event, _Ctx())
            self.send_response(res["statusCode"])
            for k, v in res["headers"].items():
                self.send_header(k, v)
            self.end_headers()
            self.wfile.write(res["body"].encode())

        def do_GET(self):
            if self._refused("GET"):
                return
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
            if self._refused("POST"):
                return
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
