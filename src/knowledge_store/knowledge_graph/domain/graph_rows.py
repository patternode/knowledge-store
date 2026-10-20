"""Nodes and edges from the projection, in the shape a property-graph backend loads."""

from __future__ import annotations

import re

from knowledge_store.kernel.identifiers import safe_name


def stamp(built_at: str) -> str:
    """2026-09-30T12:34:56+00:00 -> 20260930123456"""
    return re.sub(r"\D", "", built_at)[:14]


def rows(entities: list[dict], passages: dict, spec, base: str) -> tuple[list[dict], list[dict]]:
    """Nodes and edges from the projection (the entities and passages project() writes), in the
    shape the neo4j/mapping.json rendition describes. (Imported here, not at the top: the portal
    Lambda imports this package and ships without rdflib, which renditions needs.)"""
    from knowledge_store.ontology import label_of, property_of, rel_type

    def public(pids) -> bool:
        return any(passages.get(p, {}).get("scope") == "public" for p in pids)

    nodes, edges = [], []
    for e in entities:
        types = sorted({a for t in e["types"] if t in spec.classes for a in spec.ancestors(t)} | set(e["types"]))
        props = {"id": e["id"], "iri": base + e["id"], "name": e["label"], "type": e["type"], "types": types,
                 "aliases": list(e["aliases"]), "scope": e.get("scope", "public"), "docs": len(e["docs"]),
                 "links": len(e["out"]) + len(e["in"]), "mentioned_in": list(e["passages"])}
        if isinstance(e.get("public"), dict):  # what public documents say of it, flat (no map properties in Neo4j)
            p = e["public"]
            props.update({"public_type": p.get("type") or "", "public_types": list(p.get("types") or []),
                          "public_aliases": list(p.get("aliases") or []), "public_docs": int(p.get("docs") or 0),
                          "public_links": int(p.get("links") or 0)})
        for a in e["attributes"]:
            k = property_of(a["p"])
            props.setdefault(k, []).append(a["v"])
            cited = props.setdefault(f"{k}__passages", [])
            cited.extend(p for p in a["passages"] if p not in cited)
        nodes.append({"labels": ["Entity", *(safe_name(label_of(t)) for t in types)], "props": props})
        for r in e["out"]:
            edges.append({"s": e["id"], "o": r["o"], "type": safe_name(rel_type(r["p"])),
                          "props": {"p": r["p"], "passages": list(r["passages"]),
                                    "scope": "public" if public(r["passages"]) else "private"}})
    return nodes, edges
