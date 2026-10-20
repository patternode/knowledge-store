"""A small missions ontology and passages, shared by the Extraction tests."""

from __future__ import annotations

from knowledge_store.ingestion.domain.chunk import Passage, chunk_text
from knowledge_store.ontology.domain import model

TTL = """
@prefix o: <https://example.org/missions#> .
@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix skos: <http://www.w3.org/2004/02/skos/core#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
<https://example.org/missions> a owl:Ontology ; owl:versionInfo "0.1.0" .
o:Mission a owl:Class ; rdfs:label "Mission" ; skos:altLabel "probe" .
o:Orbiter a owl:Class ; rdfs:subClassOf o:Mission ; rdfs:label "Orbiter" .
o:SpaceAgency a owl:Class ; rdfs:label "Space agency" .
o:TargetBody a owl:Class ; rdfs:label "Target body" .
o:launchedBy a owl:ObjectProperty ; rdfs:domain o:Mission ; rdfs:range o:SpaceAgency .
o:studies a owl:ObjectProperty ; rdfs:domain o:Mission ; rdfs:range o:TargetBody .
o:launchYear a owl:DatatypeProperty ; rdfs:domain o:Mission ; rdfs:range xsd:integer .
o:budget a owl:DatatypeProperty ; rdfs:domain o:Mission ; rdfs:range xsd:decimal .
o:motto a owl:DatatypeProperty ; rdfs:domain o:Mission .
"""

DOC_ID = "a" * 64
TEXT = ("Mission Alpha was launched by Agency Nova in 2011.\n\n"
        "Mission Alpha studies Planet Kiro and cost $1,250.50 million.\n\n"
        "Its motto is “Reach further”.")


def spec() -> model.OntologySpec:
    return model.load(data=TTL)


def passages() -> list[Passage]:
    return chunk_text(TEXT, DOC_ID, target=60, max_chars=200)


def doc() -> dict:
    return {"doc_id": DOC_ID, "title": "Alpha", "source": "docs", "scope": "public"}


def run() -> dict:
    return {"run_id": "r1", "model_id": "fake", "prompt_version": "p1", "ontology_version": "0.1.0"}


def good_result() -> dict:
    p = passages()
    return {
        "entities": [
            {"ref": "e1", "type": "Mission", "name": "Mission Alpha", "aliases": ["Alpha", "Mission Alpha", " "],
             "passage_ids": [p[0].passage_id]},
            {"ref": "e2", "type": "SpaceAgency", "name": "Agency Nova", "passage_ids": [p[0].passage_id]},
            {"ref": "e3", "type": "TargetBody", "name": "Planet Kiro", "passage_ids": [p[1].passage_id]},
        ],
        "attributes": [
            {"entity": "e1", "property": "launchYear", "value": "2011", "passage_ids": [p[0].passage_id]},
            {"entity": "e1", "property": "budget", "value": "1250.50", "passage_ids": [p[1].passage_id]},
        ],
        "relations": [
            {"subject": "e1", "predicate": "launchedBy", "object": "e2", "passage_ids": [p[0].passage_id]},
            {"subject": "e1", "predicate": "studies", "object": "e3", "passage_ids": [p[1].passage_id]},
        ],
        "candidates": [],
    }
