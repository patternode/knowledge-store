"""BC-008 Platform services, the generic subdomain: the lake (the Store port and its S3 and local adapters), model access, the cost ledger, collections and deployment configuration.

This module is the context's contract: other contexts import only the names below.
"""

from knowledge_store.kernel.contract import lazy

_EXPORTS: dict[str, str] = {
    "ModelClient": "ports",
    "PrefixStore": "ports",
    "Profile": "slices.config",
    "S3Store": "adapters.store",
    "SourceConfig": "slices.config",
    "Store": "ports",
    "collections": "@slices.collections",
    "decode_tool_input": "adapters.llm",
    "get_json": "ports",
    "layout": "@domain.layout",
    "ledger": "@adapters.ledger",
    "llm": "@adapters.llm",
    "load_profile": "slices.config",
    "load_sources": "slices.config",
    "put_json": "ports",
    "runtime_client": "adapters.llm",
    "store_from_uri": "adapters.store",
}

__getattr__, __dir__ = lazy(__name__, _EXPORTS)
