"""BC-003 Extraction: silver passages and mapped tables to gold RDF, for one ontology version. Nothing here names a domain term; the loop is extract, check, repair, salvage.

This module is the context's contract: other contexts import only the names below.
"""

from knowledge_store.kernel.contract import lazy

_EXPORTS: dict[str, str] = {
}

__getattr__, __dir__ = lazy(__name__, _EXPORTS)
