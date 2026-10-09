# Structured lookup

The store answers from documents. A file becomes passages, extraction turns those passages into
RDF, and the agent looks entities and passages up through fixed tools. CSV and JSON take that
same path: a CSV is decoded as text (`refine/parsers.py` sends `.csv` through `parse_text`), and
JSON is flattened to `path: value` lines. The model then guesses entities out of the lines.

That is the right path for a report that happens to contain a table. It is the wrong path for a
table that is the source. A filter ("launches after 2010 on an Atlas V"), a total, or a value
that must match a cell cannot be grounded as a passage quote: the quote check wants twelve
characters copied from prose (`agent/grounding.py`), and the graph has no aggregate tool even
though evaluation questions already have kind `aggregate`. Entity identity is the root type plus
a normalised name, so two rows for the same mission under two labels become two nodes.

This note drafts the extension that looks structured data up in the ontology's own terms, and
where [AWS Context Ontology Accelerator](https://github.com/aws/context-ontology-accelerator)
fits. It is a design, not a change to the pipeline.

## What stays

The document path is unchanged. Gold RDF extracted from passages remains the record for anything
a model inferred. The agent still has no free SPARQL or SQL tool: `tools/gateway.py` builds a
fixed query per tool so a shared endpoint can enforce scope. A private source stays private
through `caller_private`, written by the gateway interceptor from the caller's token. A term
still reaches the ontology only when a person publishes a version.

Structured lookup is a second way to fill and read the same ontology, for sources whose schema
is already known.

## A table is a source, not a document

An adapter lists items and fetches bytes. A table does not fit that contract: its identity is a
relation, its version is a snapshot, and its rows are records rather than a file to parse. A
structured source is a catalog entry in `config/sources.json`, beside the document sources:

| Field | Meaning |
|---|---|
| `type` | `table` for an object already in the lake (CSV, TSV, or a JSON array of objects), `glue` or `athena` for a catalog table |
| `location` | Lake key, Glue table, or Athena database and table |
| `key` | Columns that identify a row |
| `scope` | `public` or `private`, the same flag documents use |
| `snapshot` | Filled by the sweep: content hash for a lake file, Glue or Athena version for a catalog |

A `.csv` that a mapping names is not refined and not extracted. A `.csv` that no mapping names
keeps today's path, so a prose file with a comma in it is undisturbed. Registering the source
is the curator's act, the same way `ontology_dir` opts out of discovery.

## The mapping is part of the version

People edit a mapping next to the ontology master. The master stays OWL. The mapping says which
table fills which class, and it is published with the version, immutable once published.

```yaml
# ontology/mappings.yaml
tables:
  launches:
    source: launches
    class: Mission
    key: [mission]
    columns:
      mission: {attribute: name}
      vehicle: {attribute: launchVehicle}
      launched: {attribute: launchDate, datatype: xsd:date}
      target: {relation: target, range: Body, match: label}
metrics:
  launches_by_vehicle:
    definition: How many missions each rocket launched.
    class: Mission
    aggregate: count
    group_by: launchVehicle
```

`knowledge-store ontology publish` checks the mapping the way review checks an edit. A class,
attribute, relation, or datatype the ontology does not have is refused. A column datatype that
disagrees with the attribute's datatype is refused. A relation's range must be a class. A metric
may only aggregate a mapped attribute, and may group by one mapped attribute.

The release renders the mapping, as it renders every other consumer form
(`ontology/renditions.py`):

| Rendition | For |
|---|---|
| `structured/mapping.json` | The sweep and the tools: class, key, columns, metrics |
| `r2rml/mapping.ttl` | A virtual backend, or a Context Ontology Accelerator namespace, generated and never edited |

Two releases of the same master and the same mapping render the same files. The agent rendition
gains one line per mapped type: the source and the snapshot the active version was bound to, so
a question can tell a table fact from an extracted one.

Column names are untrusted, as document text is. A column becomes an attribute when someone
publishes a version whose mapping names it. The sweep can list unmapped columns into the
candidate register (name, datatype, how many distinct values) so `candidates --propose` sees
them. Discovery itself keeps sampling passages. A table's schema is not a document sample.

## Snapshot into gold

The first backend copies the table at its snapshot into the lake. The sweep stage `bind` runs
after extract, for structured sources only:

```
gold/<version>/structured/<source>/<snapshot>.nq     rows as RDF, one named graph
gold/<version>/structured/<source>/<snapshot>.jsonl  the cells, for the citation check
```

Each row becomes an entity whose IRI is the class plus the key columns, not the normalised
label. That is the resolution rule for structured entities, and it is why "NASA" in a table and
"National Aeronautics and Space Administration" in a document stay two nodes until a mapping or
a document says they are the same. Attributes become assertions. A relation column matches the
object by the named field (`label` above) inside the same snapshot, and a miss is recorded in
the bind report rather than invented.

SHACL runs on the snapshot graph with the ontology shapes plus the cell shape below. A snapshot
that fails is not activated. The previous snapshot stays readable: a citation names the snapshot
it was checked against, the way a passage citation names a document id. New answers use the
snapshot `ontology/active` binding points at. Bind is skipped when the snapshot hash is
unchanged.

Copied rows join the graph the tools already query, so `neighbourhood` and `find_paths` cross a
document fact and a table fact. The projection indexes them with the document entities. A table
too large to copy, or one that must be read live, waits for the virtual backend below. The tools
do not change between the two.

A document and a table may disagree. Both assertions are kept, each with its own citation. The
answer states the disagreement and cites both. Bind does not drop a passage fact because a cell
differs.

## Tools

Three tools, on the graph Lambda when the snapshot is in the lake (it already sits in the VPC
with no route out). A virtual backend that calls Athena moves that tool to a function with a
route out, still with no free-form query.

| Tool | Arguments | Returns |
|---|---|---|
| `describe_structured` | collection | Mapped types, metrics, source, snapshot. Read before a filter or a total |
| `lookup_rows` | collection, type, filters, limit | Rows of one mapped type. A filter is an attribute, an operator (`eq`, `neq`, `lt`, `lte`, `gt`, `gte`, `prefix`), and a value. Each value carries its cell id |
| `aggregate` | collection, and either a metric name or (`type`, `op`, `attribute`, optional `group_by`, optional filters) | The figure, the snapshot, and the filters. `op` is `count`, `sum`, `min`, `max`, or `avg`. One group-by. A row cap, the same shape of cap `get_entity` already uses |

`describe_ontology` keeps returning the agent rendition, including the mapped-type lines, so the
prompt still has one vocabulary. `lookup_rows` and `aggregate` read the snapshot. They do not
accept a query string.

The chat agent and the portal loop share `run_tool`, as the other tools do. The system prompt
gains a step: a filter or a total goes to `aggregate` or `lookup_rows`, and the claim cites the
cell. Passage quotes remain the citation for anything extraction produced.

## Citations

`ks:extractedFrom` ranges over `ks:Passage`. Widening it would make every existing consumer
re-read the core vocabulary. Table assertions cite a new term instead.

| Term | Meaning |
|---|---|
| `ks:Cell` | One column of one row of one snapshot: source, snapshot, key, column |
| `ks:recordedIn` | Assertion to Cell. A `prov:wasDerivedFrom`, sibling of `ks:extractedFrom` |

Core 1.1.0 adds the class and the property. `AssertionShape` then accepts an assertion that has
a passage citation or a cell citation, and still requires a run. A consumer that assumed every
assertion had `ks:extractedFrom` must also read `ks:recordedIn`. The passage shape is unchanged.
The cell's value is stored on the cell, so the check compares against the snapshot file and does
not trust the triple alone.

A claim may cite either kind:

| Citation | Checked by |
|---|---|
| Passage id and a quote | The passage exists, the caller may read it, the quote occurs in it, the quote is long enough |
| Cell id and a value | The cell exists in that snapshot, the caller may read the source, the value equals the cell. Numbers compare as decimals. Dates compare as dates |
| Metric or aggregate, with its filters | The checker recomputes the figure over that snapshot and those filters, and the stated figure matches |

A claim that mixes a passage and a cell must pass both checks. A cell citation does not pass
the twelve-character quote rule, and a passage quote does not stand in for a cell. The guardrail's
contextual grounding check still sees the claim against the returned text, which for a cell is
the column name and the value. One repair turn, as today. A claim with nothing left is dropped.

The citation id in an answer is `c:<source>/<snapshot>/<key>/<column>` for a cell and
`m:<metric>/<snapshot>` for a metric, next to `p:<passage id>`.

## Versions

The bump classes already decide the cost. The mapping follows them.

| Change | Bump | Bind |
|---|---|---|
| A label, a metric definition's wording | patch | nothing |
| A new mapped column, a new metric, a new table | minor | that table only |
| A key, a class, a datatype, or a relation's range | major | every mapped table, and a full re-extraction where the ontology change already requires one |

An additive version's gold holds the new snapshot as its delta. The graph for the version is
still the union back to the last full version.

## Workbench and evaluation

A structured call is its own step type, "Structured lookup", with the ontology terms the filter
named. Cost-by-path can charge it: a metric run has no model call inside the tool. Usage
counters record the mapped terms the same way they record classes the graph tools touch.

"What would it take?" already distinguishes `ontology_missing` and `data_missing`. A column with
no attribute is `ontology_missing`. A filter the mapping cannot express, or a table the
collection does not have, is `data_missing`. An aggregate the snapshot computes and the answer
missed is `extraction_missed`'s sibling for tables: the report says the cell was there.

Evaluation kind `aggregate` scores the figure with the existing `must` list, and `sources` may
name the table. `grounded` counts a cell check the same way it counts a passage check. No model
judges the number.

## Virtual reads, later

Some tables should not be copied: they are large, or the answer is wrong if it is an hour old.
The virtual backend runs the same `lookup_rows` and `aggregate` calls as SQL against Athena or
Glue, through a template fixed by the mapping. The model never sees the SQL. The checker
re-executes the same template against the same snapshot id and fails closed if the source has
moved. Paths that cross a live row and a document entity resolve the row's key into the graph
first (`lookup_rows` by key, then `neighbourhood`), which keeps traversal in Neptune.

The R2RML rendition is what this backend, or an external one, consumes. Generating it in the
first milestone costs nothing at runtime and keeps the mapping portable.

## Context Ontology Accelerator

[Context Ontology Accelerator](https://aws.github.io/context-ontology-accelerator/) (Apache 2.0,
announced July 2026) is a self-deployed semantic layer. Its own description is Scan, Model,
Serve:

| Stage | What it does | With |
|---|---|---|
| Scan | Connect structured and unstructured sources, enrich metadata, ingest documents | Glue Data Catalog, JDBC, S3 documents |
| Model | Induce an OWL ontology, review it, map relational schema, define metrics | OWL 2, R2RML, SHACL, governed metrics, Neptune |
| Serve | Answer agents in tiers | MCP on AgentCore Runtime, REST, a SPARQL endpoint |

The tiers, in order, are a governed metric (compiled SQL, no model call), SPARQL over a virtual
knowledge graph (Ontop on ECS, translating SPARQL to SQL) or a natural-language-to-SQL strategy,
then retrieval over OpenSearch, a Neptune traversal, and a model synthesis. Cedar policies and a
SQL firewall sit on the structured paths. The MCP tools are `list_metrics`, `describe_schema`,
`query`, `translate_sparql`, `rag_retrieval`, and `graph_traversal`. AWS has said the
user-defined ontology in the accelerator becomes a feature of AWS Context, so a deployment that
binds to the MCP server can move with that without taking a dependency on Ontop.

### Shared ground

Both projects treat an ontology as OWL plus SHACL, reviewed by a person before it is published,
stored as the customer's graph, and read by an agent through MCP on AgentCore. Both use Neptune,
Bedrock, S3, and a guardrail, and both record where a served fact came from. A collection here
and a namespace there are the same cut: one ontology, one corpus.

### Where the designs differ

The accelerator's serve path is a planner. `query` chooses a tier and can return a synthesized
answer. `translate_sparql` and the natural-language-to-SQL strategy hand the model a query
language. This store's gateway was written the other way: fixed tools, scope applied in the
interceptor, and code checking every citation before a sentence is shown. A synthesized sentence
from another server would reach the page without a passage or a cell the checker can re-read.

The accelerator leaves structured rows in the source database and records the SQL as
provenance. This store's record for inferred facts is the gold file, and a citation has to
resolve to bytes that still exist. A metric that was true yesterday must still be checkable
tomorrow, which a live database does not promise. Snapshots give that. Virtual reads are the
exception, and they fail closed.

Induction differs on purpose. Discovery here follows extract-define-canonicalise over passage
samples, with stability across resamples and edits applied in code. The accelerator induces from
catalog metadata and documents inside its own control plane. Running both on one corpus yields
two drafts and two review queues.

The idle shape differs too. This module's fixed cost is the Neptune instance, and it can be
turned off. The accelerator adds OpenSearch Serverless, a Java virtual-knowledge-graph service,
Glue, Athena, and its own review application. That is the right stack for an estate already
living in JDBC and Glue. It is a poor fit for a lake of documents plus a few tables.

### What this extension takes from it

Four ideas, each already shaped like something this store does.

Mappings are a rendition. R2RML is the portable form. The curated file is the smaller YAML above,
checked against `OntologySpec` at publish, and `r2rml/mapping.ttl` is generated beside
`neo4j/mapping.json`. Ontop is one consumer of that rendition, and this module does not have to
run it.

Governed metrics are the accelerator's first tier: a named aggregate published with the ontology,
deterministic, with no model call on the execution path, and recomputed by the checker. The
`aggregate` tool runs a metric by name. An ad hoc aggregate is allowed only inside the operators
and the single group-by the tool schema lists. That schema is the firewall for as long as the
model cannot edit SQL.

The tier order lives in the prompt the agent already has: metrics, then row filters, then the
graph and the passages. The workbench shows which one ran. A second orchestrator that classifies
the question and falls through strategies would hide that trail and could return text the
grounding check never saw.

Unmapped columns join the candidate register. They do not open a second induction pipeline.

### What stays in this module

Scope stays the Cognito group and `caller_private`. Cedar is the accelerator's policy language
for an estate that already uses it. Duplicating it here would give two answers to the same
question of who may read a private source.

Passage search stays on the Knowledge Base and S3 Vectors. Structured lookup is a filter over
typed columns, which a vector index does not answer, and the cost note in
[aws.md](aws.md#do-we-need-a-vector-store) still holds for prose.

The chat, the grounding check, and the workbench stay one loop. The accelerator's MCP server
replaces that loop if it is asked to answer the person. Used as a backend, it is a source of
cells, and the cells still pass the checker in this agent.

### Calling the accelerator as a backend

Use it when the structured estate is already Glue or JDBC across databases, answers must be
live, and the organisation will run the accelerator's control plane (its review UI, its metrics,
its policies). The fit is a tool, not a merge.

`query_context` calls the accelerator's `query` for the namespace bound to the collection. The
caller's token maps to whatever principal that namespace already enforces. The result is usable
when it carries cells: source, snapshot or query fingerprint, column, value. Each cell is
re-checked, or the claim is dropped, the same rule as a quote that does not occur in the
passage. A result that is only a synthesized sentence is dropped.

The ontology is shared in one direction. This store's publish renders `r2rml/mapping.ttl` and a
person loads it into the namespace, or a Turtle file published by the accelerator is this
collection's `ontology_dir`. Discovery runs on one side. `describe_ontology` remains this
store's agent rendition, so the prompt does not carry two vocabularies.

Binding the tool to the accelerator's MCP, rather than to Ontop or to a private SPARQL
endpoint, follows the product direction AWS has stated: ontologies created there move to AWS
Context, and this module keeps its document record, its citation check, and its fixed tools.

## Order of work

1. Check the mapping at publish, and write the two renditions. No new source and no new tool. A
   collection with no `mappings.yaml` publishes as it does now.
2. Lake tables: `type: table` sources, the `bind` stage, `ks:Cell` in core 1.1.0,
   `describe_structured`, `lookup_rows`, `aggregate` over the snapshot, and cell checks in
   `agent/grounding.py`. Document extraction is untouched.
3. Named metrics in the mapping, recomputed by the checker, shown as their own step.
4. A virtual backend behind those same tools, Athena first. The accelerator's MCP is that
   backend when the estate is already its namespace, with cell checks still local.

Each step is separately shippable. None of them replaces the passage tools, the gold files
extracted from documents, or the rule that a statement is shown only after code has checked its
citation.
