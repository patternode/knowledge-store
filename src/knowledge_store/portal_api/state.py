"""The portal's own state: chat answers (kept a day) and each caller's daily question count.

Three adapters behind one port, chosen by CHAT_STATE:

    dynamodb  (the default)  DynamoDB table CHAT_TABLE, as on AWS
    mongodb                  database MONGODB_DB (default knowledge_store) at MONGODB_URI: MongoDB,
                             or a service that speaks its protocol
    memory                   a dict, for local runs and tests

The quota must hold across concurrent requests, so each adapter takes it with one atomic
conditional write. The MongoDB adapter keeps to what every MongoDB target supports: no
transactions, no $text, no TTL dependence. Expiry is checked on read, so a target without a
TTL index is correct and only keeps old rows longer; each deployment adds the TTL its target
supports (an index on expires_at, for example) to clear them.
"""

from __future__ import annotations

import datetime as dt
import json
import os
import threading
import time
from typing import Protocol

CHAT_TTL_S = 86400
QUOTA_TTL_S = 3 * 86400


class ChatState(Protocol):
    def put_chat(self, chat_id: str, sub: str, body: dict) -> None: ...
    def get_chat(self, chat_id: str) -> dict | None: ...
    def take_quota(self, sub: str, day: str, limit: int) -> bool: ...


def from_env() -> ChatState:
    kind = os.environ.get("CHAT_STATE", "dynamodb")
    if kind == "dynamodb":
        return DynamoState(os.environ["CHAT_TABLE"])
    if kind == "mongodb":
        return MongoState.connect(os.environ["MONGODB_URI"], os.environ.get("MONGODB_DB", "knowledge_store"))
    if kind == "memory":
        return MemoryState()
    raise ValueError(f"CHAT_STATE must be dynamodb, mongodb or memory, not {kind!r}")


class DynamoState:
    def __init__(self, table_name: str, table=None):
        if table is None:
            import boto3
            table = boto3.resource("dynamodb").Table(table_name)
        self.t = table

    def put_chat(self, chat_id, sub, body):
        self.t.put_item(Item={"pk": f"chat#{chat_id}", "sub": sub, "body": json.dumps(body, default=str),
                              "expires_at": int(time.time()) + CHAT_TTL_S})

    def get_chat(self, chat_id):
        item = self.t.get_item(Key={"pk": f"chat#{chat_id}"}).get("Item")
        return {"sub": item.get("sub"), "body": json.loads(item["body"])} if item else None

    def take_quota(self, sub, day, limit):
        from botocore.exceptions import ClientError
        try:
            self.t.update_item(
                Key={"pk": f"quota#{sub}#{day}"},
                UpdateExpression="ADD n :one SET expires_at = :exp",
                ConditionExpression="attribute_not_exists(n) OR n < :limit",
                ExpressionAttributeValues={":one": 1, ":limit": limit, ":exp": int(time.time()) + QUOTA_TTL_S})
            return True
        except ClientError as e:
            if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
                return False
            raise


class MongoState:
    def __init__(self, db):
        self.chat = db["chat"]
        self.quota = db["quota"]

    @classmethod
    def connect(cls, uri: str, db: str) -> "MongoState":
        from pymongo import MongoClient
        # retryWrites is off because some MongoDB-compatible services reject it; the writes here are
        # idempotent or conditional, so a caller's retry is safe.
        return cls(MongoClient(uri, retryWrites=False, serverSelectionTimeoutMS=10000)[db])

    @staticmethod
    def _expires(seconds: int) -> dt.datetime:
        return dt.datetime.now(dt.timezone.utc) + dt.timedelta(seconds=seconds)

    def put_chat(self, chat_id, sub, body):
        self.chat.replace_one({"_id": chat_id}, {"_id": chat_id, "sub": sub, "body": json.dumps(body, default=str),
                                                 "expires_at": self._expires(CHAT_TTL_S)}, upsert=True)

    def get_chat(self, chat_id):
        doc = self.chat.find_one({"_id": chat_id})
        if not doc:
            return None
        exp = doc["expires_at"]
        if exp.tzinfo is None:  # pymongo returns naive UTC unless the client is tz_aware
            exp = exp.replace(tzinfo=dt.timezone.utc)
        if exp < dt.datetime.now(dt.timezone.utc):
            return None
        return {"sub": doc.get("sub"), "body": json.loads(doc["body"])}

    def take_quota(self, sub, day, limit):
        """Increment the count only while it is under the limit. At the limit the filter misses,
        the upsert collides with the existing row, and the retry without upsert misses again. If
        two first questions of the day race, the loser's upsert collides and its retry counts."""
        from pymongo import ReturnDocument
        from pymongo.errors import DuplicateKeyError
        key = {"_id": f"{sub}#{day}", "n": {"$lt": limit}}
        update = {"$inc": {"n": 1}, "$set": {"expires_at": self._expires(QUOTA_TTL_S)}}
        try:
            self.quota.find_one_and_update(key, update, upsert=True, return_document=ReturnDocument.AFTER)
            return True
        except DuplicateKeyError:
            return self.quota.find_one_and_update(key, update, return_document=ReturnDocument.AFTER) is not None


class MemoryState:
    def __init__(self):
        self.lock = threading.Lock()
        self.chats: dict[str, dict] = {}
        self.counts: dict[str, int] = {}

    def put_chat(self, chat_id, sub, body):
        self.chats[chat_id] = {"sub": sub, "body": json.loads(json.dumps(body, default=str))}

    def get_chat(self, chat_id):
        return self.chats.get(chat_id)

    def take_quota(self, sub, day, limit):
        with self.lock:
            key = f"{sub}#{day}"
            if self.counts.get(key, 0) >= limit:
                return False
            self.counts[key] = self.counts.get(key, 0) + 1
            return True
