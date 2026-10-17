# Scalability

What limits Knowledge Store as a collection grows, which way each part scales, and what changes
when a whole organisation's curated data goes in. It compares Amazon Neptune with Neo4j as the
graph for that case. Limits of the managed services were checked against their documentation on
2026-10-10, and the sources are listed at the end. The code references are to this repository at
the same date.

## In short

- The graph database is not the first limit. The pipeline is. One Fargate task sweeps the whole
  lake under one lock, extracts with four threads, and rebuilds the whole projection in 4 GB of
  memory whenever one document changes. At an organisation's scale those steps take weeks, or run
  out of memory, long before Neptune is under strain.
- The second limit is the portal's in-memory projection, which is meant for tens of thousands of
  entities and is loaded by three Lambda functions of 1 GB each.
- Neptune can hold the data. One cluster stores up to 128 TiB with no limit on the number of quads
  or named graphs. Its limits are one writer, and a working set that must fit in one instance's
  cache (about two thirds of its memory: some 2.7 TiB on the largest class). Read replicas add
  throughput, not cache.
- Neo4j does not replace Neptune here. It has no SPARQL and no named graphs, its RDF plugin does not
  run on AuraDB, and an Aura instance on AWS stops at 512 GB of memory with no sharding. It fits as
  what it already is in this design: an optional traversal projection (`GRAPH_BACKEND=neo4j`)
  beside the RDF of record.
- The recommendation is to stay on Neptune for the graph of record, fix the pipeline and the
  projection first, and then scale Neptune up (a larger memory-optimised class, readers, the bulk
  loader), and out by collection (a cluster per collection or per group) when one writer is not
  enough.

## How big is an organisation's curated data

The extractor reifies every fact, so a fact costs about seven quads: the triple itself, the
assertion's type, subject, predicate and object, the extraction run, and one per cited passage
([`extract/rdf.py`](../../../src/knowledge_store/extract/rdf.py), `reify`). An entity adds a type,
a label, its aliases and one quad per passage that mentions it. Each document is its own named
graph, so an entity's type and label are stored again in every document that mentions it.

| Collection | Documents | Facts per document | Quads per ontology version |
|---|---|---|---|
| The examples | tens | 20 to 100 | thousands |
| A department | 10,000 | 100 | about 10 million |
| An organisation's curated data | 1 million | 100 | about 1 billion |
| A large organisation, several versions held | 10 million, or 1 million over several versions | 100 to 200 | 10 billion |

The estimate is ten quads per fact, entity quads included. A minor ontology version adds graphs
beside the old ones, and the loader keeps every version in the chain, so the quads held grow with
the number of versions as well as the corpus.

## Each part, and which way it scales

| Part | Today | Scales out | Scales up | First limit at an organisation's scale |
|---|---|---|---|---|
| Lake (S3) | One bucket, prefixed by collection | Yes, without limit | n/a | None |
| Pipeline (ECS Fargate) | One task, 1 vCPU and 4 GB, one lock over the whole lake | No: one sweep at a time, collections in series | Only by editing the module (`cpu`, `memory` are not passed through) | Extraction time; `project` running out of memory |
| Extraction (Bedrock) | 4 threads, one model call per document, synchronous | Threads only (`extraction_workers`) | n/a | Model throughput quotas and wall-clock time |
| Projection (`gold/<v>/index/*.json`) | Rebuilt in full by one process; loaded whole by the portal and tool Lambdas | No | Lambda memory, up to 10 GB | Memory, beyond tens of thousands of entities |
| Knowledge graph (Neptune) | One `db.t3.medium` writer, no readers; Serverless up to 8 NCU as an option | Readers, up to 15 (none used) | Instance class, up to x2iedn.32xlarge (4 TiB) | The loader, then the instance's cache |
| Passage index (Bedrock KB, S3 Vectors) | One index, one vector per passage, one data source for all collections | Yes, by index | n/a | The serial upload of passages and one ingestion job at a time |
| Agent (AgentCore Runtime) | One runtime, sessions per person | Yes, managed | n/a | The ontology in every prompt; model quotas |
| Chat API (Lambda, DynamoDB) | 20 reserved slots shared by routes and running answers | Yes, by raising `chat_concurrency` | n/a | Answers holding slots for up to 600 s |

### The pipeline

- One writer for the whole lake. `run()` takes one lock on the lake's root and sweeps the
  collections one after another inside it
  ([`pipeline/run.py`](../../../src/knowledge_store/pipeline/run.py), `run`). More collections make
  a longer sweep, not more parallel work. The EventBridge Pipe starts a task per upload
  (`batch_size = 1`), and every task but one exits on the lock.
- Extraction is four threads in one task, one Converse loop per document with up to two repair
  rounds ([`pipeline/extract.py`](../../../src/knowledge_store/pipeline/extract.py),
  [`extract/extractor.py`](../../../src/knowledge_store/extract/extractor.py)). SHACL validation
  runs under one process-wide lock (`sparql_lock.PARSE_LOCK`), so that step is serial across the
  threads. At about 45 seconds a document, four threads extract some 7,700 documents a day: a
  million documents is about four months, and a major ontology version (`semantic` or `removal`)
  re-extracts all of them. Bedrock's tokens-per-minute quota for the model is the ceiling whatever
  the concurrency.
- `project()` parses every `.nq` of every version in the chain into one in-memory rdflib dataset and
  rebuilds all five index files in full, whenever any document was extracted
  ([`pipeline/project.py`](../../../src/knowledge_store/pipeline/project.py)). rdflib's memory
  store costs several hundred bytes to about a kilobyte a triple (an estimate, not measured here),
  so a 4 GB task holds a few million quads: a department, not an organisation.
- `load_sparql` lists and parses every gold `.nq` file on every sweep to decide what changed, then
  loads changed graphs one at a time with `DROP SILENT GRAPH` and `INSERT DATA` over HTTPS, each
  request signed and on a new connection
  ([`pipeline/load.py`](../../../src/knowledge_store/pipeline/load.py)). It first asks Neptune for
  the graphs it holds with `SELECT DISTINCT ?g`, which reads every quad. A million graphs at half a
  second each is about six days of loading.
- `sync_passages` hashes every passage of every document on every sweep and writes two S3 objects
  per changed passage, one at a time.

What would scale it, in order of payoff:

1. Batch inference for backfills and full re-extraction (half the price, and no longer bound by
   four threads). The README already names it as the next step.
2. Fan the per-document steps out: one lock per collection instead of one per lake, and the
   extract step run as many tasks (ECS tasks per shard of documents, or Step Functions Distributed
   Map), each idempotent as it already is.
3. Make `project` incremental, or move it to a job sized for the corpus. A per-document projection
   merged by key, or the projection written straight to the document store
   (`PROJECTION_STORE=mongodb`), removes the single in-memory dataset.
4. Load Neptune with its bulk loader: N-Quads files in S3, written by the extract step, loaded with
   `parallelism: OVERSUBSCRIBE`. N-Quads carries the named graph on each line, so one load job
   covers millions of document graphs. Keep a manifest of what is loaded in the lake rather than
   asking Neptune with `SELECT DISTINCT ?g`.
5. Pass the pipeline task's `cpu`, `memory` and ephemeral storage through the module.

### The projection and the portal

The portal API's routes read the projection from memory, the passages tool always loads it, and
the graph tools load it when Neptune is off
([`portal_api/index.py`](../../../src/knowledge_store/portal_api/index.py),
[`tools/gateway.py`](../../../src/knowledge_store/tools/gateway.py)). Keyword search loops over every
entity and passage. Each warm Lambda can hold every collection's projection at once. The way out is
in the code already: `PROJECTION_STORE=mongodb` makes the portal stateless and scales it out, and
`GRAPH_BACKEND` moves traversals into a database ([backends](backends.md)). Neither is wired in the
Terraform module yet, and the Lambdas are packaged with the standard library and boto3 only, so the
MongoDB and graph drivers would need a layer or a container image.

### The passage index

S3 Vectors holds up to 2 billion vectors per index, 10,000 indexes per bucket, and takes up to 2,500
vector writes a second per index, so one vector per passage fits an organisation's corpus. The
limit is in front of it. The pipeline writes the passages one at a time, and Bedrock Knowledge
Bases runs one ingestion job per data source (and a few per account), so a large backfill
queues. Check the Knowledge Bases quotas in Service Quotas for the region before a large load.
Writing the passages in parallel, and giving each large collection its own data source, removes
most of the queue. Changing the embedding model re-embeds every passage.

### The agent and the chat API

- The agent's system prompt holds the whole agent rendition of the ontology: every class, relation
  and attribute with its definition ([`ontology/renditions.py`](../../../src/knowledge_store/ontology/renditions.py),
  [`agent/app.py`](../../../src/knowledge_store/agent/app.py)). Discovery aims at 15 classes, which
  is small, but a provided enterprise ontology (FIBO-sized, thousands of terms) would cost tens of
  thousands of tokens on each of up to 14 model calls per question. Past a few hundred terms the
  prompt should carry the top of the class tree and let the agent ask for the rest
  (`describe_ontology` by branch), or retrieve the relevant terms for the question.
- The chat API's answers run asynchronously in the same function as the routes, so both share the
  20 reserved slots, and an answer can hold one for up to 600 seconds. Raise `chat_concurrency`
  with the people expected, or give answers their own function.
- AgentCore Runtime, the Gateway and DynamoDB scale out as managed services. The model's quotas
  are the ceiling for questions answered at once.

## The graph: Neptune or Neo4j

### What the graph is asked to do

The graph tools run fixed, read-only SPARQL
([`graph/sparql.py`](../../../src/knowledge_store/graph/sparql.py)):

- find entities by name (`CONTAINS` over labels and aliases) or by type, following
  `rdfs:subClassOf*` in the ontology graph;
- fetch an entity's facts and the passages they cite, in batches of 200 ids;
- neighbourhoods up to three hops and shortest paths up to four, by a breadth-first search in Python
  over those two primitives ([`graph/traverse.py`](../../../src/knowledge_store/graph/traverse.py)),
  so each hop is a round trip.

Each document is a named graph, and the queries read the union of all named graphs with a filter on
the collection's IRI prefix. Scope (public or private) is applied in Python after the fetch.

### Neptune Database

| Constraint | Value | What it means here |
|---|---|---|
| Storage per cluster | 128 TiB; no limit on quads or named graphs | 10 billion quads at 100 to 200 bytes each across the indexes is 1 to 2 TB. Storage is not the limit |
| Writers | One primary per cluster; no write sharding | Ingestion goes through one instance. Global Database adds read-only regions, not writers |
| Readers | Up to 15 on the shared volume, lag usually under 100 ms | Read throughput scales out. Each reader keeps its own cache, so readers do not add cache |
| Largest instances | x2iedn.32xlarge (128 vCPU, 4 TiB), r8g.48xlarge (192 vCPU, 1.5 TiB) | About a thousand times the memory of the default `db.t3.medium` (4 GiB) |
| Buffer cache | About two thirds of instance memory; AWS advises a larger class below a 99.9% hit rate | The hot working set must fit one instance: about 2.7 TiB at most |
| Concurrency | Two query threads per vCPU, then a queue of about 8,000, then throttling | Size by latency times concurrency, divided by two |
| Serverless | 1 to 128 NCU (about 256 GiB); no pause at zero; scaling down drops the cache | Good for a department's graph; too small for an organisation's at the top of the range |
| Indexes | SPOG, POGS, GPSO by default; OSGP optional, only on an empty cluster | The tools' queries always bind the predicate, so POGS serves them and OSGP is not needed for them. It matters for ad hoc queries bound on the object alone, and can only be enabled before the first load |
| Query timeout | Default 120 s; this module sets 30 s | Unbounded aggregates time out first as the graph grows |
| Bulk loader | N-Quads, Turtle, N-Triples, RDF/XML; 64 queued jobs; no published throughput | The way to load at scale; load on a temporarily larger instance |
| Full-text search | Through OpenSearch, fed by Neptune Streams | Replaces `CONTAINS` over every label |

Neptune Analytics is not an option for this graph: it imports N-Triples only (no named graphs, so
no per-document provenance) and is queried with openCypher, not SPARQL.

What would have to change in this repository for Neptune to serve an organisation's graph:

- Point the graph tools at the reader endpoint (it is an output today and unused), and add readers.
- Replace `CONTAINS(LCASE(STR(?n)))` with Neptune's OpenSearch full-text search, or route name search
  through the passage index or the document store. Today every name search reads every label.
- Bound or precompute `list_entities` with no query: it groups every mentioned entity by its fact
  count before taking 500. Precompute the ranking in the pipeline.
- Put a limit on the fact query for one entity. A hub entity (a country, a company's own name)
  returns every fact that names it.
- Query the collection's graphs rather than the union of every collection's. A cluster per large
  collection, or a graph naming scheme that lets a query bind `?g` to the collection, keeps one
  collection's queries off another's data.
- Filter scope in the query, as the Neo4j and AGE backends already do, so private facts are not
  fetched only to be dropped.
- Decide on OSGP when creating a cluster meant for a large graph (lab mode, empty cluster only): it costs up to a fifth more storage and slower inserts, and pays only if the graph will be queried by object without a predicate.
- Choose I/O-Optimized storage once I/O passes a quarter of the Neptune bill, which a large graph
  that misses cache will.

### Neo4j

| Constraint | Value | What it means here |
|---|---|---|
| RDF | Not native. neosemantics (n10s) maps RDF to a property graph, on self-managed Neo4j only, not on AuraDB | No SPARQL. The SPARQL tools become Cypher; named graphs become a property or a label |
| Writers | One leader per database (Raft), in every edition | Ingestion still goes through one instance |
| Community Edition | One instance, no clustering, no online backup; 2^35 nodes and relationships in its store format | Fine for a projection, not for an organisation's graph of record |
| Enterprise (self-managed) | Up to 11 primaries and 20 secondaries per database; block format with 2^48 nodes | Reads scale out on secondaries; licensed per core |
| Composite databases | Enterprise, not Aura; read many, write one per transaction; no relationship across databases | Sharding by collection works; a path across collections does not |
| Infinigraph (property sharding) | GA January 2026; separate subscription, not Aura; topology on one shard, properties spread; writes on one instance | Large property volumes, not more writers |
| AuraDB Professional | Up to 128 GB memory | A department |
| AuraDB Business Critical | Up to 512 GB on AWS and Azure, 2 TB on GCP; storage about twice memory; several databases per instance since September 2026 | The ceiling for a managed Neo4j on AWS |
| AuraDB on AWS | Marketplace offers Professional; PrivateLink is documented for Virtual Dedicated Cloud | Private connectivity from the VPC needs that tier |
| Memory | The page cache should hold the store and its indexes; Graph Data Science projects onto the heap besides | The working set must fit, as with Neptune, but in less memory on Aura |

Where Neo4j is stronger is the traversal itself. Index-free adjacency and a server-side shortest
path answer a four-hop path in one query, where the current code takes a round trip per hop. That is
the reason the design keeps it as an optional projection behind the same two primitives, filled
from the gold RDF by the `load` stage ([backends](backends.md)). Even there the code drives the
breadth-first search from Python; running `shortestPath` or a variable-length match in Cypher would
use the strength the backend is there for.

### Side by side for an organisation's graph

| Question | Neptune Database | Neo4j |
|---|---|---|
| Runs the existing SPARQL and keeps a named graph per document | Yes | No: a rewrite to Cypher and a remodelling of provenance |
| Holds 10^9 to 10^10 quads | Yes, with storage to spare | Self-managed Enterprise, yes; Aura on AWS only while the working set fits in 512 GB |
| Scales reads out | Up to 15 readers, managed | Secondaries (Enterprise); not a customer control on Aura as far as documented |
| Scales writes out | No; one writer per cluster, so shard by collection across clusters | No; one leader per database, so shard by composite database (Enterprise) |
| Largest single instance | 4 TiB memory | 512 GB on Aura for AWS; whatever the hardware allows when self-managed |
| Runs inside the stack's VPC, IAM authentication, Terraform in this module | Yes | Self-managed on EC2 or EKS, or Aura over PrivateLink (Virtual Dedicated Cloud) |
| Multi-hop traversal | Round trips per hop as written; SPARQL property paths are possible but unbounded ones are the risk at scale | Native, one query |
| Cost floor | About 60 USD a month (`db.t3.medium`); large classes cost thousands a month | Aura from about 65 USD a month (Professional, 1 GB); Business Critical and Enterprise licences cost much more |

### Recommendation

1. Keep Neptune as the graph of record. It is the only one of the two that keeps the RDF, the
   SPARQL and the per-document provenance as they are, and its storage is not a constraint.
2. Before adding capacity, make the queries scale: full-text search for names, a precomputed entity
   ranking, a limit on one entity's facts, scope in the query, and the reader endpoint for tools.
3. Scale Neptune up for the working set (r8g for most, x2iedn when the cache hit rate stays under
   99.9% on the largest r8g), and out with readers for questions. Use the bulk loader, on a briefly
   larger writer, for backfills.
4. When one writer or one cache is not enough, partition by collection: a cluster per large
   collection, selected by the collection's configuration. Collections are already isolated by
   prefix in the lake, the vectors and the IRIs, so this is a configuration change more than a
   design change. A question across collections then needs the tools to fan out.
5. Use Neo4j as a traversal projection where paths and neighbourhoods matter, self-managed
   Enterprise or Aura Business Critical sized to the projection rather than to the whole RDF, and
   push the traversal into Cypher.

## Sources

- Neptune limits (storage, quads, payloads, loader jobs): <https://docs.aws.amazon.com/neptune/latest/userguide/limits.html>
- Neptune clusters, writer and readers: <https://docs.aws.amazon.com/neptune/latest/userguide/feature-overview-db-clusters.html>
- Neptune instance types, buffer cache and threads: <https://docs.aws.amazon.com/neptune/latest/userguide/instance-types.html>
- Neptune Serverless capacity: <https://docs.aws.amazon.com/neptune/latest/userguide/neptune-serverless-capacity-scaling.html>
- Neptune indexes and OSGP: <https://docs.aws.amazon.com/neptune/latest/userguide/feature-overview-storage-indexing.html>
- Neptune SPARQL and named graphs: <https://docs.aws.amazon.com/neptune/latest/userguide/feature-sparql-compliance.html>
- Neptune parameters (query timeout, DFE): <https://docs.aws.amazon.com/neptune/latest/userguide/parameters.html>
- Neptune bulk loading and best practice: <https://docs.aws.amazon.com/neptune/latest/userguide/bulk-load-tutorial-format-rdf.html>, <https://docs.aws.amazon.com/neptune/latest/userguide/best-practices-general-basic.html>
- Neptune full-text search: <https://docs.aws.amazon.com/neptune/latest/userguide/full-text-search.html>
- Neptune Global Database: <https://docs.aws.amazon.com/neptune/latest/userguide/neptune-global-database.html>
- Neptune pricing: <https://aws.amazon.com/neptune/pricing/>
- Neptune Analytics and RDF: <https://docs.aws.amazon.com/neptune-analytics/latest/userguide/using-rdf-data.html>, <https://docs.aws.amazon.com/neptune-analytics/latest/apiref/API_CreateGraph.html>
- EC2 sizes: <https://aws.amazon.com/ec2/instance-types/x2i/>, <https://aws.amazon.com/ec2/instance-types/r8g/>
- S3 Vectors limits: <https://docs.aws.amazon.com/AmazonS3/latest/userguide/s3-vectors-limitations.html>
- Neo4j neosemantics: <https://neo4j.com/labs/neosemantics-rdf/>
- Neo4j clustering: <https://neo4j.com/docs/operations-manual/current/clustering/introduction/>
- Neo4j store formats: <https://neo4j.com/docs/operations-manual/current/database-internals/store-formats/>
- Neo4j composite databases: <https://neo4j.com/docs/operations-manual/current/scalability/composite-databases/concepts/>
- Neo4j property sharding (Infinigraph): <https://neo4j.com/docs/operations-manual/current/scalability/sharded-property-databases/overview/>, <https://neo4j.com/docs/operations-manual/current/scalability/scaling-with-neo4j/>
- Neo4j memory configuration: <https://neo4j.com/docs/operations-manual/current/performance/memory-configuration/>
- AuraDB pricing and tiers: <https://neo4j.com/pricing/>
- AuraDB multiple databases: <https://neo4j.com/blog/graph-database/multiple-databases-now-generally-available-in-auradb/>
- AuraDB on cloud providers and private connections: <https://neo4j.com/docs/aura/cloud-providers/>, <https://neo4j.com/docs/aura/security/secure-connections/>

Not verified: Neptune publishes no bulk-loader throughput and no page on SPARQL property paths in
its DFE engine; the bytes per quad, rdflib's memory per triple and the seconds per extraction are
estimates; Bedrock Knowledge Bases' ingestion quotas vary by region and account; whether AuraDB
Business Critical offers private endpoints on AWS is not documented.
