"""The answer trace: one record per answer, the evidence an auditor, an evaluation and the
dashboards all read.

It says who asked (a keyed hash, never the identity), what was asked, what the answer was
answered against (the collection and ontology version; mapping and table versions once the supply
port records them), what answered (the model, the prompt version, the release), everything the
tools returned in the order they returned it, what the answer cites, each claim with its support
verdict, the outcome (answered, declined or failed), any guardrail intervention, and the tokens,
cost and time. Its schema is one of the contracts patternode-architecture ADR-083 publishes.

Pure: built from the answer the agent returned and what the composition root knows.
"""

from __future__ import annotations

import hashlib

SCHEMA = "answer-trace/1"


def caller_hash(subject: str | None, salt: str) -> str | None:
    """A keyed hash of the caller: stable for one deployment, meaningless outside it."""
    if not subject:
        return None
    return hashlib.sha256(f"{salt}:{subject}".encode()).hexdigest()[:24]


def outcome(out: dict) -> str:
    if out.get("outcome"):
        return out["outcome"]
    if out.get("error") and not out.get("answer"):
        return "failed"
    return "declined" if out.get("abstained") else "answered"


def build(*, answer_id: str, at: str, question: str, collection: str, out: dict, caller: str | None,
          scopes: list[str] | None, model: str | None, prompt_version: str | None, release: str) -> dict:
    grounding = out.get("grounding") or {}
    cited = []
    for c in out.get("claims") or []:
        for x in c.get("citations") or []:
            ref = x.get("passage_id") or x.get("cell_id") or x.get("metric_id")
            if ref and ref not in cited:
                cited.append(ref)
    for c in out.get("citations") or []:  # the portal's own loop cites passages directly
        ref = c.get("id") or c.get("passage_id")
        if ref and ref not in cited:
            cited.append(ref)
    return {
        "schema": SCHEMA, "answer_id": answer_id, "at": at,
        "caller": caller, "scopes": sorted(scopes or []),
        "question": question, "collection": collection or out.get("collection"),
        "ontology_version": out.get("ontology_version"), "mapping_version": out.get("mapping_version"),
        "snapshots": out.get("snapshots") or [],
        "model": model, "prompt_version": prompt_version, "release": release, "toolset": out.get("toolset"),
        "retrieved": out.get("retrieved") or [], "cited": cited,
        "claims": [{"text": c.get("text"), "support": c.get("support", "unchecked"), "verifier": c.get("verifier"),
                    "support_score": c.get("support_score")} for c in out.get("claims") or []],
        "outcome": outcome(out), "error": out.get("error"),
        "dropped": {"unsupported": len(grounding.get("unsupported_dropped") or []),
                    "guardrail": len(grounding.get("guardrail_dropped") or []),
                    "citations_failed": len(grounding.get("failures") or [])},
        "usage": out.get("usage"), "cost": out.get("cost"), "ms": out.get("ms"),
    }
