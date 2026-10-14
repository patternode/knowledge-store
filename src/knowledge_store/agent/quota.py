"""The agent's own per-person daily limit on invocations.

The portal counts each person's questions (DAILY_QUESTIONS, portal_api/state.py) before it asks
the agent, but the Runtime accepts the same Cognito access token the portal forwards, so a person
can POST to the Runtime's /invocations directly. This limit holds there too: every invocation
takes one from a counter in the portal's state table, under its own key namespace
("agent#<sub>#<day>", beside the portal's "quota#<sub>#<day>") so the portal's count is never
doubled. It is set somewhat above the portal's limit, so a retry through the portal is not refused.

    AGENT_QUOTA_TABLE          the DynamoDB table (the portal's chat state table); unset: no limit
    AGENT_DAILY_INVOCATIONS    invocations per person per UTC day; 0 or unset: no limit
    AGENT_QUOTA_EXEMPT_CLIENTS comma-separated app client ids not counted: the portal's own
                               service clients (site sign-in), whose tokens only the portal holds
                               and which ask for every website visitor after the portal's count

The person is the subject of the token the Runtime received. The Runtime's JWT authorizer has
verified that token (signature, issuer, allowed client) before the request reaches this code, so
its claims are read here without verifying again; nothing in the request body names the caller.
"""

from __future__ import annotations

import base64
import datetime as dt
import json
import logging
import os
import time

from .. import claims as claimset

log = logging.getLogger("agent.quota")

QUOTA_TTL_S = 3 * 86400
PREFIX = "agent#"
LIMIT_REACHED = "You have reached today's question limit."


def token_claims(token: str | None) -> dict:
    """The payload of a JWT the Runtime has already verified; {} if it is not one."""
    try:
        payload = (token or "").split(".")[1]
        out = json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))
    except (IndexError, ValueError):
        return {}
    return out if isinstance(out, dict) else {}


def today() -> str:
    return dt.datetime.now(dt.timezone.utc).date().isoformat()


class AgentQuota:
    def __init__(self, table_name: str, limit: int, exempt_clients=(), table=None):
        if table is None:
            import boto3
            table = boto3.resource("dynamodb").Table(table_name)
        self.t = table
        self.limit = int(limit)
        self.exempt = {c for c in exempt_clients if c}

    @classmethod
    def from_env(cls) -> "AgentQuota | None":
        table = os.environ.get("AGENT_QUOTA_TABLE", "").strip()
        limit = int(os.environ.get("AGENT_DAILY_INVOCATIONS", "0") or 0)
        if not table or limit <= 0:
            return None
        exempt = [c.strip() for c in os.environ.get("AGENT_QUOTA_EXEMPT_CLIENTS", "").split(",")]
        return cls(table, limit, exempt)

    def check(self, token: str | None, day: str | None = None) -> str | None:
        """None if this invocation may go ahead (and is counted), else the reason it may not."""
        c = token_claims(token)
        client = str(c.get("client_id") or c.get("azp") or "")
        if client and client in self.exempt:
            return None
        sub = claimset.subject(c)
        if not c or sub == "anonymous":
            return "the caller's token names no subject"
        return None if self.take(sub, day or today()) else LIMIT_REACHED

    def take(self, sub: str, day: str) -> bool:
        from botocore.exceptions import ClientError
        try:
            self.t.update_item(
                Key={"pk": f"{PREFIX}{sub}#{day}"},
                UpdateExpression="ADD n :one SET expires_at = :exp",
                ConditionExpression="attribute_not_exists(n) OR n < :limit",
                ExpressionAttributeValues={":one": 1, ":limit": self.limit, ":exp": int(time.time()) + QUOTA_TTL_S})
            return True
        except ClientError as e:
            if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
                return False
            raise
