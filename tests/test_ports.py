"""The ports each cloud plugs into: object stores, model providers, claims and chat state.

One contract per port, run against every adapter. Local, S3 (moto) and in-memory adapters always
run; MongoDB runs against the emulators in tests/emulators.yml when
their variables are set, and are skipped otherwise.
"""

from __future__ import annotations

import os
import threading
import uuid

import pytest

from knowledge_store import claims, ledger, llm
from knowledge_store.portal_api import state
from knowledge_store.store import LocalStore, PrefixStore, S3Store, store_from_uri

# --- object stores ------------------------------------------------------------------------


@pytest.fixture(params=["local", "s3"])
def store(request, tmp_path, monkeypatch):
    kind = request.param
    if kind == "local":
        yield LocalStore(tmp_path)
    elif kind == "s3":
        pytest.importorskip("moto", reason="the aws extra is not installed")
        import boto3
        from moto import mock_aws
        monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")
        with mock_aws():
            boto3.client("s3").create_bucket(Bucket="lake")
            yield S3Store("lake")


def test_store_put_get_exists_delete(store):
    store.put("a/b.json", b'{"x": 1}', "application/json")
    assert store.exists("a/b.json") and store.get("a/b.json") == b'{"x": 1}'
    store.delete("a/b.json")
    assert not store.exists("a/b.json")
    store.delete("a/b.json")  # deleting what is not there is not an error


def test_store_list_has_s3_prefix_semantics(store):
    for k in ("gold/1.0.0/x", "gold/1.0.0/y/z", "gold/1.0.10/x", "silver/x"):
        store.put(k, b"1")
    assert sorted(store.list("gold/1.0.0/")) == ["gold/1.0.0/x", "gold/1.0.0/y/z"]
    assert sorted(store.list("gold/1.0.")) == ["gold/1.0.0/x", "gold/1.0.0/y/z", "gold/1.0.10/x"]
    assert list(store.list("nothing/")) == []


def test_store_etag_changes_with_content(store):
    store.put("landing/a.md", b"one")
    first = dict(store.objects("landing/"))
    store.put("landing/a.md", b"two, longer")
    second = dict(store.objects("landing/"))
    assert set(first) == {"landing/a.md"} and first["landing/a.md"] != second["landing/a.md"]


def test_store_put_if_absent_has_one_winner(store):
    wins = []
    threads = [threading.Thread(target=lambda: wins.append(store.put_if_absent("lock", b"{}"))) for _ in range(6)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert wins.count(True) == 1
    assert store.put_if_absent("lock", b"{}") is False


def test_prefix_store_over_each_adapter(store):
    c = PrefixStore(store, "collections/m")
    c.put("silver/d.json", b"{}")
    assert list(c.list("silver/")) == ["silver/d.json"]
    assert store.exists("collections/m/silver/d.json")
    assert c.uri("silver/d.json").endswith("collections/m/silver/d.json")


def test_store_from_uri(monkeypatch, tmp_path):
    assert isinstance(store_from_uri(str(tmp_path)), LocalStore)


# --- model providers ----------------------------------------------------------------------


def test_providers_share_the_messages_path(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "anthropic")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    client = llm.runtime_client()
    assert isinstance(client._inner, llm.AnthropicConverse) and client._provider == "anthropic"
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    with pytest.raises(ValueError):
        llm.provider()


def test_dated_model_ids():
    assert llm.rejects_sampling("claude-sonnet-5@20260101")
    assert ledger.price_key("claude-sonnet-4-5@20250929") == "claude-sonnet-4-5"
    assert llm.model_name("us.anthropic.claude-sonnet-5") == "claude-sonnet-5"


# --- claims -------------------------------------------------------------------------------


def test_claims_default_to_cognito(monkeypatch):
    for v in ("SUBJECT_CLAIM", "GROUPS_CLAIM", "PRIVATE_GROUP", "SCOPES_CLAIM", "PRIVATE_SCOPE", "SCOPE_PREFIX"):
        monkeypatch.delenv(v, raising=False)
    assert claims.subject({"sub": "u"}) == "u" and claims.subject({}) == "anonymous"
    assert claims.private_reader({"cognito:groups": "[readers, private-readers]"})
    assert not claims.private_reader({"cognito:groups": ["readers"]})
    assert claims.private_caller({"scope": "knowledge-store/tools.private"})
    assert not claims.private_reader({"scope": "knowledge-store/tools.private"})


def test_claims_are_configurable(monkeypatch):
    monkeypatch.setenv("SUBJECT_CLAIM", "oid,sub")
    monkeypatch.setenv("GROUPS_CLAIM", "roles")
    monkeypatch.setenv("PRIVATE_GROUP", "private-reader")
    monkeypatch.setenv("SCOPES_CLAIM", "roles,scp")
    monkeypatch.setenv("PRIVATE_SCOPE", "tools.private")
    person = {"oid": "o-1", "sub": "pairwise", "roles": ["private-reader"], "scp": "tools.public"}
    app = {"oid": "o-2", "roles": ["tools.private"]}
    assert claims.subject(person) == "o-1"
    assert claims.private_reader(person) and claims.private_caller(person)
    assert claims.private_caller(app) and not claims.private_reader(app)
    assert not claims.private_caller({"roles": ["tools.public"], "scp": "tools.public"})
    assert not claims.private_caller({"cognito:groups": ["private-reader"]})  # the Cognito claim no longer counts


# --- chat state ---------------------------------------------------------------------------


class _SerialTable:
    """DynamoDB applies writes to one item one at a time; moto's in-memory backend is not thread-safe,
    so concurrent calls race inside it. A lock gives moto the service's guarantee, and the quota test
    still checks that the conditional update admits exactly the limit."""

    def __init__(self, table):
        self._table = table
        self._lock = threading.Lock()

    def __getattr__(self, name):
        attr = getattr(self._table, name)
        if not callable(attr):
            return attr

        def call(*args, **kwargs):
            with self._lock:
                return attr(*args, **kwargs)
        return call


@pytest.fixture(params=["memory", "dynamodb", "mongodb"])
def chat(request, monkeypatch):
    kind = request.param
    if kind == "memory":
        yield state.MemoryState()
    elif kind == "dynamodb":
        pytest.importorskip("moto", reason="the aws extra is not installed")
        import boto3
        from moto import mock_aws
        monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")
        with mock_aws():
            boto3.client("dynamodb").create_table(TableName="chat", BillingMode="PAY_PER_REQUEST",
                                                  KeySchema=[{"AttributeName": "pk", "KeyType": "HASH"}],
                                                  AttributeDefinitions=[{"AttributeName": "pk", "AttributeType": "S"}])
            yield state.DynamoState("chat", table=_SerialTable(boto3.resource("dynamodb").Table("chat")))
    else:
        uri = os.environ.get("MONGODB_TEST_URI")
        if not uri:
            pytest.skip("MONGODB_TEST_URI is not set")
        name = f"ks_test_{uuid.uuid4().hex[:8]}"
        s = state.MongoState.connect(uri, name)
        yield s
        s.chat.database.client.drop_database(name)


def test_chat_round_trip_and_owner(chat):
    chat.put_chat("q1", "alice", {"status": "pending"})
    assert chat.get_chat("q1") == {"sub": "alice", "body": {"status": "pending"}}
    chat.put_chat("q1", "alice", {"status": "done", "answer": "yes", "citations": ["p1"]})
    assert chat.get_chat("q1")["body"]["answer"] == "yes"
    assert chat.get_chat("missing") is None


def test_quota_holds_under_concurrency(chat):
    taken = []
    threads = [threading.Thread(target=lambda: taken.append(chat.take_quota("alice", "2026-09-30", 5)))
               for _ in range(12)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert taken.count(True) == 5
    assert chat.take_quota("alice", "2026-09-30", 5) is False
    assert chat.take_quota("alice", "2026-10-01", 5) is True  # a new day
    assert chat.take_quota("bob", "2026-09-30", 5) is True  # another caller


def test_expired_mongo_chat_reads_as_missing():
    import datetime as dt

    class Coll:
        def __init__(self):
            self.docs = {}

        def replace_one(self, flt, doc, upsert):
            self.docs[flt["_id"]] = doc

        def find_one(self, flt):
            return self.docs.get(flt["_id"])

    s = state.MongoState({"chat": Coll(), "quota": Coll()})
    s.put_chat("q", "alice", {"status": "done"})
    assert s.get_chat("q")
    s.chat.docs["q"]["expires_at"] = dt.datetime.now(dt.timezone.utc) - dt.timedelta(seconds=1)
    assert s.get_chat("q") is None


def test_state_from_env(monkeypatch):
    monkeypatch.setenv("CHAT_STATE", "memory")
    assert isinstance(state.from_env(), state.MemoryState)
    monkeypatch.setenv("CHAT_STATE", "redis")
    with pytest.raises(ValueError):
        state.from_env()
