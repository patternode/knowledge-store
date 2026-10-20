"""Identifiers written into query text.

Labels and relationship types are written into Cypher and SQL text (no engine takes them as
parameters), so they must be plain identifiers. Ontology names are; safe_name makes sure. Both
the Ontology context (its Neo4j rendition) and the Knowledge Graph context (its backends) use it.
"""

from __future__ import annotations

import re

_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

def safe_name(name: str) -> str:
    """Labels and relationship types are written into query text (no engine takes them as
    parameters), so they must be plain identifiers. Ontology names are; this makes sure."""
    if not _NAME.match(name):
        raise ValueError(f"{name!r} is not a plain identifier, so it cannot be a graph label")
    return name
