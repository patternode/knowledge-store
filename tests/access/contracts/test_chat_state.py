"""ChatState adapters beyond the shared contract (tests/platform_services/contracts/test_ports.py):
choosing one from the environment, DynamoDB's batched usage writes, and MongoDB's escaping and races."""

from __future__ import annotations

import datetime as dt

import pytest

from knowledge_store.access.adapters import state


@pytest.fixture
def dynamo(monkeypatch):
    pytest.importorskip("moto")
    import boto3
    from moto import mock_aws
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")
    with mock_aws():
        boto3.client("dynamodb").create_table(TableName="chat", BillingMode="PAY_PER_REQUEST",
                                              KeySchema=[{"AttributeName": "pk", "KeyType": "HASH"}],
                                              AttributeDefinitions=[{"AttributeName": "pk", "AttributeType": "S"}])
        yield state.DynamoState("chat")


def test_the_default_state_is_dynamodb_on_the_named_table(dynamo, monkeypatch):
    monkeypatch.delenv("CHAT_STATE", raising=False)
    monkeypatch.setenv("CHAT_TABLE", "chat")
    s = state.from_env()
    assert isinstance(s, state.DynamoState) and s.t.name == "chat"


def test_mongodb_state_connects_to_the_named_database(monkeypatch):
    pytest.importorskip("pymongo")
    monkeypatch.setenv("CHAT_STATE", "mongodb")
    monkeypatch.setenv("MONGODB_URI", "mongodb://127.0.0.1:1")
    monkeypatch.setenv("MONGODB_DB", "ks_unit")
    s = state.from_env()  # pymongo connects lazily, so nothing is reached
    assert isinstance(s, state.MongoState) and s.chat.database.name == "ks_unit"
    s.chat.database.client.close()


def test_more_counters_than_one_update_holds_are_written_in_batches(dynamo):
    counters = {f"classes|T{i}|read": 1 for i in range(170)}
    dynamo.add_usage("m", ["all"], counters)
    dynamo.add_usage("m", ["all"], {"classes|T0|read": 2})
    got = dynamo.get_usage("m", "all")
    assert len(got) == 170 and got["classes|T0|read"] == 3


def test_a_chat_is_kept_as_json_with_its_owner(dynamo):
    dynamo.put_chat("q1", "alice", {"at": dt.date(2026, 10, 20)})
    assert dynamo.get_chat("q1") == {"sub": "alice", "body": {"at": "2026-10-20"}}


def test_a_dynamodb_error_other_than_the_limit_is_raised():
    pytest.importorskip("botocore")
    from botocore.exceptions import ClientError

    class Failing:
        def update_item(self, **kw):
            raise ClientError({"Error": {"Code": "ProvisionedThroughputExceededException"}}, "UpdateItem")

    with pytest.raises(ClientError):
        state.DynamoState("t", table=Failing()).take_quota("alice", "2026-10-20", 5)


@pytest.mark.parametrize("name", ["classes|Odd.Name$|read", "100%|x", "plain"])
def test_mongo_field_names_escape_and_return(name):
    field = state.MongoState._field(name)
    assert "." not in field and "$" not in field
    assert state.MongoState._unfield(field) == name


def test_mongo_counts_the_loser_of_a_first_question_race():
    pytest.importorskip("pymongo")
    from pymongo.errors import DuplicateKeyError

    class Quota:
        def __init__(self):
            self.calls = []

        def find_one_and_update(self, key, update, upsert=False, return_document=None):
            self.calls.append(upsert)
            if upsert:
                raise DuplicateKeyError("taken")
            return {"n": 2}

    s = state.MongoState({"chat": None, "quota": Quota(), "usage": None})
    assert s.take_quota("alice", "2026-10-20", 5) is True and s.quota.calls == [True, False]


def test_mongo_refuses_at_the_limit():
    pytest.importorskip("pymongo")
    from pymongo.errors import DuplicateKeyError

    class Full:
        def find_one_and_update(self, key, update, upsert=False, return_document=None):
            if upsert:
                raise DuplicateKeyError("taken")
            return None

    assert state.MongoState({"chat": None, "quota": Full(), "usage": None}).take_quota("a", "d", 1) is False


def test_mongo_reads_a_naive_expiry_as_utc():
    class Coll:
        def find_one(self, flt):
            return {"_id": "q", "sub": "a", "body": "{}", "expires_at": dt.datetime.utcnow() + dt.timedelta(hours=1)}

    assert state.MongoState({"chat": Coll(), "quota": None, "usage": None}).get_chat("q") == {"sub": "a", "body": {}}


def test_mongo_usage_round_trips_through_escaped_fields():
    class Usage:
        def __init__(self):
            self.docs = {}

        def update_one(self, flt, update, upsert):
            row = self.docs.setdefault(flt["_id"], {"c": {}})
            for k, v in update["$inc"].items():
                f = k.split(".", 1)[1]
                row["c"][f] = row["c"].get(f, 0) + v

        def find_one(self, flt):
            return self.docs.get(flt["_id"])

    s = state.MongoState({"chat": None, "quota": None, "usage": Usage()})
    s.add_usage("m", ["all", "2026-10"], {"classes|A.b|read": 1, "questions": 1})
    assert s.get_usage("m", "2026-10") == {"classes|A.b|read": 1, "questions": 1}
    assert s.get_usage("m", "none") == {}


def test_memory_state_copies_what_it_is_given():
    s = state.MemoryState()
    body = {"steps": [1]}
    s.put_chat("q", "a", body)
    body["steps"].append(2)
    assert s.get_chat("q")["body"] == {"steps": [1]}
