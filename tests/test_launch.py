"""The CloudFormation launch stack: parameters reach the build, tfvars match the Terraform, and the
build's report to CloudFormation is right on success and on failure."""

from __future__ import annotations

import importlib.util
import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
LAUNCH = ROOT / "infra" / "launch"


def load(name: str):
    spec = importlib.util.spec_from_file_location(name, LAUNCH / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


tfvars = load("write_tfvars")
cfn = load("cfn_response")


def stack_variables() -> set[str]:
    text = (ROOT / "infra/stack/variables.tf").read_text()
    return set(re.findall(r'^variable "([a-z_]+)"', text, re.M))


def test_tfvars_only_uses_declared_variables():
    out = tfvars.build({"ADMIN_EMAIL": "a@example.org"})
    assert set(out) <= stack_variables()
    agent_fields = set(re.findall(r"^\s+(\w+)\s+= optional", (ROOT / "infra/stack/variables.tf").read_text().split('variable "agent"')[1], re.M))
    assert set(out["agent"]) <= agent_fields


def test_tfvars_defaults_and_flags():
    out = tfvars.build({"ADMIN_EMAIL": "a@example.org", "ONTOLOGY_MODE": "auto",
                        "COLLECTIONS_JSON": '{"holmes": {"profile": {"name": "Holmes"}}, "m": {"ontology_mode": "curated"}}',
                        "ENABLE_AGENT": "true", "AGENT_RUNTIME": "true", "TRANSACTION_SEARCH": "true"})
    assert out["collections"]["holmes"]["ontology_mode"] == "auto"
    assert out["collections"]["m"]["ontology_mode"] == "curated"
    assert out["agent"] == {"enabled": True, "runtime": True, "model_id": out["extraction_model_id"],
                            "transaction_search": True, "evaluations": True}
    off = tfvars.build({"ADMIN_EMAIL": "a@example.org", "AGENT_RUNTIME": "true", "TRANSACTION_SEARCH": "true"})
    assert off["agent"]["enabled"] is False and off["agent"]["runtime"] is False and off["agent"]["transaction_search"] is False
    assert off["collections"] == {"default": {"ontology_mode": "curated"}}
    assert off["force_destroy_lake"] is False


@pytest.mark.parametrize("env, message", [
    ({"ADMIN_EMAIL": "nobody"}, "email"),
    ({"ADMIN_EMAIL": "a@example.org", "COLLECTIONS_JSON": "{not json"}, "valid JSON"),
    ({"ADMIN_EMAIL": "a@example.org", "COLLECTIONS_JSON": "{}"}, "at least one"),
    ({"ADMIN_EMAIL": "a@example.org", "COLLECTIONS_JSON": '{"Bad Id": {}}'}, "collection id"),
])
def test_tfvars_rejects_bad_parameters(env, message):
    with pytest.raises(ValueError, match=message):
        tfvars.build(env)


def test_every_template_parameter_reaches_the_build():
    template = (LAUNCH / "knowledge-store.yaml").read_text()
    params = set(re.findall(r"^  ([A-Z][A-Za-z0-9]+):\n    Type:", template.split("\nResources:")[0], re.M))
    passed = set(re.search(r"PASS = \[(.*?)\]", template, re.S).group(1).replace('"', "").replace("\n", "").replace(" ", "").split(","))
    props = set(re.findall(r"^      ([A-Z][A-Za-z0-9]+): !Ref", template.split("Type: Custom::KnowledgeStoreTerraform")[1], re.M))
    assert params == passed == props


ENV = {"CFN_STACK_ID": "arn:stack", "CFN_REQUEST_ID": "r1", "CFN_LOGICAL_ID": "Deployment", "ACTION": "apply"}


def test_response_on_success_carries_outputs(tmp_path):
    outputs = tmp_path / "o.json"
    outputs.write_text(json.dumps({"portal_url": {"value": "https://x/"}, "upload_to": {"value": {"default": "s3://b/landing/default/"}},
                                   "run_now": {"value": "aws ecs run-task"}}))
    body = cfn.body({**ENV, "CODEBUILD_BUILD_SUCCEEDING": "1"}, cfn.attributes(str(outputs)))
    assert body["Status"] == "SUCCESS"
    assert body["Data"] == {"PortalUrl": "https://x/", "UploadTo": json.dumps({"default": "s3://b/landing/default/"})}
    assert body["PhysicalResourceId"] == "knowledge-store-deployment"


def test_response_on_failure_has_no_outputs(tmp_path):
    body = cfn.body({**ENV, "CODEBUILD_BUILD_SUCCEEDING": "0", "CODEBUILD_BUILD_URL": "https://logs"}, {"PortalUrl": "x"})
    assert body["Status"] == "FAILED" and body["Data"] == {} and "https://logs" in body["Reason"]
    assert cfn.attributes(str(tmp_path / "missing.json")) == {}


def test_stack_root_passes_every_module_input():
    module_vars = set(re.findall(r'^variable "([a-z_]+)"', (ROOT / "infra/modules/knowledge-store/variables.tf").read_text(), re.M))
    root = (ROOT / "infra/stack/main.tf").read_text()
    call = root[root.index('module "knowledge_store"'):root.index("\n}\n", root.index('module "knowledge_store"'))]
    wired = set(re.findall(r"^\s+([a-z_]+)\s+= var\.\1$", call, re.M))
    assert wired == module_vars
    assert module_vars <= stack_variables()
    module_outputs = set(re.findall(r'^output "([a-z_]+)"', (ROOT / "infra/modules/knowledge-store/outputs.tf").read_text(), re.M))
    for root_dir in ("infra/stack", "examples/deployment"):
        outputs = set(re.findall(r'^output "([a-z_]+)"', (ROOT / root_dir / "outputs.tf").read_text(), re.M))
        assert outputs == module_outputs, root_dir
