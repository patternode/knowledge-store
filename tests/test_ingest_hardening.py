"""Ingest hardening: the http_urls fetcher stays on public https, parsers refuse oversized or
crafted input cheaply, and ontology names cannot inject into generated graph schemas."""

from __future__ import annotations

import io
import socket
import time
import urllib.request
from email.message import Message

import pytest

from knowledge_store.adapters import http_urls
from knowledge_store.adapters.base import SourceItem
from knowledge_store.config import SourceConfig
from knowledge_store.refine import UnsupportedFormat, parse

# --- http_urls -----------------------------------------------------------------------------------

ADDRS = {"example.com": "93.184.216.34", "internal.example": "10.0.0.5", "meta.example": "169.254.169.254",
         "v6loop.example": "::1", "mapped.example": "::ffff:127.0.0.1", "zero.example": "0.0.0.0",
         "multi.example": "239.1.1.1"}


@pytest.fixture
def dns(monkeypatch):
    def fake(host, port, *a, **k):
        ip = ADDRS.get(host) or (host if host.replace(".", "").isdigit() or ":" in host else None)
        if ip is None:
            raise socket.gaierror("no such host")
        fam = socket.AF_INET6 if ":" in ip else socket.AF_INET
        return [(fam, socket.SOCK_STREAM, 6, "", (ip, port))]
    monkeypatch.setattr(socket, "getaddrinfo", fake)


class _Resp(io.BytesIO):
    def __init__(self, body: bytes, url: str, code: int = 200, headers: dict | None = None):
        super().__init__(body)
        self.url, self.code, self.status, self.msg = url, code, code, "OK"
        self.headers = Message()
        for k, v in (headers or {}).items():
            self.headers[k] = v

    def info(self):
        return self.headers

    def geturl(self):
        return self.url


class _FakeHTTPS(urllib.request.HTTPSHandler):
    """Serves canned responses by URL instead of touching the network; redirects go through the
    opener's real redirect handler."""

    def __init__(self, routes: dict):
        super().__init__()
        self.routes, self.seen = routes, []

    def https_open(self, req):
        url = req.full_url
        self.seen.append(url)
        code, body, headers = self.routes[url]
        r = _Resp(body, url, code, headers)
        if code >= 300:
            return self.parent.error("https", req, r, code, "redirect", r.headers)
        return r


def adapter(routes: dict, **opts) -> tuple[http_urls.HttpUrlsAdapter, _FakeHTTPS]:
    a = http_urls.HttpUrlsAdapter(SourceConfig("web", "http_urls", {"urls": list(routes)[:1], "delay_s": 0, **opts}), None)
    h = _FakeHTTPS(routes)
    a._opener = urllib.request.build_opener(http_urls._CheckedRedirects, h)
    return a, h


def item(url):
    return SourceItem(key=url, version="", name="x.html", uri=url)


def test_public_https_page_fetched(dns):
    a, _ = adapter({"https://example.com/a": (200, b"<p>hello</p>", {})})
    assert a.fetch(item("https://example.com/a")) == b"<p>hello</p>"


def test_public_https_redirect_followed(dns):
    a, h = adapter({"https://example.com/a": (302, b"", {"Location": "https://example.com/b"}),
                    "https://example.com/b": (200, b"moved", {})})
    assert a.fetch(item("https://example.com/a")) == b"moved"
    assert h.seen == ["https://example.com/a", "https://example.com/b"]


@pytest.mark.parametrize("target", ["https://internal.example/x", "https://meta.example/latest/meta-data/",
                                    "https://v6loop.example/", "https://mapped.example/", "https://zero.example/",
                                    "https://multi.example/", "https://127.0.0.1/", "https://[::1]/"])
def test_redirect_to_private_address_blocked(dns, target):
    a, h = adapter({"https://example.com/a": (302, b"", {"Location": target})})
    with pytest.raises(ValueError, match="non-public"):
        a.fetch(item("https://example.com/a"))
    assert h.seen == ["https://example.com/a"]


@pytest.mark.parametrize("target", ["http://example.com/b", "ftp://example.com/b", "file:///etc/passwd"])
def test_redirect_off_https_blocked(dns, target):
    a, h = adapter({"https://example.com/a": (301, b"", {"Location": target})})
    with pytest.raises(Exception):
        a.fetch(item("https://example.com/a"))
    assert h.seen == ["https://example.com/a"]


def test_configured_url_to_private_host_blocked(dns):
    a, h = adapter({"https://internal.example/a": (200, b"secret", {})})
    with pytest.raises(ValueError, match="non-public"):
        a.fetch(item("https://internal.example/a"))
    assert h.seen == []


def test_non_https_url_rejected_at_config():
    with pytest.raises(ValueError, match="https"):
        http_urls.HttpUrlsAdapter(SourceConfig("web", "http_urls", {"urls": ["http://example.com/"]}), None)


def test_size_cap(dns):
    a, _ = adapter({"https://example.com/big": (200, b"x" * 1001, {})}, max_bytes=1000)
    with pytest.raises(ValueError, match="limit"):
        a.fetch(item("https://example.com/big"))
    a, _ = adapter({"https://example.com/ok": (200, b"x" * 1000, {})}, max_bytes=1000)
    assert len(a.fetch(item("https://example.com/ok"))) == 1000
    assert http_urls.HttpUrlsAdapter(SourceConfig("web", "http_urls", {"urls": []}), None).max_bytes == 50 * 2**20


# --- parsers -------------------------------------------------------------------------------------


def test_html_title_linear_on_crafted_input():
    t = time.monotonic()
    res = parse(b"<title" * 50000, ".html")
    assert time.monotonic() - t < 2
    assert res.parser == "html@1"


def test_html_title_still_extracted():
    res = parse(b"<html><head><TITLE lang=en>  Q3 \n results &amp; more </TITLE></head><body><p>Body text</p></body></html>", ".html")
    assert res.title == "Q3 results & more"
    assert "Q3" not in res.text and "Body text" in res.text
    assert parse(b"<p>First line here</p>", ".html").title == "First line here"


def test_size_caps_per_format(monkeypatch):
    from knowledge_store.refine import parsers
    monkeypatch.setattr(parsers, "MAX_BYTES", 100)
    monkeypatch.setitem(parsers.MAX_BYTES_BY_PARSER, parsers.parse_pdf, 200)
    with pytest.raises(UnsupportedFormat, match="limit"):
        parse(b"x" * 101, ".txt")
    with pytest.raises(UnsupportedFormat, match="limit"):
        parse(b"x" * 201, ".pdf")
    assert parse(b"x" * 100, ".txt").text == "x" * 100


def test_oversized_document_recorded_not_fatal(monkeypatch):
    from knowledge_store.pipeline.refine import refine_one
    from knowledge_store.refine import parsers
    monkeypatch.setattr(parsers, "MAX_BYTES", 10)

    class Lake:
        def get(self, key):
            return b"x" * 11
    row = refine_one(Lake(), {"doc_id": "d1", "content_key": "k", "ext": ".txt"})
    assert row["status"] == "unsupported" and "limit" in row["reason"]


# --- ontology renditions -------------------------------------------------------------------------

TTL = """@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
<http://ex.org/o> a owl:Ontology .
<http://ex.org/o#Company> a owl:Class .
<http://ex.org/o#%s> a %s ; rdfs:domain <http://ex.org/o#Company> .
"""


@pytest.mark.parametrize("kind", ["owl:Class", "owl:ObjectProperty", "owl:DatatypeProperty"])
@pytest.mark.parametrize("path", ["neo4j/schema.cypher", "age/schema.sql"])
def test_malicious_local_name_rejected(kind, path):
    from knowledge_store.ontology import model, renditions
    evil = "x');SELECT(drop_graph('g',true))--"
    spec = model.load(data=TTL % (evil, kind))
    if (path == "age/schema.sql") != (kind == "owl:ObjectProperty"):
        assert evil not in renditions.render_schema(spec, path)  # AGE names only relations, Cypher only the rest
        return
    with pytest.raises(ValueError, match="plain identifier"):
        renditions.render_schema(spec, path)


def test_plain_names_render_on_loader_labels():
    from knowledge_store.ontology import model, renditions
    spec = model.load(data=TTL % ("launchedBy", "owl:ObjectProperty") + "<http://ex.org/o#revenue> a owl:DatatypeProperty ; "
                                                                      "rdfs:domain <http://ex.org/o#Company> .\n")
    cy = renditions.render_schema(spec, "neo4j/schema.cypher")
    assert "CREATE INDEX company_name IF NOT EXISTS FOR (n:Company) ON (n.name);" in cy
    assert "CREATE INDEX company_revenue IF NOT EXISTS FOR (n:Company) ON (n.revenue);" in cy
    sql = renditions.render_schema(spec, "age/schema.sql")
    assert "SELECT create_elabel('{graph}', 'LAUNCHED_BY');" in sql
