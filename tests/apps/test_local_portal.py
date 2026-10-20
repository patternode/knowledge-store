"""The local portal server (apps/local_portal.py) end to end over a swept lake: it serves the page
and the API on localhost, and refuses other hosts, other origins and non-JSON posts."""

from __future__ import annotations

import http.client
import json
import socket
import threading
import time

import pytest

from knowledge_store.apps import local_portal
from knowledge_store.apps import portal_api as handler
from test_review_fixes import mixed  # noqa: F401


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture
def server(mixed, tmp_path, monkeypatch):
    root, _ = mixed
    for name in ("_lake", "_state", "dispatch"):
        monkeypatch.setattr(handler, name, getattr(handler, name))
    portal = tmp_path / "portal"
    portal.mkdir()
    (portal / "index.html").write_text("<h1>portal</h1>")
    port = free_port()
    threading.Thread(target=local_portal.serve, args=(root.root if hasattr(root, "root") else str(tmp_path / "root"),
                                                       str(portal), port), daemon=True).start()
    for _ in range(100):
        try:
            socket.create_connection(("127.0.0.1", port), timeout=0.1).close()
            break
        except OSError:
            time.sleep(0.05)
    return port


def request(port, method, path, host=None, headers=None, body=None):
    c = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
    h = {"Host": host or f"localhost:{port}", **(headers or {})}
    c.request(method, path, body=body, headers=h)
    r = c.getresponse()
    return r.status, dict(r.getheaders()), r.read()


def test_the_page_and_its_config_are_served(server):
    status, _, body = request(server, "GET", "/")
    assert status == 200 and b"portal" in body
    status, _, body = request(server, "GET", "/config.json")
    assert json.loads(body) == {"mode": "local", "apiBase": "/api"}


def test_the_api_answers_as_a_private_reader(server):
    status, headers, body = request(server, "GET", "/api/status?c=m")
    data = json.loads(body)
    assert status == 200 and data["stage"] == "ready" and data["private"] is True
    assert not any(k.lower().startswith("access-control") for k in headers)


def test_a_file_outside_the_portal_is_not_served(server):
    assert request(server, "GET", "/../../etc/passwd")[0] == 404
    assert request(server, "GET", "/missing.js")[0] == 404


def test_another_host_is_refused(server):
    status, _, body = request(server, "GET", "/api/status", host="evil.example")
    assert status == 403 and json.loads(body)["error"] == "this server answers only on localhost"


def test_a_post_from_another_origin_or_not_json_is_refused(server):
    status, _, _ = request(server, "POST", "/api/chat", headers={"Origin": "https://evil.example",
                                                                 "Content-Type": "application/json"}, body=b"{}")
    assert status == 403
    status, _, body = request(server, "POST", "/api/chat", headers={"Content-Type": "text/plain"}, body=b"{}")
    assert status == 403 and "JSON" in json.loads(body)["error"]


def test_the_allowed_hosts_are_the_loopback_names_with_the_port():
    assert local_portal.allowed_hosts(1) == {"localhost:1", "127.0.0.1:1", "[::1]:1"}
