"""Links, email domains and UUIDs."""

from __future__ import annotations

import re
from urllib.parse import urlsplit, urlunsplit

from knowledge_store.ingestion.domain.conform.log import _overlaps

_URL = re.compile(r"https?://[^\s<>\[\]\"']+", re.IGNORECASE)

_EMAIL = re.compile(
    r"(?<![\w.+-])([\w.+-]+)@((?:[A-Za-z0-9-]+\.)+[A-Za-z]{2,})\b")

_UUID = re.compile(
    r"(?<![\w-])((?:urn:uuid:)?)(\{?)([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-"
    r"[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})(\}?)(?![\w-])",
    re.IGNORECASE)

def _identifiers(text: str, found: list) -> None:
    for matched in _URL.finditer(text):
        raw = matched.group()
        core = raw
        while core and core[-1] in ".,;:!?":
            core = core[:-1]
        if core.endswith(")") and core.count("(") < core.count(")"):
            core = core[:-1]
        if not core or _overlaps(matched.start(), matched.start() + len(core), found):
            continue
        new = _canon_url(core)
        end = matched.start() + len(core)
        if new and new != core:
            found.append((matched.start(), end, core, new, "link"))
        else:
            found.append((matched.start(), end, core, core, "link"))
    for matched in _EMAIL.finditer(text):
        if _overlaps(matched.start(), matched.end(), found):
            continue
        domain = matched.group(2).lower()
        if domain == matched.group(2):
            continue
        found.append((matched.start(), matched.end(), matched.group(),
                      f"{matched.group(1)}@{domain}", "email"))
    for matched in _UUID.finditer(text):
        if _overlaps(matched.start(), matched.end(), found):
            continue
        prefix, open_, body, close = matched.group(1), matched.group(2), matched.group(3), matched.group(4)
        if open_ and not close or close and not open_:
            body_text = matched.group()
            new = body_text.lower()
        else:
            new = f"{prefix.lower()}{open_}{body.lower()}{close}"
        if new != matched.group():
            found.append((matched.start(), matched.end(), matched.group(), new, "uuid"))
        else:
            found.append((matched.start(), matched.end(), matched.group(), matched.group(), "uuid"))

def _canon_url(raw: str) -> str | None:
    try:
        parts = urlsplit(raw)
    except ValueError:
        return None
    scheme = parts.scheme.lower()
    if scheme not in {"http", "https"} or not parts.hostname:
        return None
    host = parts.hostname.lower()
    if ":" in host:
        host = f"[{host}]"
    try:
        port = parts.port
    except ValueError:
        return None
    netloc = host
    if port and not ((scheme == "http" and port == 80) or (scheme == "https" and port == 443)):
        netloc = f"{host}:{port}"
    if parts.username:
        auth = parts.username if parts.password is None else f"{parts.username}:{parts.password}"
        netloc = f"{auth}@{netloc}"
    return urlunsplit((scheme, netloc, parts.path, parts.query, parts.fragment))
