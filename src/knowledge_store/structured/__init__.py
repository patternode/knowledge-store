"""Structured lookup: a mapped table beside the documents.

People edit mappings.yaml (and, optionally, metrics.osi.yaml) next to the ontology.
Publish checks both against the ontology and renders the forms the sweep and a later
virtual knowledge graph read. Bind copies each mapped CSV into gold at its content
hash. The tools read that snapshot; they do not accept a query string.
"""
