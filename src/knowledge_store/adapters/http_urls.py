"""A fixed list of web pages or files, fetched over HTTPS.

Options:
    urls        the URLs to fetch
    user_agent  sent with every request; many sites require a contact in it
    delay_s     pause between requests, default 1.0
    max_bytes   a response larger than this fails the item, default 50 MB

Only https is fetched, initially and across redirects, and only from hosts that resolve to public
addresses, so a listed page cannot redirect the fetcher onto the internal network.

The deployer is responsible for having the right to fetch and keep what they list here.
Many sites' terms forbid automated collection, whatever robots.txt says; check before adding
a URL. The adapter fetches each URL on every run (a page has no cheap version to compare), and
ingest then stores it only if its bytes changed.
"""

from __future__ import annotations

import ipaddress
import socket
import time
import urllib.parse
import urllib.request
from typing import ClassVar

from ..config import SourceConfig
from ..store import Store
from .base import SourceItem


MAX_BYTES = 50 * 2**20
_NAT64 = ipaddress.ip_network("64:ff9b::/96")


def _public(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    if isinstance(ip, ipaddress.IPv6Address):  # an IPv4 address carried inside IPv6 is judged as IPv4
        inner = ip.ipv4_mapped or ip.sixtofour or (ipaddress.IPv4Address(int(ip) & 0xFFFFFFFF) if ip in _NAT64 else None)
        if inner is not None:
            return _public(inner)
    return ip.is_global and not (ip.is_multicast or ip.is_private or ip.is_loopback or ip.is_link_local
                                 or ip.is_reserved or ip.is_unspecified)


def check_url(url: str) -> None:
    """Refuse a URL that is not https or whose host resolves to any non-public address. Best effort:
    the connection resolves the name again, so a host that changes its answer in between (DNS
    rebinding) is not caught here."""
    u = urllib.parse.urlsplit(url)
    if u.scheme != "https" or not u.hostname:
        raise ValueError(f"http_urls: {url!r} is not an https URL")
    try:
        infos = socket.getaddrinfo(u.hostname, u.port or 443, type=socket.SOCK_STREAM)
    except socket.gaierror as e:
        raise ValueError(f"http_urls: cannot resolve {u.hostname!r}: {e}") from e
    for info in infos:
        ip = ipaddress.ip_address(info[4][0].split("%", 1)[0])
        if not _public(ip):
            raise ValueError(f"http_urls: {u.hostname!r} resolves to non-public address {ip}")


class _CheckedRedirects(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        check_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


class HttpUrlsAdapter:
    type: ClassVar[str] = "http_urls"

    def __init__(self, source: SourceConfig, lake: Store):
        self.urls = list(source.options.get("urls") or [])
        self.user_agent = source.options.get("user_agent") or "knowledge-store/0.1"
        self.delay = float(source.options.get("delay_s", 1.0))
        self.max_bytes = int(source.options.get("max_bytes", MAX_BYTES))
        self._opener = urllib.request.build_opener(_CheckedRedirects)
        self._last = 0.0
        for u in self.urls:
            if not u.startswith("https://"):
                raise ValueError(f"http_urls: {u!r} is not an https URL")

    def items(self):
        for u in self.urls:
            name = u.rstrip("/").rsplit("/", 1)[-1] or "index.html"
            if "." not in name:
                name += ".html"
            # No cheap version for a web page: fetch every run and let ingest compare content.
            yield SourceItem(key=u, version="", name=name, uri=u)

    def fetch(self, item):
        wait = self.delay - (time.monotonic() - self._last)
        if wait > 0:
            time.sleep(wait)
        check_url(item.uri)
        req = urllib.request.Request(item.uri, headers={"User-Agent": self.user_agent})
        try:
            with self._opener.open(req, timeout=60) as r:
                body = r.read(self.max_bytes + 1)
        finally:
            self._last = time.monotonic()
        if len(body) > self.max_bytes:
            raise ValueError(f"http_urls: {item.uri} is over the {self.max_bytes}-byte limit")
        return body
