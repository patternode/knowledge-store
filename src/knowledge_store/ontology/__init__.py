"""The ontology: model (load an OWL file), core vocabulary, discovery, candidates and versions.

Two vocabularies, kept apart:

* the core vocabulary (core.ttl, namespace kl:) is fixed by the lab: Document, Passage,
  ExtractionRun, Assertion and the provenance properties. Code may name these terms.
* the domain ontology is whatever was discovered or authored for a deployment. Code never
  names its terms. The tool schema, the prompt vocabulary, validation and the RDF typing are
  all derived from the loaded file.
"""
