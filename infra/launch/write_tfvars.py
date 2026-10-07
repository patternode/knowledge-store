"""Write terraform.tfvars.json for infra/stack from the launch stack's parameters (environment).

Run by the launch stack's CodeBuild project, in infra/stack. Every value comes from a
CloudFormation parameter the Lambda passed through as an environment variable; nothing else is
read. Kept here, not inline in the template, so it is tested with the rest of the code.

    ADMIN_EMAIL            required
    DEPLOYMENT_NAME        resource prefix
    AWS_REGION             set by CodeBuild
    COLLECTIONS_JSON       {"<id>": {"profile": {...}, "sources": [...], "ontology_mode": "..."}}
    ONTOLOGY_MODE          applied to collections that do not set their own
    MODEL_ID               extraction and chat model
    KNOWLEDGE_GRAPH, KNOWLEDGE_BASE, AGENT_RUNTIME    "true" or "false"
    DELETE_DATA            "true" lets destroy delete the lake
"""

from __future__ import annotations

import json
import os
import re
import sys

ID = re.compile(r"^[a-z0-9][a-z0-9-]{0,39}$")


def build(env: dict | None = None) -> dict:
    env = os.environ if env is None else env
    email = (env.get("ADMIN_EMAIL") or "").strip()
    if "@" not in email:
        raise ValueError("ADMIN_EMAIL must be an email address")
    raw = (env.get("COLLECTIONS_JSON") or "").strip() or '{"default": {}}'
    try:
        collections = json.loads(raw)
    except json.JSONDecodeError as e:
        raise ValueError(f"CollectionsJson is not valid JSON: {e}") from None
    if not isinstance(collections, dict) or not collections:
        raise ValueError('CollectionsJson must be an object with at least one collection, e.g. {"default": {}}')
    mode = env.get("ONTOLOGY_MODE") or "curated"
    for cid, c in collections.items():
        if not ID.match(cid):
            raise ValueError(f"collection id {cid!r}: 1-40 lower-case letters, digits or hyphens")
        if not isinstance(c, dict):
            raise ValueError(f"collection {cid!r} must be an object")
        c.setdefault("ontology_mode", mode)
    model = env.get("MODEL_ID") or "us.anthropic.claude-sonnet-5"
    return {
        "admin_email": email,
        "name": env.get("DEPLOYMENT_NAME") or "knowledge-store",
        "region": env.get("AWS_REGION") or env.get("AWS_DEFAULT_REGION") or "us-east-1",
        "collections": collections,
        "extraction_model_id": model,
        "chat_model_id": model,
        "force_destroy_lake": flag_of(env, "DELETE_DATA"),
        "knowledge_graph": {"enabled": flag_of(env, "KNOWLEDGE_GRAPH", True)},
        "knowledge_base": {"enabled": flag_of(env, "KNOWLEDGE_BASE", True)},
        "agent": {"runtime": flag_of(env, "AGENT_RUNTIME"), "model_id": model},
    }


def flag_of(env, name: str, default: bool = False) -> bool:
    return str(env.get(name, str(default))).strip().lower() == "true"


def main() -> int:
    try:
        tfvars = build()
    except ValueError as e:
        print(f"invalid parameters: {e}", file=sys.stderr)
        return 2
    with open("terraform.tfvars.json", "w", encoding="utf-8") as f:
        json.dump(tfvars, f, indent=2)
    print(json.dumps({k: v for k, v in tfvars.items() if k != "admin_email"}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
