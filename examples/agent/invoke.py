"""Call the example agent the way an application would: client credentials in, typed result out.

    python examples/agent/invoke.py --stack-dir infra/stack dossier holmes "Irene Adler"
    python examples/agent/invoke.py compare missions Cassini Juno --aspects "launch vehicle" target
    python examples/agent/invoke.py query holmes "Which clients came to Baker Street in disguise?"
    python examples/agent/invoke.py --as-service query holmes "..."        # the agent acts as itself
    python examples/agent/invoke.py --session my-research-1 ...            # reuse a session (memory)

It reads the stack's outputs (terraform output -json in --stack-dir), fetches the caller client's
secret from Cognito with your AWS credentials (it is never stored), gets an access token by client
credentials, and posts to the Runtime's HTTPS endpoint with that bearer token. boto3 cannot send a
bearer token to AgentCore Runtime, so this uses plain HTTPS.
"""

from __future__ import annotations

import argparse
import base64
import json
import subprocess
import urllib.parse
import urllib.request
import uuid


def outputs(stack_dir: str) -> dict:
    out = subprocess.run(["terraform", "output", "-json"], cwd=stack_dir, capture_output=True, text=True, check=True)
    return {k: v["value"] for k, v in json.loads(out.stdout).items()}


def client_secret(pool_id: str, client_id: str, region: str) -> str:
    import boto3
    c = boto3.client("cognito-idp", region_name=region)
    return c.describe_user_pool_client(UserPoolId=pool_id, ClientId=client_id)["UserPoolClient"]["ClientSecret"]


def access_token(endpoint: str, client_id: str, secret: str, scopes: list[str]) -> str:
    auth = base64.b64encode(f"{client_id}:{secret}".encode()).decode()
    body = urllib.parse.urlencode({"grant_type": "client_credentials", "scope": " ".join(scopes)}).encode()
    req = urllib.request.Request(endpoint, data=body, headers={
        "Authorization": f"Basic {auth}", "Content-Type": "application/x-www-form-urlencoded"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())["access_token"]


def invoke(runtime_arn: str, region: str, token: str, payload: dict, session: str, qualifier: str) -> dict:
    url = (f"https://bedrock-agentcore.{region}.amazonaws.com/runtimes/"
           f"{urllib.parse.quote(runtime_arn, safe='')}/invocations?qualifier={qualifier}")
    req = urllib.request.Request(url, data=json.dumps(payload).encode(), headers={
        "Authorization": f"Bearer {token}", "Content-Type": "application/json",
        "X-Amzn-Bedrock-AgentCore-Runtime-Session-Id": session})
    with urllib.request.urlopen(req, timeout=900) as r:
        return json.loads(r.read())


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--stack-dir", default="infra/stack")
    ap.add_argument("--region", default="us-east-1")
    ap.add_argument("--session", help="a session id to reuse (at least 33 characters is enforced by padding)")
    ap.add_argument("--qualifier", default="DEFAULT", help="DEFAULT, or prod for the pinned version")
    ap.add_argument("--as-service", action="store_true", help="ask the agent to act as itself (public scope)")
    ap.add_argument("--corroborate", action="store_true", help="let the agent use the browser, reported apart")
    ap.add_argument("task", choices=["dossier", "compare", "query"])
    ap.add_argument("collection")
    ap.add_argument("subject", nargs="+", help="an entity, several entities, or a question")
    ap.add_argument("--aspects", nargs="*", default=[])
    a = ap.parse_args()

    o = outputs(a.stack_dir)
    agent = o["agent"]
    if not agent or not agent.get("runtime_arn"):
        raise SystemExit("the agent Runtime is not deployed: set agent.enabled and agent.runtime in tfvars")
    secret = client_secret(o["cognito_user_pool"], agent["caller_client"], a.region)
    scopes = [f"{agent['scope_prefix']}/agent.invoke", f"{agent['scope_prefix']}/tools.public"]
    token = access_token(agent["token_endpoint"], agent["caller_client"], secret, scopes)
    payload: dict = {"task": a.task, "collection": a.collection}
    if a.task == "dossier":
        payload["entity"] = " ".join(a.subject)
    elif a.task == "compare":
        payload["entities"], payload["aspects"] = a.subject, a.aspects
    else:
        payload["question"] = " ".join(a.subject)
    if a.as_service:
        payload["as"] = "service"
    if a.corroborate:
        payload["corroborate"] = True
    session = (a.session or f"knowledge-store-{uuid.uuid4().hex}").ljust(33, "0")
    print(json.dumps(invoke(agent["runtime_arn"], a.region, token, payload, session, a.qualifier), indent=2))
    print(f"\nsession: {session}  (pass --session {session} to follow up with memory)")


if __name__ == "__main__":
    main()
