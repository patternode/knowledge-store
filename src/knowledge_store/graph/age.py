"""The graph projection in PostgreSQL with Apache AGE (Azure Database for PostgreSQL, or any
PostgreSQL with the extension).

AGE holds each loaded graph as a graph of its own, so a load creates one and a drop removes it.
AGE gives a vertex one label, so every node is :Entity and its classes are in `types`; each
relation is an edge label. The schema is the age/schema.sql rendition. Loading writes the label
tables with plain SQL (the fast path AGE documents for bulk loads); queries use openCypher with
their values passed as parameters.

    AGE_DSN     a libpq connection string: host=... dbname=... user=...
    AGE_ENTRA   1 to sign in with an Entra token as the password (the managed identity on Azure)
    AGE_LOAD    0 where the server preloads the extension (Azure does), so LOAD 'age' is not run
    AGE_READERS roles granted read access to each graph loaded, comma-separated (on Azure, the
                API's managed identity; created as an Entra principal if it does not exist)

The loader runs as an administrator: it creates the extension and each graph. The readers get
only USAGE and SELECT, on AGE's catalog and on each graph as it is loaded.
"""

from __future__ import annotations

import hashlib
import json
import os
import threading

from . import safe_name

ENTRA_SCOPE = "https://ossrdbms-aad.database.windows.net/.default"


def _agtype(value):
    """AGE prints a scalar as its JSON text; a value may come back as a string or already parsed."""
    return json.loads(value) if isinstance(value, str) else value


class AgeStore:
    name = "age"
    rendition = "age/schema.sql"

    def __init__(self, dsn: str, *, password_provider=None, load_extension: bool = True, readers=()):
        self.dsn, self.password_provider, self.load_extension = dsn, password_provider, load_extension
        self.readers = [r for r in readers if r]
        self._local = threading.local()

    @classmethod
    def from_env(cls) -> "AgeStore":
        provider = None
        if os.environ.get("AGE_ENTRA") == "1":
            from azure.identity import DefaultAzureCredential
            cred = DefaultAzureCredential()
            provider = lambda: cred.get_token(ENTRA_SCOPE).token  # noqa: E731
        return cls(os.environ["AGE_DSN"], password_provider=provider, load_extension=os.environ.get("AGE_LOAD") != "0",
                   readers=[r.strip() for r in os.environ.get("AGE_READERS", "").split(",")])

    def _conn(self):
        """One connection per thread. An Entra token expires, so a closed connection is reopened
        with a fresh one."""
        import psycopg
        c = getattr(self._local, "conn", None)
        if c is None or c.closed:
            kw = {"password": self.password_provider()} if self.password_provider else {}
            c = psycopg.connect(self.dsn, autocommit=True, **kw)
            if self.load_extension:
                c.execute("LOAD 'age'")
            c.execute('SET search_path = ag_catalog, "$user", public')
            self._local.conn = c
        return c

    def _cypher(self, graph: str, query: str, columns: str, params: dict) -> list[tuple]:
        """A Cypher query with its values as an agtype parameter; the graph name is ours and the
        query text constant, so nothing from a caller reaches the query text."""
        sql = f"SELECT * FROM cypher('{safe_name(graph)}', $$ {query} $$, %s) AS ({columns})"
        return self._conn().execute(sql, (json.dumps(params),)).fetchall()

    def key_for(self, collection, version, built_at):
        c = hashlib.sha256(collection.encode()).hexdigest()[:8]
        k = hashlib.sha256(f"{collection}\0{version}\0{built_at}".encode()).hexdigest()[:16]
        return f"ks_{c}_{k}"

    def load(self, key, nodes, edges, schema):
        g = safe_name(key)
        conn = self._conn()
        conn.execute("CREATE EXTENSION IF NOT EXISTS age")
        with conn.transaction():
            for stmt in schema.replace("{graph}", g).split(";\n"):
                stmt = "\n".join(line for line in stmt.splitlines() if not line.strip().startswith("--")).strip()
                if stmt:
                    conn.execute(stmt)
            have = {r[0] for r in conn.execute(
                "SELECT l.name FROM ag_catalog.ag_label l JOIN ag_catalog.ag_graph g ON l.graph = g.graphid "
                "WHERE g.name = %s", (g,))}
            for rtype in sorted({e["type"] for e in edges} - have):
                conn.execute("SELECT create_elabel(%s, %s)", (g, safe_name(rtype)))
            ids: dict[str, str] = {}
            with conn.cursor() as cur:
                cur.executemany(f'INSERT INTO "{g}"."Entity" (properties) VALUES (%s::agtype) RETURNING id',
                                [(json.dumps(n["props"]),) for n in nodes], returning=True)
                for n in nodes:
                    ids[n["props"]["id"]] = str(cur.fetchone()[0])
                    cur.nextset()
            by_type: dict[str, list] = {}
            for e in edges:
                by_type.setdefault(e["type"], []).append((ids[e["s"]], ids[e["o"]], json.dumps(e["props"])))
            with conn.cursor() as cur:
                for rtype, rows in by_type.items():
                    cur.executemany(f'INSERT INTO "{g}"."{safe_name(rtype)}" (start_id, end_id, properties) '
                                    "VALUES (%s::graphid, %s::graphid, %s::agtype)", rows)
            self._grant(conn, g)
            n = conn.execute(f'SELECT count(*) FROM "{g}"."Entity"').fetchone()[0]
            m = conn.execute(f'SELECT count(*) FROM "{g}"."_ag_label_edge"').fetchone()[0]
        return {"nodes": n, "edges": m}

    def _grant(self, conn, graph: str) -> None:
        from psycopg import sql
        for r in self.readers:
            if not conn.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (r,)).fetchone():
                if not self.password_provider:
                    raise RuntimeError(f"AGE_READERS names {r!r}, which is not a role")
                conn.execute("SELECT * FROM pgaadauth_create_principal(%s, false, false)", (r,))
            who = sql.Identifier(r)
            for stmt in ("GRANT USAGE ON SCHEMA {s} TO {r}", "GRANT SELECT ON ALL TABLES IN SCHEMA {s} TO {r}"):
                for schema in ("ag_catalog", graph):
                    conn.execute(sql.SQL(stmt).format(s=sql.Identifier(schema), r=who))

    def drop(self, key):
        conn = self._conn()
        if conn.execute("SELECT 1 FROM ag_catalog.ag_graph WHERE name = %s", (key,)).fetchone():
            conn.execute("SELECT drop_graph(%s, true)", (safe_name(key),))

    def keys(self, collection):
        c = hashlib.sha256(collection.encode()).hexdigest()[:8]
        rows = self._conn().execute("SELECT name FROM ag_catalog.ag_graph WHERE name LIKE %s", (f"ks_{c}_%",))
        return sorted(r[0] for r in rows)

    def bind(self, key):
        return _Bound(self, key)

    def close(self):
        c = getattr(self._local, "conn", None)
        if c is not None:
            c.close()


_COLUMNS = "s agtype, o agtype, p agtype, scope agtype, id agtype, name agtype, type agtype, aliases agtype, " \
           "docs agtype, links agtype, nscope agtype"
_FIELDS = ("id", "name", "type", "aliases", "docs", "links", "scope")


class _Bound:
    def __init__(self, store: AgeStore, key: str):
        self.store, self.key = store, key

    def node(self, node_id):
        rows = self.store._cypher(
            self.key, "MATCH (n:Entity {id: $id}) RETURN n.id, n.name, n.type, n.aliases, n.docs, n.links, n.scope",
            "id agtype, name agtype, type agtype, aliases agtype, docs agtype, links agtype, scope agtype", {"id": node_id})
        return dict(zip(_FIELDS, map(_agtype, rows[0]))) if rows else None

    def adjacent(self, ids, private):
        out = []
        params = {"ids": list(dict.fromkeys(ids))}
        for pattern, s, o in (("(x:Entity)-[r]->(y:Entity)", "x", "y"), ("(y:Entity)-[r]->(x:Entity)", "y", "x")):
            q = (f"MATCH {pattern} WHERE x.id IN $ids "
                 f"RETURN {s}.id, {o}.id, r.p, r.scope, y.id, y.name, y.type, y.aliases, y.docs, y.links, y.scope")
            for row in self.store._cypher(self.key, q, _COLUMNS, params):
                v = [_agtype(x) for x in row]
                out.append(({"s": v[0], "o": v[1], "p": v[2], "scope": v[3]}, dict(zip(_FIELDS, v[4:]))))
        return [(e, n) for e, n in out if private or (e["scope"] == "public" and n["scope"] == "public")]
