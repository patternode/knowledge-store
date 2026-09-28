"""A directory on this machine: for local runs, demos and tests.

Options:
    path     the directory
    pattern  glob, default "**/*"
"""

from __future__ import annotations

from pathlib import Path
from typing import ClassVar

from ..config import SourceConfig
from ..store import Store
from .base import SourceItem


class LocalDirAdapter:
    type: ClassVar[str] = "local_dir"

    def __init__(self, source: SourceConfig, lake: Store):
        self.root = Path(source.options["path"]).resolve()
        self.pattern = source.options.get("pattern", "**/*")

    def items(self):
        for p in sorted(self.root.glob(self.pattern)):
            if not p.is_file() or p.name.startswith("."):
                continue
            st = p.stat()
            rel = p.relative_to(self.root).as_posix()
            yield SourceItem(key=rel, version=f"{st.st_size}-{st.st_mtime_ns}", name=p.name, uri=p.as_uri())

    def fetch(self, item):
        return (self.root / item.key).read_bytes()
