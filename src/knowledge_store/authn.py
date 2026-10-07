"""Verify a bearer token where no gateway has verified it first (Azure Functions, Cloud Run).

On AWS, API Gateway and AgentCore Gateway verify tokens before the code runs. Elsewhere the code
verifies them itself, against the identity provider's published keys:

    AUTH_ISSUERS    accepted issuers, comma-separated (Entra: https://login.microsoftonline.com/<tenant>/v2.0)
    AUTH_AUDIENCES  accepted audiences, comma-separated (Entra: the API's client id and api://... URI)
    AUTH_JWKS_URL   the signing keys (Entra: https://login.microsoftonline.com/<tenant>/discovery/v2.0/keys)

Signature (RS256), issuer, audience, expiry and not-before are all checked; a token failing any of
them is refused. What the claims then allow is knowledge_store.claims' business.
"""

from __future__ import annotations

import os
from functools import lru_cache


class Unauthorized(Exception):
    pass


def _list(var: str) -> list[str]:
    return [v.strip() for v in os.environ.get(var, "").split(",") if v.strip()]


@lru_cache(maxsize=4)
def _keys(url: str):
    import jwt
    return jwt.PyJWKClient(url, cache_keys=True, lifespan=3600)


def bearer(authorization: str | None) -> str:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise Unauthorized("a bearer token is required")
    return authorization.split(" ", 1)[1].strip()


def verify(token: str, *, jwks=None) -> dict:
    """The token's claims, if it is valid for this deployment."""
    import jwt
    issuers, audiences = _list("AUTH_ISSUERS"), _list("AUTH_AUDIENCES")
    if not issuers or not audiences:
        raise RuntimeError("AUTH_ISSUERS and AUTH_AUDIENCES must be set")
    try:
        key = (jwks or _keys(os.environ["AUTH_JWKS_URL"])).get_signing_key_from_jwt(token).key
        claims = jwt.decode(token, key, algorithms=["RS256"], audience=audiences, leeway=60,
                            options={"require": ["exp", "iss", "aud"]})
    except jwt.PyJWTError as e:
        raise Unauthorized(str(e)) from e
    if claims.get("iss") not in issuers:
        raise Unauthorized("the token's issuer is not accepted")
    return claims
