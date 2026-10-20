"""Claims: who a verified token names, and whether it may read private-scope content."""

from __future__ import annotations

import pytest

from knowledge_store.access.domain import claims


@pytest.fixture(autouse=True)
def cognito_defaults(monkeypatch):
    for var in ("SUBJECT_CLAIM", "GROUPS_CLAIM", "PRIVATE_GROUP", "SCOPES_CLAIM", "PRIVATE_SCOPE", "SCOPE_PREFIX"):
        monkeypatch.delenv(var, raising=False)


@pytest.mark.parametrize("value, expected", [
    (["a", "b"], {"a", "b"}),
    (("a",), {"a"}),
    ("a b", {"a", "b"}),
    ("[a, b]", {"a", "b"}),          # how API Gateway passes a list claim
    ("", set()),
    (None, set()),
])
def test_claim_values_read_lists_and_strings(value, expected):
    assert claims.values({"g": value}, ["g"]) == expected


def test_values_of_several_claims_are_merged():
    assert claims.values({"a": "x", "b": ["y"]}, ["a", "b", "missing"]) == {"x", "y"}


def test_the_subject_is_the_sub_claim():
    assert claims.subject({"sub": "u-1"}) == "u-1"


def test_a_token_without_a_subject_is_anonymous():
    assert claims.subject({}) == "anonymous"


def test_the_subject_claim_is_configurable_and_the_first_present_wins(monkeypatch):
    monkeypatch.setenv("SUBJECT_CLAIM", "oid, sub")
    assert claims.subject({"sub": "s", "oid": "o"}) == "o"
    assert claims.subject({"sub": "s"}) == "s"


def test_a_person_in_the_private_group_is_a_private_reader():
    assert claims.private_reader({"cognito:groups": ["private-readers"]})
    assert claims.private_caller({"cognito:groups": "[private-readers]"})


def test_a_person_outside_the_group_is_not():
    assert not claims.private_caller({"cognito:groups": ["readers"]})


def test_the_group_and_its_claim_are_configurable(monkeypatch):
    monkeypatch.setenv("GROUPS_CLAIM", "roles")
    monkeypatch.setenv("PRIVATE_GROUP", "Insiders")
    assert claims.private_reader({"roles": ["Insiders"]})
    assert not claims.private_reader({"cognito:groups": ["private-readers"]})


def test_the_private_scope_defaults_from_the_prefix(monkeypatch):
    assert claims.private_scope() == "knowledge-store/tools.private"
    monkeypatch.setenv("SCOPE_PREFIX", "ks-prod")
    assert claims.private_scope() == "ks-prod/tools.private"
    monkeypatch.setenv("PRIVATE_SCOPE", "custom/private")
    assert claims.private_scope() == "custom/private"


def test_an_application_with_the_private_scope_is_a_private_caller():
    assert claims.private_caller({"scope": "knowledge-store/tools.public knowledge-store/tools.private"})


def test_an_application_with_only_the_public_scope_is_not():
    assert not claims.private_caller({"scope": "knowledge-store/tools.public"})
