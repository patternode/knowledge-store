"""The adapter contract."""

from __future__ import annotations

import mimetypes
from dataclasses import dataclass, field
from typing import ClassVar, Iterator, Protocol

from ..config import SourceConfig
from ..store import Store


@dataclass(frozen=True)
class SourceItem:
    """One item a source holds.

    key: stable identity within the source (an S3 key, a URL, a relative path).
    version: changes whenever the item's content does (an etag, a last-modified stamp).
        Ingest skips an item whose key and version it has already stored.
    name: a file name, used for the extension and as a fallback title.
    metadata: anything the source knows that a reader would want (title, author, date).
    """
    key: str
    version: str
    name: str
    uri: str
    content_type: str | None = None
    metadata: dict = field(default_factory=dict)

    def extension(self) -> str:
        dot = self.name.rfind(".")
        if dot > 0 and len(self.name) - dot <= 6:
            return self.name[dot:].lower()
        return mimetypes.guess_extension(self.content_type or "") or ".bin"


class SourceAdapter(Protocol):
    type: ClassVar[str]

    def __init__(self, source: SourceConfig, lake: Store) -> None: ...

    def items(self) -> Iterator[SourceItem]:
        """Every item the source holds now. Cheap: no content reads."""
        ...

    def fetch(self, item: SourceItem) -> bytes:
        """The item's bytes."""
        ...
