"""BC-003 Extraction: silver passages and mapped tables to gold RDF, for one ontology version. Nothing here names a domain term; the loop is extract, check, repair, salvage.

This module is the context's contract: other contexts import only the names below.
"""

from knowledge_store.kernel.contract import lazy

_EXPORTS: dict[str, str] = {
    "active": "slices.bind_tables",
    "binding": "slices.bind_tables",
    "data_base": "domain.rdf",
    "mapped_doc_ids": "slices.bind_tables",
    "open_fact_rows": "slices.open_facts",
    "published_mapping": "slices.bind_tables",
}

__getattr__, __dir__ = lazy(__name__, _EXPORTS)
