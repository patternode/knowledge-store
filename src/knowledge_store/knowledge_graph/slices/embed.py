"""Embed every silver passage, for search by meaning without a Knowledge Base.

One row a passage, with its vector, in silver/vectors/passages.jsonl (layout.SILVER_VECTORS), behind a
header row naming the model, its dimensions, the build time and the count. adapters/passages.py reads it
(LocalVectorSearch). The embedder is given, an Embedder (model, dimensions, embed(texts) -> vectors), so
this slice holds no SDK; the command line wires Titan on Bedrock (adapters/embeddings.py).

A passage id carries its content hash, so a passage the same model embedded before keeps its vector and
is not sent again; a new model, or new dimensions, embeds everything.
"""

from __future__ import annotations

import datetime as dt
import json
from concurrent.futures import ThreadPoolExecutor

from knowledge_store.ingestion import load_doc, load_passages, silver_doc_ids
from knowledge_store.platform_services import layout

BATCH = 16


def read_vectors(lake) -> tuple[dict, list[dict]]:
    """The header and the rows of the vector file, or ({}, []) when there is none."""
    if not lake.exists(layout.SILVER_VECTORS):
        return {}, []
    rows = [json.loads(line) for line in lake.get(layout.SILVER_VECTORS).decode().splitlines() if line.strip()]
    return (rows[0], rows[1:]) if rows else ({}, [])


def embed_passages(lake, embedder, *, workers: int = 4) -> dict:
    header, old = read_vectors(lake)
    same = header.get("model") == embedder.model and header.get("dim") == embedder.dimensions
    kept = {r["id"]: r["vec"] for r in old} if same else {}
    rows, todo = [], []
    for doc_id in silver_doc_ids(lake):
        doc = load_doc(lake, doc_id)
        for p in load_passages(lake, doc_id):
            row = {"id": p.passage_id, "doc": doc_id, "title": doc.get("title") or doc.get("name"),
                   "scope": doc.get("scope", "public"), "source_uri": doc.get("source_uri"), "seq": p.seq, "text": p.text}
            if p.passage_id in kept:
                row["vec"] = kept[p.passage_id]
            else:
                todo.append(row)
            rows.append(row)

    def run(batch: list[dict]) -> None:
        for row, vec in zip(batch, embedder.embed([r["text"] for r in batch])):
            row["vec"] = [round(x, 6) for x in vec]

    with ThreadPoolExecutor(max(1, workers)) as ex:
        list(ex.map(run, [todo[i:i + BATCH] for i in range(0, len(todo), BATCH)]))
    head = {"model": embedder.model, "dim": embedder.dimensions, "passages": len(rows),
            "built_at": dt.datetime.now(dt.UTC).isoformat(timespec="seconds")}
    lake.put(layout.SILVER_VECTORS, ("\n".join(json.dumps(x) for x in [head, *rows]) + "\n").encode(),
             "application/x-ndjson")
    return {"passages": len(rows), "embedded": len(todo), "kept": len(rows) - len(todo),
            "model": embedder.model, "dim": embedder.dimensions}
