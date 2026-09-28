"""Ontology-guided extraction: silver passages -> gold RDF, for one ontology version.

Nothing here names a domain term. The tool schema, the vocabulary in the prompt, the checks
and the RDF typing are all derived from the loaded ontology (ontology/model.py), which is
what makes the lab domain-agnostic. The loop is extract, check, repair, salvage.
"""
