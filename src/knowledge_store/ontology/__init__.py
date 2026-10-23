"""BC-002 Ontology: the model, discovery, review, released versions, renditions and the candidate register.

The lab ships three shared vocabularies, kept apart from the domain ontology a deployment authors. The core vocabulary (core.ttl, namespace ks:) says where a fact came from, and code may name it. The values vocabulary (values.ttl, namespace kv:) is the datatypes and units a domain attribute may use. The measures ontology (measures.ttl, namespace km:) is the quantities, metrics, instants and periods a domain ontology imports and builds on. The domain ontology says what the documents are about, and code never names its terms. The tool schema, the prompt vocabulary, validation and the RDF typing are all derived from the loaded file.

This module is the context's contract: other contexts import only the names below.
"""

from knowledge_store.kernel.contract import lazy

_EXPORTS: dict[str, str] = {
    "CORE_SHAPES": "domain.model",
    "CORE_TTL": "domain.model",
    "Column": "domain.mapping",
    "DATATYPES": "domain.model",
    "KL": "domain.model",
    "Mapping": "domain.mapping",
    "OntologySpec": "domain.model",
    "PROMPT_VERSION": "domain.tool_schema",
    "TOOL_NAME": "domain.tool_schema",
    "Table": "domain.mapping",
    "label_of": "domain.renditions",
    "model": "@domain.model",
    "normalise": "domain.model",
    "property_of": "domain.renditions",
    "rel_type": "domain.renditions",
    "renditions": "@domain.renditions",
    "subject_template": "domain.mapping",
    "tool_spec": "domain.tool_schema",
    "versions": "@slices.versions",
}

__getattr__, __dir__ = lazy(__name__, _EXPORTS)
