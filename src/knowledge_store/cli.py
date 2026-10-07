"""knowledge-store: the command line for every step and the ontology lifecycle.

    knowledge-store run                          the full sweep (what the triggers run)
    knowledge-store ingest | refine | extract | project
    knowledge-store discover [--sample 20 --resamples 2]
    knowledge-store ontology versions | active
    knowledge-store ontology pull <draft-id|version> <dir>   copy a draft or version into git to curate
    knowledge-store ontology diff <dir>                      what publishing <dir> would change, and the bump it needs
    knowledge-store ontology publish <dir> [--activate]      publish a curated version (immutable)
    knowledge-store ontology activate <version>
    knowledge-store ontology render <dir> <out>              the renditions a release of <dir> would ship
    knowledge-store candidates [--min-docs 2] [--propose]    the register, and a draft revision from it
    knowledge-store status

--lake is s3://bucket, az://account/container, gs://bucket or a local directory; it defaults
to $LAKE_URI. -c names the collection (default: default); knowledge-store collections lists
them. Model calls use $LLM_PROVIDER (bedrock, anthropic, foundry or vertex) and
$EXTRACTION_MODEL_ID.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from pathlib import Path

from . import layout, ledger
from .config import load_profile, load_sources
from .store import store_from_uri

DEFAULT_MODEL = "us.anthropic.claude-sonnet-5"


def _client():
    from .llm import runtime_client
    return runtime_client(read_timeout=600)


def _print(obj) -> None:
    print(json.dumps(obj, indent=2, default=str))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="knowledge-store", description=__doc__.split("\n\n")[0])
    ap.add_argument("--lake", default=os.environ.get("LAKE_URI"))
    ap.add_argument("--model", default=os.environ.get("EXTRACTION_MODEL_ID", DEFAULT_MODEL))
    ap.add_argument("-c", "--collection", default=os.environ.get("COLLECTION"),
                    help="the collection to work on (default: default; run sweeps them all unless one is given)")
    ap.add_argument("-v", "--verbose", action="store_true")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("run")
    sub.add_parser("ingest")
    p = sub.add_parser("refine")
    p.add_argument("--reparse", action="store_true")
    p = sub.add_parser("extract")
    p.add_argument("--limit", type=int)
    p.add_argument("--workers", type=int, default=4)
    p.add_argument("--retry-rejected", action="store_true")
    p.add_argument("--all-delta", action="store_true")
    sub.add_parser("project")
    p = sub.add_parser("discover")
    p.add_argument("--sample", type=int, default=20)
    p.add_argument("--resamples", type=int, default=2)
    p.add_argument("--seed", type=int, default=7)
    p.add_argument("--target", type=int, default=15)
    o = sub.add_parser("ontology").add_subparsers(dest="ocmd", required=True)
    o.add_parser("versions")
    o.add_parser("active")
    p = o.add_parser("pull")
    p.add_argument("ref")
    p.add_argument("dir")
    p = o.add_parser("diff")
    p.add_argument("dir")
    p = o.add_parser("publish")
    p.add_argument("dir")
    p.add_argument("--activate", action="store_true")
    p.add_argument("--note", default="")
    p.add_argument("--by", default=os.environ.get("USER") or os.environ.get("USERNAME") or "")
    p.add_argument("--full", action="store_true", help="treat an additive change as needing full re-extraction")
    p = o.add_parser("activate")
    p.add_argument("version")
    p = o.add_parser("render")
    p.add_argument("dir")
    p.add_argument("out")
    p = sub.add_parser("candidates")
    p.add_argument("--min-docs", type=int, default=2)
    p.add_argument("--propose", action="store_true")
    sub.add_parser("status")
    sub.add_parser("collections")
    args = ap.parse_args(argv)
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO,
                        format="%(asctime)s %(name)s %(levelname)s %(message)s")
    for noisy in ("botocore", "urllib3", "httpx", "rdflib", "pyshacl", "anthropic"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
    if not args.lake and not (args.cmd == "ontology" and args.ocmd == "render"):
        ap.error("--lake or LAKE_URI is required")
    root = store_from_uri(args.lake or ".")
    from . import collections
    lake = collections.scoped(root, args.collection or collections.DEFAULT_ID)
    ledger.set_run(args.cmd, None)

    from .ontology import candidates, discover, model, versions
    from .pipeline import extract, ingest, project, refine, run

    if args.cmd == "run":
        if os.environ.get("LAKE_QUEUE_URL"):  # an Azure job started by upload notifications
            from .hosts.azure import drain
            logging.getLogger("cli").info("drained %d upload notifications", drain())
        _print(run.run(root, _client, args.model, [args.collection] if args.collection else None))
    elif args.cmd == "ingest":
        out = {}
        for s in load_sources(lake):
            stats, _ = ingest.ingest_source(lake, s)
            out[s.name] = stats.as_dict()
        _print(out)
    elif args.cmd == "refine":
        rows = refine.refine_all(lake, reparse=args.reparse)
        _print({"refined": sum(r["status"] == "refined" for r in rows), "rows": rows[:50]})
    elif args.cmd == "extract":
        rows = extract.extract_all(lake, _client(), args.model, load_profile(lake), workers=args.workers,
                                   limit=args.limit, retry_rejected=args.retry_rejected, all_delta=args.all_delta)
        _print([{k: r.get(k) for k in ("doc_id", "status", "counts", "candidates", "repairs", "error", "reason")}
                for r in rows])
    elif args.cmd == "project":
        _print(project.project(lake))
    elif args.cmd == "discover":
        r = discover.discover(_client(), args.model, lake, load_profile(lake), sample=args.sample,
                              resamples=args.resamples, seed=args.seed, target_classes=args.target)
        _print({k: r[k] for k in ("draft_id", "counts", "stability_jaccard", "usage")})
        print(f"\nCurate it: knowledge-store ontology pull {r['draft_id']} <dir>", file=sys.stderr)
    elif args.cmd == "ontology":
        if args.ocmd == "versions":
            _print([versions.manifest(lake, v) | {"active": v == versions.active_version(lake)}
                    for v in versions.published_versions(lake)])
        elif args.ocmd == "active":
            print(versions.active_version(lake) or "(none)")
        elif args.ocmd == "pull":
            d = Path(args.dir)
            d.mkdir(parents=True, exist_ok=True)
            pre = (f"{layout.ONTOLOGY_DRAFTS}/{args.ref}" if lake.exists(f"{layout.ONTOLOGY_DRAFTS}/{args.ref}/ontology.ttl")
                   else layout.ontology_version_prefix(args.ref))
            for name in ("ontology.ttl", "shapes.ttl", "report.json", "manifest.json"):
                if lake.exists(f"{pre}/{name}"):
                    (d / name).write_bytes(lake.get(f"{pre}/{name}"))
            print(f"wrote {d}")
        elif args.ocmd == "diff":
            new = model.load(Path(args.dir) / "ontology.ttl")
            active = versions.active_version(lake)
            if not active:
                _print({"kind": "initial", "version": new.version})
            else:
                old, _ = versions.load_version(lake, active)
                d = versions.diff(old, new)
                _print({"from": active, "to": new.version, **d.to_dict(), "required_bump": versions.required_bump(d.kind)})
        elif args.ocmd == "publish":
            _print(versions.publish(lake, args.dir, by=args.by, note=args.note, activate=args.activate,
                                    force_full=args.full))
        elif args.ocmd == "render":
            from .ontology import renditions
            spec, ttl, shapes = renditions.read_master(args.dir)
            for path in renditions.write_local(renditions.render_all(spec, ttl, shapes), args.out):
                print(path)
        elif args.ocmd == "activate":
            versions.activate_version(lake, args.version)
            print(f"active: {args.version}")
    elif args.cmd == "candidates":
        if args.propose:
            _print(candidates.propose_revision(_client(), args.model, lake, load_profile(lake), min_docs=args.min_docs))
        else:
            v = versions.active_version(lake)
            if not v:
                ap.error("no active ontology")
            reg = candidates.build_register(lake, v)
            _print([{k: t[k] for k in ("kind", "term", "docs", "covered_by", "nearest")} for t in reg["terms"][:50]])
    elif args.cmd == "collections":
        _print([{"id": c, "status": (json.loads(collections.scoped(root, c).get(layout.STATUS))
                                     if collections.scoped(root, c).exists(layout.STATUS) else {"stage": "never_run"}).get("stage")}
                for c in collections.ids(root)])
    elif args.cmd == "status":
        _print(json.loads(lake.get(layout.STATUS)) if lake.exists(layout.STATUS) else {"stage": "never_run"})
    return 0


if __name__ == "__main__":
    sys.exit(main())
