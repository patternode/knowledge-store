"""Source adapters: how content gets from where it lives into bronze.

An adapter does acquisition only. It lists the items a source holds, each with a
version that changes when the item does, and fetches an item's bytes. It does not parse:
turning bytes into text is the refine step's job, chosen by format (refine/), so a new
source never needs to know about PDF and a new format never needs to know about sources.

The ingest step (pipeline/ingest.py) owns everything else: skipping items whose version
it has seen, content-addressing the bytes into bronze, and the manifest. An adapter is
therefore small, and safe to rerun.

Built-in types are registered below. A package can add one without touching this code by
declaring an entry point in the group "knowledge_store.adapters":

    [project.entry-points."knowledge_store.adapters"]
    sharepoint = "my_package.sharepoint:SharePointAdapter"
"""

from __future__ import annotations

from importlib.metadata import entry_points

from ..config import SourceConfig
from ..store import Store
from .base import SourceAdapter, SourceItem
from .http_urls import HttpUrlsAdapter
from .local_dir import LocalDirAdapter
from .s3_landing import S3LandingAdapter

BUILTIN: dict[str, type] = {
    S3LandingAdapter.type: S3LandingAdapter,
    LocalDirAdapter.type: LocalDirAdapter,
    HttpUrlsAdapter.type: HttpUrlsAdapter,
}


def registry() -> dict[str, type]:
    found = dict(BUILTIN)
    for ep in entry_points(group="knowledge_store.adapters"):
        found.setdefault(ep.name, ep.load())
    return found


def build(source: SourceConfig, lake: Store) -> SourceAdapter:
    types = registry()
    if source.type not in types:
        raise ValueError(f"source {source.name!r}: unknown adapter type {source.type!r}; "
                         f"known: {', '.join(sorted(types))}")
    return types[source.type](source, lake)


__all__ = ["SourceAdapter", "SourceItem", "build", "registry"]
