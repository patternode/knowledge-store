"""The pipeline sweep: ingest -> refine -> (discover) -> extract -> candidates -> project.

One entry point for every trigger: an upload (S3 event -> EventBridge -> SQS -> Pipe -> ECS
task), the schedule (EventBridge Scheduler, the safety net for missed events) and a person
running it by hand. Every step is idempotent, so the sweep is also the recovery path: rerun it
and it does exactly the work that is missing.

The sweep runs over every collection (collections.py) in turn; one failing collection is
recorded in its status and does not stop the others. Only one sweep runs at a time: the lock is an S3 object created with a conditional write, so
two tasks started by one burst of uploads cannot both win. The loser exits at once, and the
winner keeps sweeping until a round finds nothing new, so uploads that arrive mid-run are
picked up by the run already going. A lock older than LOCK_TTL is taken over (a task that died).

Ontology mode (config/settings.json, from tfvars):

    curated  (default) with no active ontology, discovery writes a draft and extraction waits
             until a person curates and publishes a version.
    auto     with no active ontology, discovery's draft is published as 0.1.0 and activated,
             so an upload goes all the way to the portal unattended. The version is marked
             provisional; curate it and publish 0.1.1 or 1.0.0 in its place when ready.

A provided ontology (config/ontology/, from the collection's ontology_dir in tfvars) takes the
place of discovery in either mode: the sweep publishes and activates it, and extracts against it
(ontology/provided.py).
"""

from __future__ import annotations

import datetime as dt
import json
import logging
import os
import socket
import tempfile
import time
from pathlib import Path

from .. import collections, layout
from ..config import load_profile, load_sources
from ..ontology import candidates, discover, provided, versions
from ..store import Store, put_json
from .extract import extract_all
from .ingest import ingest_source
from .project import project
from .refine import refine_all, silver_doc_ids

log = logging.getLogger("run")

LOCK_TTL_S = 6 * 3600
MAX_ROUNDS = 5

DEFAULT_SETTINGS = {"ontology_mode": "curated", "discovery_min_docs": 5, "discovery_sample": 20,
                    "discovery_resamples": 2, "discovery_target_classes": 15, "discovery_review": True,
                    "extraction_workers": 4}


def settings(lake: Store) -> dict:
    s = dict(DEFAULT_SETTINGS)
    if lake.exists(layout.CONFIG_SETTINGS):
        s.update(json.loads(lake.get(layout.CONFIG_SETTINGS)))
    return s


def acquire(lake: Store, owner: str) -> bool:
    body = json.dumps({"owner": owner, "at": time.time()}).encode()
    if lake.put_if_absent(layout.PIPELINE_LOCK, body):
        return True
    try:
        held = json.loads(lake.get(layout.PIPELINE_LOCK))
    except Exception:
        return False
    if time.time() - float(held.get("at", 0)) > LOCK_TTL_S:
        log.warning("taking over a stale lock held by %s", held.get("owner"))
        lake.delete(layout.PIPELINE_LOCK)
        return lake.put_if_absent(layout.PIPELINE_LOCK, body)
    return False


def release(lake: Store) -> None:
    lake.delete(layout.PIPELINE_LOCK)


def drafts(lake: Store) -> list[dict]:
    out = []
    for key in lake.list(layout.ONTOLOGY_DRAFTS + "/"):
        if key.endswith("/report.json"):
            r = json.loads(lake.get(key))
            out.append({"draft_id": r["draft_id"], "kind": r["kind"], "counts": r.get("counts"),
                        "proposed_version": r.get("proposed_version"), "diff": r.get("diff", {}).get("kind")})
    return sorted(out, key=lambda d: d["draft_id"])


def write_status(lake: Store, stage: str, extra: dict | None = None) -> None:
    active = versions.active_version(lake)
    put_json(lake, layout.STATUS, {
        "stage": stage, "active_version": active, "drafts": drafts(lake),
        "silver_documents": len(silver_doc_ids(lake)),
        "updated_at": dt.datetime.now(dt.UTC).isoformat(timespec="seconds"), **(extra or {})})


def _auto_publish(lake: Store, report: dict) -> None:
    pre = f"{layout.ONTOLOGY_DRAFTS}/{report['draft_id']}"
    with tempfile.TemporaryDirectory() as tmp:
        for name in ("ontology.ttl", "shapes.ttl"):
            Path(tmp, name).write_bytes(lake.get(f"{pre}/{name}"))
        versions.publish(lake, tmp, by="pipeline (ontology_mode=auto)", activate=True,
                         note=f"Provisional: published unreviewed from discovery draft {report['draft_id']}.")


def sweep_once(lake: Store, client_factory, model_id: str, cfg: dict) -> dict:
    stats: dict = {"ingest": {}, "refined": 0, "extracted": 0}
    for source in load_sources(lake):
        s, _ = ingest_source(lake, source)
        stats["ingest"][source.name] = s.as_dict()
    refined = refine_all(lake)
    stats["refined"] = sum(1 for r in refined if r["status"] == "refined")
    profile = load_profile(lake)
    provided_now = provided.apply(lake)  # a provided ontology replaces discovery
    if provided_now:
        stats["ontology"] = provided_now
    if not versions.active_version(lake):
        n = len(silver_doc_ids(lake))
        if n < cfg["discovery_min_docs"]:
            write_status(lake, "waiting_for_documents", {"needed": cfg["discovery_min_docs"]})
            return stats
        if not drafts(lake) or cfg["ontology_mode"] == "auto":
            write_status(lake, "discovering")
            report = discover.discover(client_factory(), model_id, lake, profile,
                                       sample=min(cfg["discovery_sample"], n),
                                       resamples=cfg["discovery_resamples"],
                                       target_classes=cfg["discovery_target_classes"],
                                       review=cfg["discovery_review"])
            stats["discovered"] = report["draft_id"]
            if cfg["ontology_mode"] == "auto":
                _auto_publish(lake, report)
        if not versions.active_version(lake):
            write_status(lake, "awaiting_curation")
            return stats
    write_status(lake, "extracting")
    rows = extract_all(lake, client_factory(), model_id, profile, workers=cfg["extraction_workers"])
    stats["extracted"] = sum(1 for r in rows if r["status"] == "extracted")
    stats["rejected"] = sum(1 for r in rows if r["status"] == "rejected")
    if rows or not lake.exists(layout.index_key(versions.active_version(lake), "summary")):
        candidates.build_register(lake, versions.active_version(lake))
        stats["projection"] = project(lake)
    write_status(lake, "ready", {"last_run": stats})
    return stats


def run_collection(lake: Store, client_factory, model_id: str) -> list[dict]:
    cfg = settings(lake)
    rounds = []
    try:
        for _ in range(MAX_ROUNDS):
            stats = sweep_once(lake, client_factory, model_id, cfg)
            rounds.append(stats)
            log.info("round: %s", json.dumps(stats, default=str))
            new = sum(s.get("stored", 0) for s in stats["ingest"].values())
            if not new and not stats.get("discovered"):
                break
    except Exception as e:
        log.exception("sweep failed")
        write_status(lake, "failed", {"error": repr(e)[:1000]})
        rounds.append({"failed": repr(e)[:300]})
    return rounds


def run(root: Store, client_factory, model_id: str, only: list[str] | None = None) -> dict[str, list[dict]]:
    """Sweep every collection (or only those named) under one lock on the whole lake."""
    owner = f"{socket.gethostname()}-{os.getpid()}"
    if not acquire(root, owner):
        log.info("another sweep holds the lock: nothing to do")
        return {}
    try:
        out = {}
        for cid in collections.ids(root):
            if only and cid not in only:
                continue
            log.info("collection %s", cid)
            out[cid] = run_collection(collections.scoped(root, cid), client_factory, model_id)
        return out
    finally:
        release(root)
