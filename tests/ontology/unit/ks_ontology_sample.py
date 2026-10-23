"""A small ontology the Ontology context's tests share: missions, agencies and targets."""

TTL = """
@prefix o:    <https://example.org/space#> .
@prefix owl:  <http://www.w3.org/2002/07/owl#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix xsd:  <http://www.w3.org/2001/XMLSchema#> .
@prefix kv:   <https://w3id.org/knowledge-store/values#> .
@prefix skos: <http://www.w3.org/2004/02/skos/core#> .
@prefix ext:  <https://other.example/x#> .

<https://example.org/space> a owl:Ontology ;
    rdfs:label "Space"@en ;
    rdfs:comment "Missions and who flies them."@en ;
    owl:versionInfo "1.2.0" ;
    owl:versionIRI <https://example.org/space/1.2.0> ;
    owl:priorVersion <https://example.org/space/1.1.0> .

o:Organisation a owl:Class ; rdfs:label "Organisation"@en .
o:SpaceAgency a owl:Class ; rdfs:label "Space agency"@en ; rdfs:label "Agence spatiale"@fr ;
    skos:altLabel "agency"@en ; skos:definition "A body that runs space programmes."@en ;
    rdfs:subClassOf o:Organisation, ext:Thing .
o:Mission a owl:Class ; rdfs:label "Mission"@en ; rdfs:comment "A flight."@en .
o:CrewedMission a owl:Class ; rdfs:subClassOf o:Mission .
o:Target a owl:Class ; rdfs:label "Target"@en .
o:Retired a owl:Class ; owl:deprecated true .
ext:Thing a owl:Class .

o:launchedBy a owl:ObjectProperty ; rdfs:label "launched by"@en ;
    rdfs:domain o:Mission ; rdfs:range o:Organisation .
o:studies a owl:ObjectProperty ; rdfs:domain o:Mission ; rdfs:range o:Target .
o:launchYear a owl:DatatypeProperty ; rdfs:domain o:Mission ; rdfs:range xsd:integer .
o:budget a owl:DatatypeProperty ; rdfs:domain o:Mission ; rdfs:range xsd:double .
o:motto a owl:DatatypeProperty .
"""


def spec():
    from knowledge_store.ontology.domain import model

    return model.load(data=TTL)
