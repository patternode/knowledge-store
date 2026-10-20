"""Platform services' ports: the object store every context reads and writes the lake through.

Every job reads and writes through Store so that the whole pipeline runs locally against a
directory (tests, dry runs) and in S3 unchanged. Beyond put/get/list: objects() (keys with etags,
so adapters can skip unchanged objects without reading them), put_if_absent() (the pipeline lock)
and delete(). PrefixStore and the JSON helpers work on any Store, so they live with the port.
"""

from __future__ import annotations

import json
from typing import Iterator, Protocol


class Store(Protocol):
    def put(self, key: str, body: bytes, content_type: str = "application/octet-stream") -> None: ...
    def get(self, key: str) -> bytes: ...
    def exists(self, key: str) -> bool: ...
    def list(self, prefix: str) -> Iterator[str]: ...
    def objects(self, prefix: str) -> Iterator[tuple[str, str]]: ...
    def put_if_absent(self, key: str, body: bytes) -> bool: ...
    def delete(self, key: str) -> None: ...
    def uri(self, key: str) -> str: ...


def put_json(store: Store, key: str, obj) -> None:
    store.put(key, json.dumps(obj, indent=2, default=str).encode(), "application/json")


def get_json(store: Store, key: str):
    return json.loads(store.get(key))


class PrefixStore:
    """A view of another store under a key prefix: how each collection gets a lake of its own
    (collections/<id>/...) with the same layout, so no step needs to know collections exist.
    whole is the whole lake, for what spans collections (adapters reading landing/, the lock)."""

    def __init__(self, inner: Store, prefix: str):
        self.inner = inner
        self.prefix = prefix if prefix.endswith("/") else prefix + "/"
        self.whole = getattr(inner, "whole", inner)

    def _k(self, key: str) -> str:
        return self.prefix + key

    def put(self, key, body, content_type="application/octet-stream"):
        self.inner.put(self._k(key), body, content_type)

    def get(self, key):
        return self.inner.get(self._k(key))

    def exists(self, key):
        return self.inner.exists(self._k(key))

    def list(self, prefix):
        n = len(self.prefix)
        for k in self.inner.list(self._k(prefix)):
            yield k[n:]

    def objects(self, prefix):
        n = len(self.prefix)
        for k, etag in self.inner.objects(self._k(prefix)):
            yield k[n:], etag

    def put_if_absent(self, key, body):
        return self.inner.put_if_absent(self._k(key), body)

    def delete(self, key):
        self.inner.delete(self._k(key))

    def uri(self, key):
        return self.inner.uri(self._k(key))


class ModelClient(Protocol):
    """A model call: the Bedrock runtime client, or AnthropicConverse for the Anthropic API
    (adapters.llm.runtime_client returns whichever LLM_PROVIDER names).

    Its request and response follow Bedrock's Converse shape (modelId, messages, system,
    toolConfig, inferenceConfig; output.message.content, stopReason, usage). That is a vendor's
    shape, which ADR-046 point 5 says a port should not be; it is kept because every caller and
    the cost ledger already speak it, and AnthropicConverse translates it. Replacing it with a
    request shaped by the domain is recorded as follow-up work.
    """

    def converse(self, **request) -> dict: ...

