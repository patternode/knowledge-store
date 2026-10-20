"""Ingestion port contract: every SourceAdapter lists items cheaply and fetches their bytes.

Run against each adapter that works offline: local_dir over a folder, s3_landing over a local lake
and over moto's S3, and http_urls through a fake HTTPS handler (the adapter's opener is its
network boundary)."""

from __future__ import annotations

import io
import socket
import urllib.request
from email.message import Message

import pytest

from knowledge_store.ingestion.adapters import http_urls, registry
from knowledge_store.ingestion.adapters.local_dir import LocalDirAdapter
from knowledge_store.ingestion.adapters.s3_landing import S3LandingAdapter
from knowledge_store.ingestion.ports import SourceItem
from knowledge_store.ingestion.slices.ingest import ingest
from knowledge_store.platform_services import SourceConfig
from knowledge_store.platform_services.adapters.store import LocalStore

FILES = {"a.txt": b"alpha", "sub/b.md": b"# beta"}


class _Resp(io.BytesIO):
    def __init__(self, body, url):
        super().__init__(body)
        self.url, self.code, self.status, self.msg, self.headers = url, 200, 200, "OK", Message()

    def info(self):
        return self.headers

    def geturl(self):
        return self.url


class _FakeHTTPS(urllib.request.HTTPSHandler):
    def __init__(self, routes):
        super().__init__()
        self.routes = routes

    def https_open(self, req):
        return _Resp(self.routes[req.full_url], req.full_url)


def _local_dir(tmp_path, monkeypatch):
    root = tmp_path / "src"
    for k, v in FILES.items():
        (root / k).parent.mkdir(parents=True, exist_ok=True)
        (root / k).write_bytes(v)
    (root / ".hidden").write_bytes(b"no")
    return LocalDirAdapter(SourceConfig("s", "local_dir", {"path": str(root)}), None)


def _s3_landing_local(tmp_path, monkeypatch):
    lake = LocalStore(tmp_path / "lake")
    for k, v in FILES.items():
        lake.put("landing/" + k, v)
    lake.put("landing/.DS_Store", b"no")
    return S3LandingAdapter(SourceConfig("s", "s3_landing"), lake)


def _s3_landing_moto(tmp_path, monkeypatch):
    moto = pytest.importorskip("moto")
    boto3 = pytest.importorskip("boto3")
    for k in ("AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY"):
        monkeypatch.setenv(k, "test")
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")
    mock = moto.mock_aws()
    mock.start()
    s3 = boto3.client("s3")
    s3.create_bucket(Bucket="uploads")
    for k, v in FILES.items():
        s3.put_object(Bucket="uploads", Key="in/" + k, Body=v)
    a = S3LandingAdapter(SourceConfig("s", "s3_landing", {"bucket": "uploads", "prefix": "in/"}), None)
    a._stop = mock.stop
    return a


def _http_urls(tmp_path, monkeypatch):
    monkeypatch.setattr(socket, "getaddrinfo", lambda host, port, *a, **k: [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", port))])
    routes = {f"https://example.com/{k}": v for k, v in FILES.items()}
    a = http_urls.HttpUrlsAdapter(SourceConfig("s", "http_urls", {"urls": list(routes), "delay_s": 0}), None)
    a._opener = urllib.request.build_opener(http_urls._CheckedRedirects, _FakeHTTPS(routes))
    return a


ADAPTERS = {"local_dir": _local_dir, "s3_landing_local": _s3_landing_local, "s3_landing_moto": _s3_landing_moto,
            "http_urls": _http_urls}


@pytest.fixture(params=list(ADAPTERS))
def adapter(request, tmp_path, monkeypatch):
    a = ADAPTERS[request.param](tmp_path, monkeypatch)
    yield a
    getattr(a, "_stop", lambda: None)()


def test_it_has_a_registered_type(adapter):
    assert registry.registry()[adapter.type] is type(adapter)


def test_it_lists_every_item_and_no_hidden_file(adapter):
    items = list(adapter.items())
    assert all(isinstance(i, SourceItem) for i in items)
    assert sorted(i.name for i in items) == ["a.txt", "b.md"]


def test_item_keys_are_unique(adapter):
    keys = [i.key for i in adapter.items()]
    assert len(keys) == len(set(keys))


def test_it_fetches_each_items_bytes(adapter):
    got = sorted(adapter.fetch(i) for i in adapter.items())
    assert got == sorted(FILES.values())


def test_items_have_extensions_and_uris(adapter):
    for i in adapter.items():
        assert i.extension() in (".txt", ".md") and i.uri


def test_listing_twice_gives_the_same_versions(adapter):
    assert [(i.key, i.version) for i in adapter.items()] == [(i.key, i.version) for i in adapter.items()]


def test_ingest_stores_what_it_lists(adapter, tmp_path):
    stats, _ = ingest(LocalStore(tmp_path / "bronze-lake"), SourceConfig("s", adapter.type), adapter)
    assert stats.stored == len(FILES) and stats.failed == 0


# --- the parts of each adapter outside the shared contract ---------------------------------------


def test_s3_landing_honours_its_include_list(tmp_path, monkeypatch):
    lake = LocalStore(tmp_path)
    for k, v in FILES.items():
        lake.put("landing/" + k, v)
    a = S3LandingAdapter(SourceConfig("s", "s3_landing", {"include": [".MD"]}), lake)
    assert [i.name for i in a.items()] == ["b.md"]


def test_s3_landing_records_the_folder_as_metadata(tmp_path, monkeypatch):
    a = _s3_landing_local(tmp_path, monkeypatch)
    meta = {i.name: i.metadata for i in a.items()}
    assert meta == {"a.txt": {}, "b.md": {"folder": "sub"}}


def test_local_dir_honours_its_pattern(tmp_path, monkeypatch):
    a = _local_dir(tmp_path, monkeypatch)
    a.pattern = "*.txt"
    assert [i.key for i in a.items()] == ["a.txt"]


def test_http_urls_names_a_page_without_an_extension_as_html():
    a = http_urls.HttpUrlsAdapter(SourceConfig("s", "http_urls", {"urls": ["https://example.com/about"]}), None)
    assert [i.name for i in a.items()] == ["about.html"]


def test_http_urls_names_a_sites_root_page_as_html():
    a = http_urls.HttpUrlsAdapter(SourceConfig("s", "http_urls", {"urls": ["https://example.com/"]}), None)
    assert next(a.items()).extension() == ".html"


def test_http_urls_waits_between_requests(monkeypatch, tmp_path):
    a = _http_urls(tmp_path, monkeypatch)
    a.delay = 5.0
    slept = []
    monkeypatch.setattr(http_urls.time, "sleep", slept.append)
    for i in a.items():
        a.fetch(i)
    assert len(slept) == 1 and 0 < slept[0] <= 5.0


def test_http_urls_refuses_a_name_that_does_not_resolve(monkeypatch):
    def boom(*a, **k):
        raise socket.gaierror("nope")
    monkeypatch.setattr(socket, "getaddrinfo", boom)
    with pytest.raises(ValueError, match="cannot resolve"):
        http_urls.check_url("https://nowhere.invalid/")


@pytest.mark.parametrize("ip,public", [("93.184.216.34", True), ("10.1.2.3", False), ("2002:0a00:0001::", False),
                                       ("64:ff9b::0a00:0001", False), ("64:ff9b::5db8:d822", True),
                                       ("2606:4700::1111", True), ("fe80::1", False)])
def test_http_urls_judges_addresses_inside_ipv6_as_ipv4(ip, public):
    import ipaddress
    assert http_urls._public(ipaddress.ip_address(ip)) is public


def test_registry_refuses_an_unknown_type(tmp_path):
    with pytest.raises(ValueError, match="unknown adapter type 'nope'"):
        registry.build(SourceConfig("s", "nope"), LocalStore(tmp_path))


def test_registry_adds_types_from_entry_points(monkeypatch):
    class EP:
        name = "plugin"

        def load(self):
            return dict

    monkeypatch.setattr(registry, "entry_points", lambda group: [EP()] if group == "knowledge_store.adapters" else [])
    assert registry.registry()["plugin"] is dict


def test_ingest_source_builds_the_adapter_and_ingests_into_the_whole_lake(tmp_path, monkeypatch):
    root = tmp_path / "src"
    root.mkdir()
    (root / "a.txt").write_bytes(b"alpha")
    stats, rows = registry.ingest_source(LocalStore(tmp_path / "lake"), SourceConfig("s", "local_dir", {"path": str(root)}))
    assert stats.stored == 1 and rows[0]["status"] == "stored"
