"""Sweep the walk's query settings on the multi-document questions, no model cost but the query embeddings.

    python examples/enterprise-rag-bench/walk_grid.py <k> <lake> <set.yaml> <ids file>

Prints, for vector search and for each setting of the walk (and the two fused by reciprocal rank), how
many questions had every expected document in the top k, how many had at least one, and the mean share
of expected documents found. The lake must be embedded, with facts and walk built."""
import sys, yaml, itertools
from knowledge_store.platform_services.adapters.store import store_from_uri
from knowledge_store.platform_services.slices import collections
from knowledge_store.knowledge_graph.adapters import passages, index
from knowledge_store.knowledge_graph.slices import walk
from knowledge_store.ingestion import load_doc, silver_doc_ids
L = sys.argv[2]
root = store_from_uri(L); lake = collections.scoped(root, "enterprise-rag")
qs = {q["id"]: q for q in yaml.safe_load(open(sys.argv[3]))["questions"]}
ids = open(sys.argv[4]).read().strip().split(",")
emb = passages.embedder_from_env(); idx = index.load(lake, "enterprise-rag")
dsid = {d: (load_doc(lake, d).get("name") or "").split("__")[0] for d in silver_doc_ids(lake)}
K = int(sys.argv[1])
want = {i: {s.split("__")[0] for s in qs[i]["sources"]} for i in ids}
qvec = {i: emb.embed([qs[i]["question"][:1000]])[0] for i in ids}   # one embedding a question, reused

class Fixed:
    """An embedder that answers with the precomputed question vector."""
    model, dimensions = emb.model, emb.dimensions
    def __init__(self, v): self.v = v
    def embed(self, texts): return [self.v]

def score(found_by_q):
    full = sum(1 for i in ids if {dsid.get(p["doc"], p["doc"]) for p in found_by_q[i]} >= want[i])
    any_ = sum(1 for i in ids if {dsid.get(p["doc"], p["doc"]) for p in found_by_q[i]} & want[i])
    cov = sum(len({dsid.get(p["doc"], p["doc"]) for p in found_by_q[i]} & want[i]) / len(want[i]) for i in ids) / len(ids)
    return full, any_, round(cov, 3)

base = {i: passages.search(lake, idx, "enterprise-rag", qs[i]["question"], private=False, limit=K)["passages"] for i in ids}
print(f"search k={K}: all {score(base)[0]}/{len(ids)} any {score(base)[1]}/{len(ids)} coverage {score(base)[2]}")
for pw, tf, damp, go in itertools.product((0.05, 0.3, 1.0, 3.0), (10, 20), (0.5,), (False,)):
    found = {i: walk.related(lake, qs[i]["question"], embedder=Fixed(qvec[i]), limit=K, top_facts=tf,
                             passage_weight=pw, damping=damp, grounded_only=go)["passages"] for i in ids}
    s = score(found)
    print(f"walk pw={pw:<4} facts={tf:<3} damping={damp:<5} grounded_only={go!s:<5}: all {s[0]}/{len(ids)} any {s[1]}/{len(ids)} coverage {s[2]}", flush=True)
    fused = {}
    for i in ids:   # reciprocal rank fusion of the walk and the search, top K kept
        rank = {}
        for lst in (found[i], base[i]):
            for r, p in enumerate(lst):
                rank[p["id"]] = rank.get(p["id"], 0.0) + 1.0 / (10 + r)
        by_id = {p["id"]: p for lst in (found[i], base[i]) for p in lst}
        fused[i] = [by_id[pid] for pid, _ in sorted(rank.items(), key=lambda x: -x[1])[:K]]
    s = score(fused)
    print(f"  fused with search                                      : all {s[0]}/{len(ids)} any {s[1]}/{len(ids)} coverage {s[2]}", flush=True)
