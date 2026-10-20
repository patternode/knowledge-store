"""BC-006 Access: who may ask, who may read what, quotas and chat state, and the portal API and gateway interceptor that enforce it.

This module is the context's contract: other contexts import only the names below.
"""

from knowledge_store.kernel.contract import lazy

_EXPORTS: dict[str, str] = {
    "agent_quota": "@adapters.agent_quota",
}

__getattr__, __dir__ = lazy(__name__, _EXPORTS)
