"""Collections: several corpora in one lake, each with its own sources, profile, ontology
lineage, gold and portal projection.

    config/collections.json               [{"id": "holmes"}, {"id": "missions"}] (written by Terraform)
    collections/<id>/config/*.json        that collection's sources, profile and settings
    collections/<id>/bronze/ ... gold/    the same layout as a single lake (layout.py)
    landing/<id>/                         where a collection's uploads land by default

Each collection is a PrefixStore over the lake, so every step works on one collection
unchanged. Ontologies never span collections: two domains discovered as one ontology would be
a muddle, and every revision would touch both. Collections that must be isolated from each
other by account or key, not just by prefix and IAM, belong in separate stacks.
"""

from __future__ import annotations

import json
import re

from .store import PrefixStore, Store

CONFIG = "config/collections.json"
PREFIX = "collections"
DEFAULT_ID = "default"
_ID = re.compile(r"^[a-z0-9][a-z0-9-]{0,39}$")


def valid_id(cid: str) -> str:
    if not _ID.match(cid or ""):
        raise ValueError(f"collection id {cid!r} must be 1-40 lower-case letters, digits or hyphens")
    return cid


def ids(root: Store) -> list[str]:
    if root.exists(CONFIG):
        return [valid_id(c["id"]) for c in json.loads(root.get(CONFIG))]
    return [DEFAULT_ID]


def scoped(root: Store, cid: str) -> PrefixStore:
    return PrefixStore(root, f"{PREFIX}/{valid_id(cid)}/")


def collection_id(store: Store) -> str | None:
    """The collection a scoped store belongs to, or None for a bare store."""
    p = getattr(store, "prefix", "")
    m = re.match(rf"^{PREFIX}/([^/]+)/$", p)
    return m.group(1) if m else None
