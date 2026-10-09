# Graph and document backends

The portal's projection is JSON under `gold/<version>/index/`, loaded into one process's memory.
That is right for tens of thousands of entities (see Limits in the README). Two optional backends
take it further, each filled by the pipeline's `load` stage after `project`, and each set
independently:

| Setting | Values | Holds |
|---|---|---|
| `GRAPH_BACKEND` | `none` (default), `neo4j`, `age` | entities and relations, for neighbourhoods and paths |
| `PROJECTION_STORE` | `memory` (default), `mongodb` | the entities, passages and documents the portal and tools read, and their search |
| `CHAT_STATE` | `dynamodb` (default), `mongodb`, `memory` | chat answers and the daily question quota |

With `PROJECTION_STORE=mongodb` the portal API holds nothing in memory and scales out. With a
graph backend, traversals run in the database. The MongoDB settings (`MONGODB_URI`,
`MONGODB_DB`) are shared by the projection and the chat state.

### Loading and switching

A load goes into a new graph, or a new set of documents, keyed by collection, version and build.
Its counts are checked against the projection before the lake's pointer (`gold/graph.json`,
`gold/documents.json`) moves to it. The portal uses a backend only while the pointer names the
index it is serving, and answers from memory otherwise, so a failed or half-finished load is
never served. The previous load is kept for rollback (point back at it) and older ones are
dropped. The load runs at the end of every sweep and does nothing when the pointer is current, so
turning a backend on needs no migration step: the next sweep fills it.

### Graph

- Each release renders the schema per backend: `neo4j/schema.cypher` and `age/schema.sql` (the
  graph, its labels, indexes). The loader runs the rendition of the active version. The mapping
  in `neo4j/mapping.json` (node key, labels, properties, provenance) is shared by both.
- Neo4j keeps several graphs in one database (an AuraDB instance has one), told apart by `g`; a
  node is unique on `(g, id)` and carries a label per class, ancestors included. AGE keeps each
  load as a graph of its own, and gives a vertex one label, so classes are in a `types` property.
- A backend answers two primitives: a node by id, and the relations of a set of nodes. The
  neighbourhood and path traversals (`graph/traverse.py`) run on those primitives, the same code
  for memory and every backend, and a contract test checks that Neo4j and AGE give the in-memory
  answer for every entity and every pair, in both scopes. A public caller never passes through a
  private entity or along a private relation.
- The tools gain `find_paths` (every shortest chain of relations between two entities, up to four
  long) and `neighbourhood` takes `hops`; the portal API gains `/api/neighbourhood` and
  `/api/paths`. They work without a graph backend too, from memory.

### Documents

The document store speaks the MongoDB wire protocol through `pymongo`, so the switch is a
connection string. The code keeps to a subset that MongoDB-compatible services also support: CRUD,
`find_one_and_update` with `$inc` and a filter (the quota), `$in` and `$regex`, compound and
multikey indexes. It avoids `$text`, Atlas Search, transactions and rich aggregation, and never
depends on TTL for correctness. Search uses token arrays with a multikey index, the same tokens
`index.py` uses, and ranks as `index.py` does; a contract test checks every route and view against
the in-memory index. The suite runs on MongoDB; run it against any compatible service before
relying on it, because "compatible" differs in detail.

### Cost

The AWS stack idles at close to nothing. Every graph backend has a monthly floor (a burstable
PostgreSQL server, or an Aura instance), which is why `memory` stays the default and the graph is for collections
that have outgrown it.
