"""The default source: files people upload to an S3 prefix.

Options:
    prefix   where uploads land; default "landing/". Everything under it is a candidate.
    bucket   read from another bucket than the lake (an existing bucket the deployer owns).
             The pipeline task role must be allowed to read it (kl_extra_read_buckets in tfvars).
    include  optional list of suffixes to take, e.g. [".pdf", ".md"]; default all.

Uploads are never modified or deleted: bronze holds the lab's own copy, so the landing
area stays the uploader's to manage.
"""

from __future__ import annotations

from typing import ClassVar

from ..config import SourceConfig
from ..store import S3Store, Store
from .base import SourceItem


class S3LandingAdapter:
    type: ClassVar[str] = "s3_landing"

    def __init__(self, source: SourceConfig, lake: Store):
        self.source = source
        self.prefix = source.options.get("prefix", "landing/")
        bucket = source.options.get("bucket")
        self.store = S3Store(bucket) if bucket else lake
        self.include = tuple(s.lower() for s in source.options.get("include") or ())

    def items(self):
        for key, etag in self.store.objects(self.prefix):
            name = key.rsplit("/", 1)[-1]
            if not name or key.endswith("/"):
                continue
            if name.startswith(".") or (self.include and not name.lower().endswith(self.include)):
                continue
            rel = key[len(self.prefix):]
            folder = rel.rsplit("/", 1)[0] if "/" in rel else ""
            yield SourceItem(key=key, version=etag, name=name, uri=self.store.uri(key),
                             metadata={"folder": folder} if folder else {})

    def fetch(self, item):
        return self.store.get(item.key)
