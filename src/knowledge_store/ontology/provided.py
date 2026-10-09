"""A provided ontology: bring your own instead of discovering one.

A collection whose configuration holds an ontology (config/ontology/ontology.ttl, and optionally
shapes.ttl, put there by Terraform from the collection's ontology_dir) never runs discovery. The
sweep publishes the provided ontology as the version its owl:versionInfo names, with every check
a publish makes, and activates it; extraction then runs against it in the same sweep.

The provided files are the master, kept in the deployer's own repository. To change the ontology,
edit them, bump owl:versionInfo and apply: the next sweep publishes the new version, and the bump
says what it costs (a patch re-extracts nothing, a minor extracts the new terms, a major
re-extracts everything; see versions.py). Published versions are immutable, so a provided file
that changed while its version did not is refused, and the collection's status says why.

Without shapes.ttl, shapes are generated from the ontology, as for a discovered draft.
"""

from __future__ import annotations

import hashlib
import logging
import tempfile
from pathlib import Path

from .. import layout
from ..store import Store
from . import model, versions, writer

log = logging.getLogger("provided")

ONTOLOGY_KEY = f"{layout.CONFIG_ONTOLOGY}/ontology.ttl"
SHAPES_KEY = f"{layout.CONFIG_ONTOLOGY}/shapes.ttl"
MAPPING_KEY = f"{layout.CONFIG_ONTOLOGY}/mappings.yaml"
METRICS_KEY = f"{layout.CONFIG_ONTOLOGY}/metrics.osi.yaml"
_EXTRA = (("mappings.yaml", MAPPING_KEY), ("metrics.osi.yaml", METRICS_KEY))


def _semver(v: str) -> tuple[int, ...]:
    return tuple(int(x) for x in v.split("."))


def present(lake: Store) -> bool:
    return lake.exists(ONTOLOGY_KEY)


def apply(lake: Store) -> dict | None:
    """Publish and activate the provided ontology if it is new; None if there is none.
    Raises ValueError when it cannot be used, with the reason the collection's status shows."""
    if not present(lake):
        return None
    ttl = lake.get(ONTOLOGY_KEY)
    shapes = lake.get(SHAPES_KEY) if lake.exists(SHAPES_KEY) else None
    try:
        spec = model.load(data=ttl.decode())
    except Exception as e:
        raise ValueError(f"the provided ontology does not parse as Turtle: {e}") from e
    version = spec.version
    if not versions.SEMVER.match(version or ""):
        raise ValueError(f"the provided ontology needs owl:versionInfo set to a version X.Y.Z, not {version!r}")
    active = versions.active_version(lake)
    pre = layout.ontology_version_prefix(version)
    if lake.exists(f"{pre}/manifest.json"):
        published = versions.manifest(lake, version)["sha256"]["ontology.ttl"]
        if published != hashlib.sha256(ttl).hexdigest():
            raise ValueError(f"the provided ontology changed but its owl:versionInfo is still {version}, which is "
                             "published and immutable: bump the version")
        for name, key in _EXTRA:
            if not lake.exists(key):
                continue
            digest = hashlib.sha256(lake.get(key)).hexdigest()
            recorded = (versions.manifest(lake, version).get("sha256") or {}).get(name)
            if recorded and recorded != digest:
                raise ValueError(f"the provided {name} changed but owl:versionInfo is still {version}, which is "
                                 "published and immutable: bump the version")
        if active != version and (active is None or _semver(version) > _semver(active)):
            versions.activate_version(lake, version)
            log.info("activated provided ontology %s", version)
            return {"version": version, "action": "activated"}
        return {"version": version, "action": "current" if active == version else "published, not active"}
    newer = active is None or _semver(version) > _semver(active)
    if not newer:
        raise ValueError(f"the provided ontology is {version}, older than the active {active}: bump it past {active}")
    with tempfile.TemporaryDirectory() as tmp:
        Path(tmp, "ontology.ttl").write_bytes(ttl)
        Path(tmp, "shapes.ttl").write_bytes(shapes if shapes is not None else writer.shapes_ttl(spec).encode())
        for name, key in _EXTRA:
            if lake.exists(key):
                Path(tmp, name).write_bytes(lake.get(key))
        m = versions.publish(lake, tmp, by="configuration (ontology_dir)",
                             note="provided ontology" + ("" if shapes is not None else "; shapes generated"),
                             activate=True)
    log.info("published provided ontology %s (%s)", version, m["kind"])
    return {"version": version, "action": "published", "kind": m["kind"]}
