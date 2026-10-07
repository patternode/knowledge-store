"""Object-key layout of the lake. One place, so the jobs, the portal API and the Terraform
(modules/lake, modules/pipeline) agree on prefixes; keep them in step.

    landing/<anything>                      uploads from people and tools; never written by the lab
    bronze/<source>/<hh>/<sha256>/content<ext>  immutable copy of each distinct object, keyed by content
    bronze/<source>/<hh>/<sha256>/meta.json     where it came from (adapter, source uri, etag, fetched_at)
    bronze/_seen/<source>/<key-hash>.json   adapter bookkeeping: source key + etag -> bronze id
    silver/documents/<doc_id>.json          parsed document: text, title, metadata, parser version
    silver/passages/<doc_id>.jsonl          deterministic chunks, the unit of citation
    silver/skipped/<doc_id>.json            why a bronze object has no silver document (format, empty)
    gold/<version>/graph/<doc_id>.nq        SHACL-valid N-Quads for one document at one ontology
                                            version: the system of record
    gold/<version>/extractions/<doc_id>.json    the model's result, repairs and usage, for audit
    gold/<version>/rejected/<doc_id>.json   what failed validation and why
    gold/<version>/candidates/<doc_id>.jsonl    terms the ontology has no word for, seen in this document
    gold/<version>/index/*.json             projection the portal serves (rebuildable from graph/)
    ontology/versions/<version>/ontology.ttl, shapes.ttl, manifest.json   immutable once published
    ontology/active.json                    {"version": ...}: the version extraction runs against
    ontology/drafts/<draft_id>/...          discovery and revision proposals, for a person to curate
    ontology/candidates/register.json       candidate terms aggregated across documents
    config/sources.json, config/profile.json, config/settings.json   written by Terraform from tfvars
    gold/sparql.json, gold/kb.json          what the SPARQL store and the Knowledge Base hold
    portal/status.json                      pipeline stage and counts, for the portal before any ontology exists
    locks/pipeline.json                     the one-at-a-time pipeline lock
    manifests/<job>/<run_id>.jsonl          one row per item a run touched
    usage/ledger/...                        model call ledger (ledger.py)

doc_id is the sha256 of the bronze object's bytes, so the same content uploaded twice is one
document, and a changed file is a new document.
"""

from __future__ import annotations

import hashlib

LANDING = "landing"
BRONZE = "bronze"
SEEN = "bronze/_seen"
SILVER_DOCS = "silver/documents"
SILVER_PASSAGES = "silver/passages"
SILVER_SKIPPED = "silver/skipped"
GOLD = "gold"
ONTOLOGY_VERSIONS = "ontology/versions"
ONTOLOGY_ACTIVE = "ontology/active.json"
ONTOLOGY_DRAFTS = "ontology/drafts"
CANDIDATE_REGISTER = "ontology/candidates/register.json"
CONFIG_SOURCES = "config/sources.json"
CONFIG_PROFILE = "config/profile.json"
CONFIG_SETTINGS = "config/settings.json"
CONFIG_ONTOLOGY = "config/ontology"   # a provided ontology: ontology.ttl, optional shapes.ttl
STATUS = "portal/status.json"
GRAPH_POINTER = "gold/graph.json"
DOCUMENTS_POINTER = "gold/documents.json"
SPARQL_POINTER = "gold/sparql.json"        # what the SPARQL store (Neptune) holds of this collection
PASSAGES_POINTER = "gold/kb.json"          # what the Knowledge Base data source holds of it
KB_PASSAGES = "kb/passages"                # kb/passages/<collection>/<passage id>.txt (+ .metadata.json),
                                           # at the lake's root: the Knowledge Base's one data source
PIPELINE_LOCK = "locks/pipeline.json"
MANIFESTS = "manifests"


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def bronze_prefix(source: str, digest: str) -> str:
    return f"{BRONZE}/{source}/{digest[:2]}/{digest}"


def bronze_content_key(source: str, digest: str, ext: str) -> str:
    return f"{bronze_prefix(source, digest)}/content{ext}"


def bronze_meta_key(source: str, digest: str) -> str:
    return f"{bronze_prefix(source, digest)}/meta.json"


def seen_key(source: str, source_key: str) -> str:
    return f"{SEEN}/{source}/{sha256(source_key.encode())[:32]}.json"


def doc_key(doc_id: str) -> str:
    return f"{SILVER_DOCS}/{doc_id}.json"


def passages_key(doc_id: str) -> str:
    return f"{SILVER_PASSAGES}/{doc_id}.jsonl"


def skipped_key(doc_id: str) -> str:
    return f"{SILVER_SKIPPED}/{doc_id}.json"


def gold_prefix(version: str) -> str:
    return f"{GOLD}/{version}"


def graph_key(version: str, doc_id: str) -> str:
    return f"{GOLD}/{version}/graph/{doc_id}.nq"


def extraction_key(version: str, doc_id: str) -> str:
    return f"{GOLD}/{version}/extractions/{doc_id}.json"


def rejected_key(version: str, doc_id: str) -> str:
    return f"{GOLD}/{version}/rejected/{doc_id}.json"


def candidates_key(version: str, doc_id: str) -> str:
    return f"{GOLD}/{version}/candidates/{doc_id}.jsonl"


def index_key(version: str, name: str) -> str:
    return f"{GOLD}/{version}/index/{name}.json"


def ontology_version_prefix(version: str) -> str:
    return f"{ONTOLOGY_VERSIONS}/{version}"


def doc_id_from_key(key: str) -> str:
    """The doc id in a silver or gold key: the file name without its extension."""
    return key.rsplit("/", 1)[-1].split(".", 1)[0]
