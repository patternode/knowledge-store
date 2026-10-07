"""Object store port with S3, Azure Blob, Google Cloud Storage and local-filesystem adapters.

Every job reads and writes through this port so that the whole pipeline runs
locally against a directory (tests, dry runs) and in any cloud's object store unchanged.
Each cloud's SDK is imported only by its adapter, so no deployment needs another's.

Beyond put/get/list: objects() (keys with etags, so adapters can skip unchanged objects without reading
them), put_if_absent() (the pipeline lock) and delete().
"""

from __future__ import annotations

import json
import os
from pathlib import Path
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


class LocalStore:
    def __init__(self, root: str | os.PathLike):
        self.root = Path(root)

    def _p(self, key: str) -> Path:
        return self.root / key

    def put(self, key, body, content_type="application/octet-stream"):
        p = self._p(key)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(body)

    def get(self, key):
        return self._p(key).read_bytes()

    def exists(self, key):
        return self._p(key).exists()

    def list(self, prefix):
        """S3 semantics: every key that starts with prefix, not only a directory's contents."""
        parent = prefix.rsplit("/", 1)[0] if "/" in prefix else ""
        base = self._p(parent) if parent else self.root
        if not base.exists():
            return
        for p in sorted(base.rglob("*")):
            if p.is_file():
                key = p.relative_to(self.root).as_posix()
                if key.startswith(prefix):
                    yield key

    def objects(self, prefix):
        """(key, etag) for every key under prefix. The local etag is size and mtime, which
        changes when the file does; that is all an adapter needs from it."""
        for key in self.list(prefix):
            st = self._p(key).stat()
            yield key, f"{st.st_size}-{st.st_mtime_ns}"

    def put_if_absent(self, key, body):
        p = self._p(key)
        p.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(p, "xb") as f:
                f.write(body)
            return True
        except FileExistsError:
            return False

    def delete(self, key):
        self._p(key).unlink(missing_ok=True)

    def uri(self, key):
        return self._p(key).as_uri()


class S3Store:
    def __init__(self, bucket: str, client=None):
        import boto3
        self.bucket = bucket
        self.s3 = client or boto3.client("s3")

    def put(self, key, body, content_type="application/octet-stream"):
        self.s3.put_object(Bucket=self.bucket, Key=key, Body=body, ContentType=content_type)

    def get(self, key):
        return self.s3.get_object(Bucket=self.bucket, Key=key)["Body"].read()

    def exists(self, key):
        from botocore.exceptions import ClientError
        try:
            self.s3.head_object(Bucket=self.bucket, Key=key)
            return True
        except ClientError as e:
            if e.response["Error"]["Code"] in ("404", "NoSuchKey", "NotFound"):
                return False
            raise

    def list(self, prefix):
        pages = self.s3.get_paginator("list_objects_v2").paginate(Bucket=self.bucket, Prefix=prefix)
        for page in pages:
            for obj in page.get("Contents", []):
                yield obj["Key"]

    def objects(self, prefix):
        pages = self.s3.get_paginator("list_objects_v2").paginate(Bucket=self.bucket, Prefix=prefix)
        for page in pages:
            for obj in page.get("Contents", []):
                yield obj["Key"], obj["ETag"].strip('"')

    def put_if_absent(self, key, body):
        """S3 conditional write (If-None-Match: *): exactly one caller wins."""
        from botocore.exceptions import ClientError
        try:
            self.s3.put_object(Bucket=self.bucket, Key=key, Body=body, IfNoneMatch="*",
                               ContentType="application/json")
            return True
        except ClientError as e:
            if e.response["Error"]["Code"] in ("PreconditionFailed", "ConditionalRequestConflict", "412"):
                return False
            raise

    def delete(self, key):
        self.s3.delete_object(Bucket=self.bucket, Key=key)

    def uri(self, key):
        return f"s3://{self.bucket}/{key}"


class BlobStore:
    """Azure Blob Storage: one container is the lake.

    Authenticates with Entra ID (DefaultAzureCredential: the managed identity when deployed), or
    with AZURE_STORAGE_CONNECTION_STRING when set (Azurite, local runs). The account's blob
    endpoint is https://<account>.blob.core.windows.net unless AZURE_STORAGE_BLOB_ENDPOINT names
    another."""

    def __init__(self, account: str, container: str, client=None):
        self.account, self.container = account, container
        if client is None:
            from azure.storage.blob import BlobServiceClient
            conn = os.environ.get("AZURE_STORAGE_CONNECTION_STRING")
            if conn:
                service = BlobServiceClient.from_connection_string(conn)
            else:
                from azure.identity import DefaultAzureCredential
                endpoint = os.environ.get("AZURE_STORAGE_BLOB_ENDPOINT") or f"https://{account}.blob.core.windows.net"
                service = BlobServiceClient(endpoint, credential=DefaultAzureCredential())
            client = service.get_container_client(container)
        self.c = client

    def put(self, key, body, content_type="application/octet-stream"):
        from azure.storage.blob import ContentSettings
        self.c.upload_blob(key, body, overwrite=True, content_settings=ContentSettings(content_type=content_type))

    def get(self, key):
        return self.c.download_blob(key).readall()

    def exists(self, key):
        return self.c.get_blob_client(key).exists()

    def list(self, prefix):
        for b in self.c.list_blobs(name_starts_with=prefix):
            yield b.name

    def objects(self, prefix):
        for b in self.c.list_blobs(name_starts_with=prefix):
            yield b.name, b.etag.strip('"')

    def put_if_absent(self, key, body):
        """A conditional write (If-None-Match: *): exactly one caller wins."""
        from azure.core.exceptions import ResourceExistsError
        from azure.storage.blob import ContentSettings
        try:
            # overwrite=False is the SDK's If-None-Match: *
            self.c.upload_blob(key, body, overwrite=False, content_settings=ContentSettings(content_type="application/json"))
            return True
        except ResourceExistsError:
            return False

    def delete(self, key):
        from azure.core.exceptions import ResourceNotFoundError
        try:
            self.c.delete_blob(key)
        except ResourceNotFoundError:
            pass

    def uri(self, key):
        return f"az://{self.account}/{self.container}/{key}"


class GcsStore:
    """Google Cloud Storage. Authenticates with Application Default Credentials (the service
    account when deployed); STORAGE_EMULATOR_HOST points the client at an emulator."""

    def __init__(self, bucket: str, client=None):
        if client is None:
            from google.cloud import storage
            if os.environ.get("STORAGE_EMULATOR_HOST"):
                from google.auth.credentials import AnonymousCredentials
                client = storage.Client(project=os.environ.get("GOOGLE_CLOUD_PROJECT", "test"),
                                        credentials=AnonymousCredentials())
            else:
                client = storage.Client()
        self.name = bucket
        self.b = client.bucket(bucket)
        self.client = client

    def put(self, key, body, content_type="application/octet-stream"):
        self.b.blob(key).upload_from_string(body, content_type=content_type)

    def get(self, key):
        return self.b.blob(key).download_as_bytes()

    def exists(self, key):
        return self.b.blob(key).exists()

    def list(self, prefix):
        for b in self.client.list_blobs(self.b, prefix=prefix):
            yield b.name

    def objects(self, prefix):
        """The generation, not the etag: it changes when the content does and not when only
        metadata does."""
        for b in self.client.list_blobs(self.b, prefix=prefix):
            yield b.name, str(b.generation)

    def put_if_absent(self, key, body):
        """A conditional write (if_generation_match=0): exactly one caller wins."""
        from google.api_core.exceptions import PreconditionFailed
        try:
            self.b.blob(key).upload_from_string(body, content_type="application/json", if_generation_match=0)
            return True
        except PreconditionFailed:
            return False

    def delete(self, key):
        from google.api_core.exceptions import NotFound
        try:
            self.b.blob(key).delete()
        except NotFound:
            pass

    def uri(self, key):
        return f"gs://{self.name}/{key}"


def store_from_uri(uri: str) -> Store:
    """s3://bucket, az://account/container, gs://bucket or a local path."""
    if uri.startswith("s3://"):
        return S3Store(uri[5:].split("/", 1)[0])
    if uri.startswith("az://"):
        parts = uri[5:].split("/")
        if len(parts) < 2 or not parts[0] or not parts[1]:
            raise ValueError(f"an Azure lake is az://<account>/<container>, not {uri!r}")
        return BlobStore(parts[0], parts[1])
    if uri.startswith("gs://"):
        return GcsStore(uri[5:].split("/", 1)[0])
    return LocalStore(uri)


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
