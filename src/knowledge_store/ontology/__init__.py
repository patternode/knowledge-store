"""BC-002 Ontology: the model, discovery, review, released versions, renditions and the candidate register.

Two vocabularies, kept apart: the core vocabulary (core.ttl, namespace kl:), fixed by the lab, which code may name; and the domain ontology discovered or authored for a deployment, which code never names. The tool schema, the prompt vocabulary, validation and the RDF typing are all derived from the loaded file.

This module is the context's contract: other contexts import only the names below.
"""

from knowledge_store.kernel.contract import lazy

_EXPORTS: dict[str, str] = {
}

__getattr__, __dir__ = lazy(__name__, _EXPORTS)
