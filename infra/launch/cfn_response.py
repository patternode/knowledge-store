"""Tell CloudFormation how the Terraform run went: the last step of the launch stack's build.

    python cfn_response.py [outputs.json]

The Lambda that started the build passed the custom resource's request through as environment
variables (CFN_RESPONSE_URL and the ids). SUCCESS when CodeBuild says the build has succeeded so
far (CODEBUILD_BUILD_SUCCEEDING=1), with the stack's outputs as the resource's attributes;
otherwise FAILED, pointing at the build log. A response is always sent, so the stack never waits
for its timeout.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.request

ATTRIBUTES = {"portal_url": "PortalUrl", "lake_bucket": "LakeBucket", "upload_to": "UploadTo",
              "pipeline_logs": "PipelineLogs", "cognito_user_pool": "UserPool"}


def attributes(outputs_path: str | None) -> dict:
    if not outputs_path or not os.path.exists(outputs_path):
        return {}
    with open(outputs_path, encoding="utf-8") as f:
        raw = json.load(f)
    out = {}
    for key, attr in ATTRIBUTES.items():
        if key in raw:
            v = raw[key]["value"]
            out[attr] = v if isinstance(v, str) else json.dumps(v)
    return out


def body(env: dict, data: dict) -> dict:
    ok = env.get("CODEBUILD_BUILD_SUCCEEDING") == "1"
    log = env.get("CODEBUILD_BUILD_URL") or env.get("CODEBUILD_LOG_PATH") or "the CodeBuild log"
    return {
        "Status": "SUCCESS" if ok else "FAILED",
        "Reason": f"Terraform {env.get('ACTION', 'apply')} {'succeeded' if ok else 'failed'}; see {log}"[:1000],
        "PhysicalResourceId": env.get("CFN_PHYSICAL_ID") or "knowledge-store-deployment",
        "StackId": env["CFN_STACK_ID"],
        "RequestId": env["CFN_REQUEST_ID"],
        "LogicalResourceId": env["CFN_LOGICAL_ID"],
        "Data": data if ok else {},
    }


def main() -> int:
    env = dict(os.environ)
    if not env.get("CFN_RESPONSE_URL"):
        print("no CFN_RESPONSE_URL: not started by the launch stack, nothing to report")
        return 0
    payload = json.dumps(body(env, attributes(sys.argv[1] if len(sys.argv) > 1 else None))).encode()
    req = urllib.request.Request(env["CFN_RESPONSE_URL"], data=payload, method="PUT",
                                 headers={"Content-Type": "", "Content-Length": str(len(payload))})
    with urllib.request.urlopen(req, timeout=30) as r:
        print(f"reported to CloudFormation: HTTP {r.status}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
