"""BC-005 Answering: a person's question to an answer made only of claims that passed their checks, within limits, with the steps visible.

This module is the context's contract: other contexts import only the names below.
"""

from knowledge_store.kernel.contract import lazy

_EXPORTS: dict[str, str] = {
}

__getattr__, __dir__ = lazy(__name__, _EXPORTS)
