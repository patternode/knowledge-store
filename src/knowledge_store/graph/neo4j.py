"""The graph projection in Neo4j (AuraDB, or any Neo4j 5).

Graphs share one database (an AuraDB instance has one), told apart by the `g` property on every
node; a node is unique on (g, id). Nodes carry :Entity and a label per class, ancestors included,
so a query on a parent class finds its subclasses. The schema is the neo4j/schema.cypher rendition.

    NEO4J_URI        neo4j+s://<instance>.databases.neo4j.io (or bolt://host:7687)
    NEO4J_USERNAME   default neo4j
    NEO4J_PASSWORD   from the deployment's secret store
    NEO4J_DATABASE   default neo4j
"""

from __future__ import annotations

import hashlib
import os
from collections import defaultdict

from . import safe_name, stamp

BATCH = 1000
_BRIEF = "{.id, .name, .type, .aliases, .docs, .links, .scope}"


def _chunks(rows: list, n: int = BATCH):
    for i in range(0, len(rows), n):
        yield rows[i:i + n]


class Neo4jStore:
    name = "neo4j"
    rendition = "neo4j/schema.cypher"

    def __init__(self, driver, database: str = "neo4j"):
        self.driver, self.database = driver, database

    @classmethod
    def from_env(cls) -> "Neo4jStore":
        from neo4j import GraphDatabase
        driver = GraphDatabase.driver(os.environ["NEO4J_URI"],
                                      auth=(os.environ.get("NEO4J_USERNAME", "neo4j"), os.environ["NEO4J_PASSWORD"]))
        return cls(driver, os.environ.get("NEO4J_DATABASE", "neo4j"))

    def _session(self):
        return self.driver.session(database=self.database)

    def key_for(self, collection, version, built_at):
        tail = hashlib.sha256(f"{collection}\0{version}\0{built_at}".encode()).hexdigest()[:8]
        return f"{collection}@{version}@{stamp(built_at)}-{tail}"

    def load(self, key, nodes, edges, schema):
        with self._session() as s:
            for stmt in schema.split(";"):
                stmt = "\n".join(line for line in stmt.splitlines() if not line.strip().startswith("//")).strip()
                if stmt:
                    s.run(stmt).consume()
            by_labels: dict[tuple, list] = defaultdict(list)
            for n in nodes:
                by_labels[tuple(n["labels"])].append({**n["props"], "g": key})
            for labels, props in by_labels.items():
                text = f"UNWIND $rows AS r CREATE (n:{':'.join(safe_name(x) for x in labels)}) SET n = r"
                for chunk in _chunks(props):
                    s.run(text, rows=chunk).consume()
            by_type: dict[str, list] = defaultdict(list)
            for e in edges:
                by_type[e["type"]].append({"s": e["s"], "o": e["o"], "props": e["props"]})
            for rtype, rows in by_type.items():
                text = (f"UNWIND $rows AS r MATCH (a:Entity {{g: $g, id: r.s}}) MATCH (b:Entity {{g: $g, id: r.o}}) "
                        f"CREATE (a)-[x:{safe_name(rtype)}]->(b) SET x = r.props")
                for chunk in _chunks(rows):
                    s.run(text, rows=chunk, g=key).consume()
            n = s.run("MATCH (n:Entity {g: $g}) RETURN count(n) AS n", g=key).single()["n"]
            m = s.run("MATCH (:Entity {g: $g})-[r]->() RETURN count(r) AS n", g=key).single()["n"]
        return {"nodes": n, "edges": m}

    def drop(self, key):
        with self._session() as s:
            s.run("MATCH (n:Entity {g: $g}) CALL { WITH n DETACH DELETE n } IN TRANSACTIONS OF 5000 ROWS", g=key).consume()

    def keys(self, collection):
        with self._session() as s:
            res = s.run("MATCH (n:Entity) WHERE n.g STARTS WITH $p RETURN DISTINCT n.g AS g", p=f"{collection}@")
            return sorted(r["g"] for r in res)

    def bind(self, key):
        return _Bound(self, key)

    def close(self):
        self.driver.close()


class _Bound:
    def __init__(self, store: Neo4jStore, key: str):
        self.store, self.key = store, key

    def node(self, node_id):
        with self.store._session() as s:
            r = s.run(f"MATCH (n:Entity {{g: $g, id: $id}}) RETURN n {_BRIEF} AS n", g=self.key, id=node_id).single()
            return dict(r["n"]) if r else None

    def adjacent(self, ids, private):
        text = (f"UNWIND $ids AS i MATCH (x:Entity {{g: $g, id: i}})-[r]->(y:Entity) "
                f"WHERE $private OR (r.scope = 'public' AND y.scope = 'public') "
                f"RETURN x.id AS s, y.id AS o, r.p AS p, r.scope AS scope, y {_BRIEF} AS n "
                f"UNION ALL "
                f"UNWIND $ids AS i MATCH (y:Entity)-[r]->(x:Entity {{g: $g, id: i}}) "
                f"WHERE $private OR (r.scope = 'public' AND y.scope = 'public') "
                f"RETURN y.id AS s, x.id AS o, r.p AS p, r.scope AS scope, y {_BRIEF} AS n")
        with self.store._session() as s:
            return [({"s": r["s"], "o": r["o"], "p": r["p"], "scope": r["scope"]}, dict(r["n"]))
                    for r in s.run(text, ids=list(dict.fromkeys(ids)), g=self.key, private=private)]
