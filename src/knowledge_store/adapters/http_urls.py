"""A fixed list of web pages or files, fetched over HTTPS.

Options:
    urls        the URLs to fetch
    user_agent  sent with every request; many sites require a contact in it
    delay_s     pause between requests, default 1.0

The deployer is responsible for having the right to fetch and keep what they list here.
Many sites' terms forbid automated collection, whatever robots.txt says; check before adding
a URL. The adapter fetches each URL on every run (a page has no cheap version to compare), and
ingest then stores it only if its bytes changed.
"""

from __future__ import annotations

import time
import urllib.request
from typing import ClassVar

from ..config import SourceConfig
from ..store import Store
from .base import SourceItem


class HttpUrlsAdapter:
    type: ClassVar[str] = "http_urls"

    def __init__(self, source: SourceConfig, lake: Store):
        self.urls = list(source.options.get("urls") or [])
        self.user_agent = source.options.get("user_agent") or "knowledge-store/0.1"
        self.delay = float(source.options.get("delay_s", 1.0))
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
        req = urllib.request.Request(item.uri, headers={"User-Agent": self.user_agent})
        with urllib.request.urlopen(req, timeout=60) as r:
            body = r.read()
        self._last = time.monotonic()
        return body
