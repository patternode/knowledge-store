"""Source adapters: how content gets from where it lives into bronze.

An adapter does acquisition only. It lists the items a source holds, each with a
version that changes when the item does, and fetches an item's bytes. It does not parse:
turning bytes into text is the refine step's job, chosen by format (refine/), so a new
source never needs to know about PDF and a new format never needs to know about sources.

The ingest slice (ingestion/slices/ingest.py) owns everything else: skipping items whose version
it has seen, content-addressing the bytes into bronze, and the manifest. An adapter is
therefore small, and safe to rerun.

Built-in types are registered below. A package can add one without touching this code by
declaring an entry point in the group "knowledge_store.adapters":

    [project.entry-points."knowledge_store.adapters"]
    sharepoint = "my_package.sharepoint:SharePointAdapter"
"""

from __future__ import annotations

from importlib.metadata import entry_points

from knowledge_store.platform_services import SourceConfig
from knowledge_store.platform_services import Store
from knowledge_store.ingestion.ports import SourceAdapter, SourceItem
from knowledge_store.ingestion.adapters.http_urls import HttpUrlsAdapter
from knowledge_store.ingestion.adapters.local_dir import LocalDirAdapter
from knowledge_store.ingestion.adapters.s3_landing import S3LandingAdapter

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


def ingest_source(lake: Store, source: SourceConfig, *, limit: int | None = None):
    """Build the source's adapter and ingest what it lists. Adapters read from the whole lake
    (landing/ is outside any collection's prefix)."""
    from knowledge_store.ingestion.slices.ingest import ingest
    return ingest(lake, source, build(source, getattr(lake, "whole", lake)), limit=limit)


__all__ = ["SourceAdapter", "SourceItem", "build", "ingest_source", "registry"]
