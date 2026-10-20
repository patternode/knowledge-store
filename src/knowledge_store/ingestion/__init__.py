"""BC-001 Ingestion: sources, the immutable bronze copies, parsing into silver documents and passages.

This module is the context's contract: other contexts import only the names below.
"""

from knowledge_store.kernel.contract import lazy

_EXPORTS: dict[str, str] = {
    "Passage": "domain.chunk",
    "bronze_objects": "slices.ingest",
    "load_doc": "slices.refine",
    "load_passages": "slices.refine",
    "silver_doc_ids": "slices.refine",
}

__getattr__, __dir__ = lazy(__name__, _EXPORTS)
