"""Who a verified token names, and whether it may read private-scope content.

The claims differ by identity provider; the rule does not. A person is private if a group (or
role) claim holds PRIVATE_GROUP; an application is private if a scope (or role) claim holds
PRIVATE_SCOPE. The claim names are configuration:

                    Cognito (the default)
    SUBJECT_CLAIM   sub
    GROUPS_CLAIM    cognito:groups
    PRIVATE_GROUP   private-readers
    SCOPES_CLAIM    scope
    PRIVATE_SCOPE   <SCOPE_PREFIX>/tools.private

A claim setting may name several claims, comma-separated. Nothing here verifies a signature:
callers pass claims that a gateway or authorizer has already verified. Standard library only,
because the Lambda packages ship without dependencies.
"""

from __future__ import annotations

import os


def _names(var: str, default: str) -> list[str]:
    return [n.strip() for n in os.environ.get(var, default).split(",") if n.strip()]


def values(claims: dict, names: list[str]) -> set[str]:
    """Every value of the named claims. A claim may be a list, a space-separated string, or a
    string like "[a, b]" (how API Gateway passes a list claim)."""
    out: set[str] = set()
    for n in names:
        v = claims.get(n)
        if isinstance(v, (list, tuple)):
            out.update(str(x) for x in v)
        elif v:
            out.update(str(v).strip("[]").replace(",", " ").split())
    return out


def subject(claims: dict) -> str:
    for n in _names("SUBJECT_CLAIM", "sub"):
        if claims.get(n):
            return str(claims[n])
    return "anonymous"


def private_reader(claims: dict) -> bool:
    """A person in the private group (or holding the private role)."""
    return os.environ.get("PRIVATE_GROUP", "private-readers") in values(claims, _names("GROUPS_CLAIM", "cognito:groups"))


def private_scope() -> str:
    return os.environ.get("PRIVATE_SCOPE") or f"{os.environ.get('SCOPE_PREFIX', 'knowledge-store')}/tools.private"


def private_caller(claims: dict) -> bool:
    """A person in the private group, or an application granted the private scope."""
    return private_reader(claims) or private_scope() in values(claims, _names("SCOPES_CLAIM", "scope"))
