"""Retrieval measures over what the tools returned, not only what the answer cited.

Citation precision and recall measure the answer's citations, so a retrieval that found the right
passage and an answer that ignored it look the same as a retrieval that never found it. These
measures read the answer trace's retrieved list (every id the tools returned, in order) and keep
the two apart:

    recall_at_k            of the units the set expects, the share among the first k retrieved
    precision_at_k         of the first k retrieved, the share the set expects
    reciprocal_rank        one over the rank of the first expected unit retrieved, 0 when none was
    retrieved_not_cited    expected units the tools returned and the answer left out: an answering
                           fault, not a retrieval one
    ndcg_at_k              with graded relevance in the set: discounted gain against the ideal order

A unit is a passage when the question names passages, otherwise a document (the set's sources),
matched as the citation measures match them. No model judges anything here.
"""

from __future__ import annotations

import math
from pathlib import Path

KS = (5, 10)


def _hit(found: str, expected: str) -> bool:
    return (found == expected or found.endswith("/" + expected) or expected.endswith("/" + found)
            or Path(expected).name == found)


def ranked_units(retrieved: list[dict], by_passage: bool) -> list[str]:
    """The distinct units in the order the tools first returned them."""
    out: list[str] = []
    for item in retrieved or []:
        unit = item.get("id") if by_passage else (item.get("doc") or None)
        if unit and unit not in out:
            out.append(str(unit))
    return out


def _match(unit: str, expected: list[str]) -> str | None:
    return next((e for e in expected if _hit(unit, e)), None)


def measures(expected: list[str], relevance: dict, retrieved: list[dict], cited: set[str],
             by_passage: bool) -> dict:
    ranked = ranked_units(retrieved, by_passage)
    out: dict = {"retrieved_units": len(ranked)}
    if expected:
        for k in KS:
            top = ranked[:k]
            found = {m for u in top if (m := _match(u, expected))}
            out[f"recall_at_{k}"] = round(len(found) / len(expected), 3)
            out[f"precision_at_{k}"] = round(sum(1 for u in top if _match(u, expected)) / len(top), 3) if top else 0.0
        first = next((i for i, u in enumerate(ranked, 1) if _match(u, expected)), None)
        out["reciprocal_rank"] = round(1 / first, 3) if first else 0.0
        got = {m for u in ranked if (m := _match(u, expected))}
        out["retrieved_not_cited"] = sorted(e for e in got if not any(_hit(c, e) for c in cited))
    if relevance:
        k = KS[-1]
        gains = [next((g for unit, g in relevance.items() if _hit(u, unit)), 0) for u in ranked[:k]]
        dcg = sum((2 ** g - 1) / math.log2(i + 2) for i, g in enumerate(gains))
        ideal = sorted(relevance.values(), reverse=True)[:k]
        idcg = sum((2 ** g - 1) / math.log2(i + 2) for i, g in enumerate(ideal))
        out[f"ndcg_at_{k}"] = round(dcg / idcg, 3) if idcg else None
    return out
