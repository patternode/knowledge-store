# Knowledge Store core vocabulary

Namespace `https://w3id.org/knowledge-store/core#`, prefix `ks:`. Version 1.0.0, version IRI `https://w3id.org/knowledge-store/core/1.0.0`.

The core vocabulary says where a fact came from, never what it is about. Every deployment shares it, and code may name its terms. What a fact is about is said by the collection's own ontology, which is discovered or authored per collection and never redefines these terms.

| Identifier | Resolves to |
|---|---|
| `https://w3id.org/knowledge-store/core` | The latest version: Turtle for RDF clients (`Accept: text/turtle`), this page for browsers |
| `https://w3id.org/knowledge-store/core/<version>` | That release, from git tag `core-v<version>` |
| `https://w3id.org/knowledge-store/core/shapes` | The core SHACL shapes (`/core/<version>/shapes` for a release) |

Source: [`src/knowledge_store/ontology/core.ttl`](../src/knowledge_store/ontology/core.ttl) and [`core-shapes.ttl`](../src/knowledge_store/ontology/core-shapes.ttl).

## Classes

| Class | Meaning |
|---|---|
| `ks:Document` | One distinct piece of content, identified by the sha256 of its bytes (a `prov:Entity`) |
| `ks:Passage` | A deterministic chunk of a document: the unit a fact cites (a `prov:Entity`) |
| `ks:ExtractionRun` | One pass of a model over documents against one ontology version (a `prov:Activity`) |
| `ks:Assertion` | A reified attribute or relation, carrying the passages it is stated in and the run that extracted it (an `rdf:Statement`) |

## Properties

| Property | From, to | Meaning |
|---|---|---|
| `ks:partOf` | Passage, Document | The document a passage belongs to |
| `ks:mentionedIn` | any, Passage | An entity is named in this passage |
| `ks:extractedFrom` | Assertion, Passage | The passage an assertion is stated in (a `prov:wasDerivedFrom`) |
| `ks:extractedBy` | any, ExtractionRun | The run that produced it (a `prov:wasGeneratedBy`) |
| `ks:document` | any, Document | The document a graph describes |
| `ks:source` | Document, string | The configured source it was ingested from |
| `ks:scope` | Document, string | `public` or `private`: private facts are served to private-scope callers only |
| `ks:seq` | Passage, integer | Its position in the document |
| `ks:contentHash` | any, string | The sha256 of the content |
| `ks:modelId`, `ks:promptVersion` | ExtractionRun, string | What produced the run |
| `ks:ontologyVersion` | any, string | The collection ontology version a run or graph belongs to |
| `ks:delta` | ExtractionRun, boolean | The run extracted only the terms an additive ontology version added |

## The shapes

The core shapes are the provenance gate every document's graph passes before it is stored: every assertion cites at least one passage and exactly one run, and names its subject, predicate and object; every entity mentioned in a passage has a label; every passage belongs to exactly one document; every run names its model and ontology version.

## Versioning

The core vocabulary is versioned separately from the software, with semantic versions: additions are minor, changes to the meaning of a term or its removal are major. Each release is tagged `core-v<version>` in the repository, and its version IRI resolves to that tag.
