"""Where runs and baselines are kept: a local folder, or the lake (under private/, since a run
holds the answers and the passages they cite)."""

from __future__ import annotations

import json
from pathlib import Path


class DirRunStore:
    def __init__(self, root: str | Path):
        self.root = Path(root)

    def save(self, name: str, run: dict, report: str) -> str:
        d = self.root / name
        d.mkdir(parents=True, exist_ok=True)
        (d / "results.json").write_text(json.dumps(run, indent=1, default=str), encoding="utf-8")
        (d / "report.md").write_text(report, encoding="utf-8")
        return str(d)

    def _baseline(self, set_name: str) -> Path:
        return self.root / "baselines" / f"{set_name}.json"

    def baseline(self, set_name: str) -> dict | None:
        p = self._baseline(set_name)
        return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None

    def keep_as_baseline(self, set_name: str, run: dict) -> None:
        p = self._baseline(set_name)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(run, indent=1, default=str), encoding="utf-8")


class LakeRunStore:
    """Runs under <prefix>/<name>/ in a Store; baselines under <prefix>/baselines/."""

    def __init__(self, store, prefix: str = "private/evals"):
        self.store, self.prefix = store, prefix.rstrip("/")

    def save(self, name: str, run: dict, report: str) -> str:
        key = f"{self.prefix}/{name}"
        self.store.put(f"{key}/results.json", json.dumps(run, indent=1, default=str).encode(), "application/json")
        self.store.put(f"{key}/report.md", report.encode(), "text/markdown")
        return self.store.uri(key)

    def baseline(self, set_name: str) -> dict | None:
        key = f"{self.prefix}/baselines/{set_name}.json"
        return json.loads(self.store.get(key)) if self.store.exists(key) else None

    def keep_as_baseline(self, set_name: str, run: dict) -> None:
        self.store.put(f"{self.prefix}/baselines/{set_name}.json", json.dumps(run, indent=1, default=str).encode(),
                       "application/json")
