"""The Store port's contract, beyond tests/platform_services/contracts/test_ports.py: the JSON
helpers, PrefixStore's whole port, uris, and each adapter's edges."""

import pytest

from knowledge_store.platform_services.adapters.store import LocalStore, S3Store, store_from_uri
from knowledge_store.platform_services.ports import PrefixStore, get_json, put_json


@pytest.fixture(params=["local", "s3", "prefix-local", "prefix-s3"])
def store(request, tmp_path, monkeypatch):
    kind = request.param
    if kind.endswith("local"):
        inner = LocalStore(tmp_path)
        yield PrefixStore(inner, "collections/c") if kind.startswith("prefix") else inner
        return
    pytest.importorskip("moto", reason="the aws extra is not installed")
    import boto3
    from moto import mock_aws
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")
    with mock_aws():
        boto3.client("s3").create_bucket(Bucket="lake")
        inner = S3Store("lake")
        yield PrefixStore(inner, "collections/c/") if kind.startswith("prefix") else inner


def test_json_round_trips(store):
    put_json(store, "config/x.json", {"a": [1, 2], "b": None})
    assert get_json(store, "config/x.json") == {"a": [1, 2], "b": None}


def test_json_writes_values_it_cannot_encode_as_text(store):
    import datetime as dt

    put_json(store, "x.json", {"when": dt.date(2024, 1, 2)})
    assert get_json(store, "x.json") == {"when": "2024-01-02"}


def test_getting_a_missing_key_raises(store):
    with pytest.raises(Exception):
        store.get("nothing/here")


def test_a_key_that_was_never_written_does_not_exist(store):
    assert not store.exists("nothing/here")


def test_objects_lists_keys_with_etags_under_a_prefix(store):
    store.put("silver/a.json", b"1")
    store.put("silver/b.json", b"22")
    store.put("gold/c", b"3")
    got = dict(store.objects("silver/"))
    assert set(got) == {"silver/a.json", "silver/b.json"}
    assert all(isinstance(e, str) and e for e in got.values())


def test_put_overwrites(store):
    store.put("k", b"one")
    store.put("k", b"two")
    assert store.get("k") == b"two"


def test_put_if_absent_writes_the_body_once(store):
    assert store.put_if_absent("locks/p.json", b"first")
    assert not store.put_if_absent("locks/p.json", b"second")
    assert store.get("locks/p.json") == b"first"


def test_uri_names_the_key(store):
    assert store.uri("silver/a.json").endswith("silver/a.json")


def test_a_prefix_store_hides_its_prefix_and_keeps_the_whole_lake(tmp_path):
    lake = LocalStore(tmp_path)
    c = PrefixStore(lake, "collections/c")
    assert c.prefix == "collections/c/" and c.whole is lake
    nested = PrefixStore(c, "sub")
    assert nested.whole is lake
    c.put("x", b"1")
    assert list(c.objects(""))[0][0] == "x"
    assert c.uri("x") == lake.uri("collections/c/x")
    c.delete("x")
    assert not lake.exists("collections/c/x")


def test_local_list_of_a_missing_folder_is_empty(tmp_path):
    assert list(LocalStore(tmp_path).list("no/such/")) == []


def test_local_list_of_the_root_lists_everything(tmp_path):
    s = LocalStore(tmp_path)
    s.put("a", b"1")
    s.put("b/c", b"2")
    assert list(s.list("")) == ["a", "b/c"]


def test_local_uri_is_a_file_uri(tmp_path):
    assert LocalStore(tmp_path).uri("a").startswith("file://")


def test_store_from_uri_reads_an_s3_uri(monkeypatch):
    pytest.importorskip("moto", reason="the aws extra is not installed")
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")
    s = store_from_uri("s3://lake/ignored/path")
    assert isinstance(s, S3Store) and s.bucket == "lake" and s.uri("k") == "s3://lake/k"


def test_store_from_uri_reads_a_path(tmp_path):
    assert isinstance(store_from_uri(str(tmp_path)), LocalStore)


class _Failing:
    """An S3 client whose head_object and put_object fail with a given code."""

    def __init__(self, code):
        from botocore.exceptions import ClientError

        self.err = ClientError({"Error": {"Code": code}}, "op")

    def head_object(self, **_):
        raise self.err

    def put_object(self, **_):
        raise self.err


def test_s3_exists_raises_errors_other_than_not_found():
    pytest.importorskip("botocore")
    with pytest.raises(Exception):
        S3Store("lake", client=_Failing("AccessDenied")).exists("k")


def test_s3_exists_is_false_for_not_found():
    pytest.importorskip("botocore")
    assert S3Store("lake", client=_Failing("404")).exists("k") is False


def test_s3_put_if_absent_is_false_on_a_precondition_failure():
    pytest.importorskip("botocore")
    assert S3Store("lake", client=_Failing("PreconditionFailed")).put_if_absent("k", b"") is False


def test_s3_put_if_absent_raises_other_errors():
    pytest.importorskip("botocore")
    with pytest.raises(Exception):
        S3Store("lake", client=_Failing("AccessDenied")).put_if_absent("k", b"")
