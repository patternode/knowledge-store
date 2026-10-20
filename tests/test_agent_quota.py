"""The agent's own per-person daily limit (agent/quota.py): it holds when the Runtime is called
directly with a person's token, counts apart from the portal's quota, and is off when unset."""

import base64
import json

import pytest

boto3 = pytest.importorskip("boto3")
moto = pytest.importorskip("moto")

from knowledge_store.apps import agent as app
from knowledge_store.access.adapters import agent_quota as quota  # noqa: E402
from knowledge_store.access.adapters.state import DynamoState  # noqa: E402


def jwt(**claims) -> str:
    part = base64.urlsafe_b64encode(json.dumps(claims).encode()).rstrip(b"=").decode()
    return f"eyJhbGciOiJSUzI1NiJ9.{part}.sig"


@pytest.fixture
def table(monkeypatch):
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")
    with moto.mock_aws():
        ddb = boto3.resource("dynamodb")
        t = ddb.create_table(TableName="ks-chat", KeySchema=[{"AttributeName": "pk", "KeyType": "HASH"}],
                             AttributeDefinitions=[{"AttributeName": "pk", "AttributeType": "S"}],
                             BillingMode="PAY_PER_REQUEST")
        yield t


def test_limit_per_subject_per_day(table):
    q = quota.AgentQuota("ks-chat", 2, table=table)
    alice, bob = jwt(sub="alice", client_id="web"), jwt(sub="bob", client_id="web")
    assert q.check(alice, "2026-10-14") is None
    assert q.check(alice, "2026-10-14") is None
    assert q.check(alice, "2026-10-14") == quota.LIMIT_REACHED
    assert q.check(bob, "2026-10-14") is None          # another person has their own count
    assert q.check(alice, "2026-10-15") is None        # and a new day starts again
    row = table.get_item(Key={"pk": "agent#alice#2026-10-14"})["Item"]
    assert int(row["n"]) == 2 and int(row["expires_at"]) > 0


def test_separate_from_the_portal_quota(table):
    portal = DynamoState("ks-chat", table=table)
    q = quota.AgentQuota("ks-chat", 1, table=table)
    assert portal.take_quota("alice", "2026-10-14", 1)
    assert q.check(jwt(sub="alice"), "2026-10-14") is None   # the portal's count is not the agent's
    assert not portal.take_quota("alice", "2026-10-14", 1)
    assert int(table.get_item(Key={"pk": "quota#alice#2026-10-14"})["Item"]["n"]) == 1


def test_no_subject_is_refused_and_service_clients_are_exempt(table):
    q = quota.AgentQuota("ks-chat", 1, exempt_clients=["site-public-id"], table=table)
    assert q.check("not-a-jwt") is not None
    assert q.check(jwt(client_id="web")) is not None
    for _ in range(3):  # the portal's service client: the portal has already counted the person
        assert q.check(jwt(sub="site-public-id", client_id="site-public-id")) is None
    assert "Items" not in table.scan() or not table.scan()["Items"]


def test_off_when_unset(monkeypatch):
    monkeypatch.delenv("AGENT_QUOTA_TABLE", raising=False)
    monkeypatch.setenv("AGENT_DAILY_INVOCATIONS", "60")
    assert quota.AgentQuota.from_env() is None
    monkeypatch.setenv("AGENT_QUOTA_TABLE", "ks-chat")
    monkeypatch.setenv("AGENT_DAILY_INVOCATIONS", "0")
    assert quota.AgentQuota.from_env() is None
    assert app.admit(jwt(sub="alice"), None) is None


def test_from_env(table, monkeypatch):
    monkeypatch.setenv("AGENT_QUOTA_TABLE", "ks-chat")
    monkeypatch.setenv("AGENT_DAILY_INVOCATIONS", "60")
    monkeypatch.setenv("AGENT_QUOTA_EXEMPT_CLIENTS", "a, b")
    q = quota.AgentQuota.from_env()
    assert q.limit == 60 and q.exempt == {"a", "b"}


class Broken:
    def update_item(self, **_):
        raise RuntimeError("no table")


def test_a_limit_that_cannot_be_checked_refuses():
    assert app.admit(jwt(sub="alice"), quota.AgentQuota("t", 5, table=Broken()))


def test_the_entrypoint_refuses_past_the_limit(table, monkeypatch):
    pytest.importorskip("bedrock_agentcore")
    q = quota.AgentQuota("ks-chat", 1, table=table)
    calls = []

    class Tools:
        def __init__(self, url, token):
            calls.append(token)

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

    monkeypatch.setattr(app, "GatewayTools", Tools)
    monkeypatch.setattr(app, "run", lambda payload, tools, **_: {"answer": "ok"})
    monkeypatch.setenv("GATEWAY_MCP_URL", "https://gateway.example")
    invoke = app.make_app(quota=q).handlers["main"]

    class Ctx:
        request_headers = {"Authorization": "Bearer " + jwt(sub="alice", client_id="web")}

    payload = {"question": "q", "collection": "c", "sub": "someone-else"}  # a body field never names the caller
    assert invoke(payload, Ctx()) == {"answer": "ok"}
    refused = invoke(payload, Ctx())
    assert refused["error"] == quota.LIMIT_REACHED and len(calls) == 1
    assert table.get_item(Key={"pk": f"agent#alice#{quota.today()}"})["Item"]["n"] == 1
