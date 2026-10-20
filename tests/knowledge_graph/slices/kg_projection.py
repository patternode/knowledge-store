"""A small hand-written projection in a local folder lake: what project() would write, without
running the pipeline. Used by the Knowledge Graph's slice and contract tests.

    Mission Alpha (public)  --launchedBy-->  Agency Nova (public)        stated in a public passage
    Mission Zeta (private)  --launchedBy-->  Agency Nova                 stated in a private passage
    Agency Nova has public names (Nova) and a private alias (Hush Agency).
"""

from __future__ import annotations

from knowledge_store.knowledge_graph.adapters.index import Index
from knowledge_store.platform_services.adapters.store import LocalStore
from knowledge_store.platform_services.domain import layout
from knowledge_store.platform_services.ports import put_json

VERSION = "1.0.0"
ALPHA, ZETA, NOVA = "entity/Mission/alpha", "entity/Mission/zeta", "entity/SpaceAgency/nova"


def _entity(i, label, type_, scope, *, aliases=(), docs=(), out=(), in_=(), passages=(), attributes=(), public=None):
    e = {"id": i, "label": label, "type": type_, "types": [type_], "aliases": list(aliases), "docs": list(docs),
         "out": list(out), "in": list(in_), "passages": list(passages), "attributes": list(attributes), "scope": scope}
    if public:
        e["public"] = public
    return e


ENTITIES = [
    _entity(ALPHA, "Mission Alpha", "Mission", "public", aliases=["Alpha"], docs=["pubdoc"],
            out=[{"p": "launchedBy", "o": NOVA, "passages": ["p-pub"]}], passages=["p-pub"],
            attributes=[{"p": "launchYear", "v": "2020", "passages": ["p-pub"]}],
            public={"type": "Mission", "types": ["Mission"], "aliases": ["Alpha"], "docs": 1, "links": 1}),
    _entity(ZETA, "Mission Zeta", "Mission", "private", docs=["privdoc"],
            out=[{"p": "launchedBy", "o": NOVA, "passages": ["p-priv"]}], passages=["p-priv"]),
    _entity(NOVA, "Agency Nova", "SpaceAgency", "public", aliases=["Nova", "Hush Agency"], docs=["pubdoc", "privdoc"],
            in_=[{"p": "launchedBy", "s": ALPHA, "passages": ["p-pub"]}, {"p": "launchedBy", "s": ZETA, "passages": ["p-priv"]}],
            passages=["p-pub", "p-priv"],
            public={"type": "SpaceAgency", "types": ["SpaceAgency"], "aliases": ["Nova"], "docs": 1, "links": 1}),
]
PASSAGES = {
    "p-pub": {"doc": "pubdoc", "seq": 0, "text": "Mission Alpha was launched by Agency Nova in 2020.", "scope": "public"},
    "p-priv": {"doc": "privdoc", "seq": 0, "text": "Mission Zeta was launched by Agency Nova, the Hush Agency.", "scope": "private"},
}
DOCS = {"pubdoc": {"title": "Public", "name": "public.md", "scope": "public", "format": "md"},
        "privdoc": {"title": "Secret", "name": "secret.md", "scope": "private", "format": "md"}}
ONTOLOGY = {
    "namespace": "https://example.org/missions/", "version": VERSION, "label": "Missions",
    "classes": [{"name": "Mission", "definition": "A mission.", "parents": [], "count": 1},
                {"name": "SpaceAgency", "definition": "An agency.", "parents": ["Organisation"], "count": 1}],
    "relations": [{"name": "launchedBy", "definition": "Who launched it.", "domain": ["Mission"], "range": ["SpaceAgency"], "count": 1},
                  {"name": "relatedTo", "definition": "Anything.", "domain": [], "range": [], "count": 0}],
    "attributes": [{"name": "launchYear", "definition": "The year.", "domain": ["Mission"], "datatype": "integer", "count": 1}],
    "observed": [],
}
SUMMARY = {
    "profile": {"name": "Missions", "description": "Space missions.", "key_terms": ["mission", "agency"]},
    "version": VERSION, "chain": [VERSION], "built_at": "2026-10-20T00:00:00+00:00",
    "history": [{"version": VERSION, "kind": "major", "note": "private note", "in_chain": True}],
    "sources": [{"name": "public", "scope": "public"}, {"name": "private", "scope": "private"}],
    "counts": {"documents": 2, "entities": 3},
    "public": {"counts": {"documents": 1, "entities": 2}},
    "candidates": [{"kind": "class", "term": "Instrument", "evidence": [{"doc_id": "pubdoc", "scope": "public", "text": "x"},
                                                                       {"doc_id": "privdoc", "scope": "private", "text": "y"}]},
                   {"kind": "class", "term": "Hush", "evidence": [{"doc_id": "privdoc", "scope": "private"}]}],
    "ontology_counts": {"classes": {"Mission": 2, "SpaceAgency": 1}, "properties": {"launchedBy": 2, "launchYear": 1},
                        "observed": [{"domain": "Mission", "p": "launchedBy", "range": "SpaceAgency", "count": 2}]},
}


def write(lake) -> None:
    put_json(lake, layout.ONTOLOGY_ACTIVE, {"version": VERSION})
    for name, obj in (("summary", SUMMARY), ("ontology", ONTOLOGY), ("entities", ENTITIES), ("passages", PASSAGES),
                      ("docs", DOCS)):
        put_json(lake, layout.index_key(VERSION, name), obj)


def lake_with_projection(tmp_path):
    lake = LocalStore(tmp_path / "lake")
    write(lake)
    return lake


def index_of(tmp_path) -> Index:
    return Index(lake_with_projection(tmp_path), VERSION)
