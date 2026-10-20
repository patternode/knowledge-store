"""BC-008 Platform services, the generic subdomain: the lake (the Store port and its S3 and local adapters), model access, the cost ledger, collections and deployment configuration.

This module is the context's contract: other contexts import only the names below.
"""

from knowledge_store.kernel.contract import lazy

_EXPORTS: dict[str, str] = {
}

__getattr__, __dir__ = lazy(__name__, _EXPORTS)
