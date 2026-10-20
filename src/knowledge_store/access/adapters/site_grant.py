"""Sign-in through a host website: a short grant the site signs for this lab alone.

A website that signs people in can frame the portal and hand each signed-in person's page a short
JWT for this lab (the embed protocol's pn:grant message). The page sends it as the header
X-Site-Grant, and the portal API verifies it here, in place of the identity provider's token:

1. ES256 only, against the site's public keys, given as configuration (SITE_GRANT_JWKS, a JWKS
   document), so a request never waits on the site. The portal can verify a grant, never mint one;
2. the issuer is the site (SITE_GRANT_ISSUER), the audience names this lab (`lab:<SITE_GRANT_LAB>`),
   and it is within its lifetime (a grant lasts minutes);
3. the person's roles decide what they may do here, and the portal, not the site, decides: a role in
   SITE_ROLES may read, one in SITE_PRIVATE_ROLES may also read private-scope content, and a person
   with neither is refused.

The portal Lambda ships with the standard library only, so the signature is checked with the
P-256 arithmetic below: verification only, with public parameters, every input range-checked.
tests/test_site_grant.py checks it against the cryptography package's signatures, good and bad.
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import time

LEEWAY_S = 30
MAX_GRANT_BYTES = 4096

# NIST P-256 (FIPS 186-4 D.1.2.3)
_P = 0xFFFFFFFF00000001000000000000000000000000FFFFFFFFFFFFFFFFFFFFFFFF
_A = _P - 3
_B = 0x5AC635D8AA3A93E7B3EBBD55769886BC651D06B0CC53B0F63BCE3C3E27D2604B
_N = 0xFFFFFFFF00000000FFFFFFFFFFFFFFFFBCE6FAADA7179E84F3B9CAC2FC632551
_G = (0x6B17D1F2E12C4247F8BCE6E563A440F277037D812DEB33A0F4A13945D898C296,
      0x4FE342E2FE1A7F9B8EE7EB4A7C0F9E162BCE33576B315ECECBB6406837BF51F5)


class Refused(Exception):
    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status


# ---- P-256 signature verification ------------------------------------------------------------
# Points in Jacobian coordinates (X, Y, Z), affine (X/Z^2, Y/Z^3); Z == 0 is the point at infinity.

_INF = (1, 1, 0)


def _on_curve(x: int, y: int) -> bool:
    return 0 <= x < _P and 0 <= y < _P and (y * y - (x * x * x + _A * x + _B)) % _P == 0


def _double(p1):
    x1, y1, z1 = p1
    if z1 == 0 or y1 == 0:
        return _INF
    delta = z1 * z1 % _P
    gamma = y1 * y1 % _P
    beta = x1 * gamma % _P
    alpha = 3 * (x1 - delta) * (x1 + delta) % _P
    x3 = (alpha * alpha - 8 * beta) % _P
    z3 = ((y1 + z1) ** 2 - gamma - delta) % _P
    y3 = (alpha * (4 * beta - x3) - 8 * gamma * gamma) % _P
    return x3, y3, z3


def _add(p1, p2):
    if p1[2] == 0:
        return p2
    if p2[2] == 0:
        return p1
    x1, y1, z1 = p1
    x2, y2, z2 = p2
    z1z1, z2z2 = z1 * z1 % _P, z2 * z2 % _P
    u1, u2 = x1 * z2z2 % _P, x2 * z1z1 % _P
    s1, s2 = y1 * z2 * z2z2 % _P, y2 * z1 * z1z1 % _P
    if u1 == u2:
        return _double(p1) if s1 == s2 else _INF
    hh = (u2 - u1) % _P
    r = (s2 - s1) % _P
    h2 = hh * hh % _P
    h3 = hh * h2 % _P
    x3 = (r * r - h3 - 2 * u1 * h2) % _P
    y3 = (r * (u1 * h2 - x3) - s1 * h3) % _P
    z3 = hh * z1 * z2 % _P
    return x3, y3, z3


def _mul2(k1: int, p1, k2: int, p2):
    """k1*p1 + k2*p2 (Shamir's trick: one pass over the bits of both scalars)."""
    both = _add(p1, p2)
    out = _INF
    for i in range(max(k1.bit_length(), k2.bit_length()) - 1, -1, -1):
        out = _double(out)
        b1, b2 = (k1 >> i) & 1, (k2 >> i) & 1
        if b1 and b2:
            out = _add(out, both)
        elif b1:
            out = _add(out, p1)
        elif b2:
            out = _add(out, p2)
    return out


def es256_verify(public: tuple[int, int], message: bytes, signature: bytes) -> bool:
    """Whether `signature` (JWS form: r and s, 32 bytes each) is P-256 ECDSA over SHA-256 of `message`
    by the key `public` (an affine point already checked to be on the curve)."""
    if len(signature) != 64:
        return False
    r, s = int.from_bytes(signature[:32], "big"), int.from_bytes(signature[32:], "big")
    if not (0 < r < _N and 0 < s < _N):
        return False
    e = int.from_bytes(hashlib.sha256(message).digest(), "big")
    w = pow(s, -1, _N)
    x, _, z = _mul2(e * w % _N, (*_G, 1), r * w % _N, (*public, 1))
    if z == 0:
        return False
    return (x * pow(z * z, -1, _P)) % _P % _N == r


# ---- the grant -----------------------------------------------------------------------------------

def _b64(part: str) -> bytes:
    return base64.urlsafe_b64decode(part + "=" * (-len(part) % 4))


_keys: dict = {"raw": None, "value": {}}


def keys() -> dict[str, tuple[int, int]]:
    """kid -> public key, from SITE_GRANT_JWKS. A key not on the curve is left out."""
    raw = os.environ.get("SITE_GRANT_JWKS") or ""
    if raw != _keys["raw"]:
        out = {}
        for k in (json.loads(raw).get("keys") if raw else None) or []:
            if k.get("kty") == "EC" and k.get("crv") == "P-256" and k.get("use", "sig") == "sig":
                x, y = int.from_bytes(_b64(k["x"]), "big"), int.from_bytes(_b64(k["y"]), "big")
                if _on_curve(x, y):
                    out[k.get("kid") or ""] = (x, y)
        _keys.update(raw=raw, value=out)
    return _keys["value"]


def enabled() -> bool:
    return bool(os.environ.get("SITE_GRANT_ISSUER") and os.environ.get("SITE_GRANT_JWKS"))


def audience() -> str:
    return f"lab:{os.environ.get('SITE_GRANT_LAB', 'knowledge')}"


def _roles(var: str, default: str) -> set[str]:
    return {r.strip() for r in os.environ.get(var, default).split(",") if r.strip()}


def verify(grant: str, now: float | None = None) -> dict:
    """The grant's claims, or Refused. The signature first, then issuer, audience and time."""
    if not enabled():
        raise Refused(401, "Signing in through the website is not set up here.")
    if not grant or len(grant) > MAX_GRANT_BYTES or grant.count(".") != 2:
        raise Refused(401, "Open this page from the website, signed in.")
    head_b64, body_b64, sig_b64 = grant.split(".")
    try:
        head, claims, sig = json.loads(_b64(head_b64)), json.loads(_b64(body_b64)), _b64(sig_b64)
    except ValueError:
        raise Refused(401, "That sign-in is not recognised.") from None
    if not isinstance(head, dict) or not isinstance(claims, dict) or head.get("alg") != "ES256":
        raise Refused(401, "That sign-in is not recognised.")
    key = keys().get(head.get("kid") or "")
    if key is None or not es256_verify(key, f"{head_b64}.{body_b64}".encode(), sig):
        raise Refused(401, "That sign-in is not recognised.")
    now = time.time() if now is None else now
    aud = claims.get("aud")
    if claims.get("iss") != os.environ["SITE_GRANT_ISSUER"] or audience() not in (aud if isinstance(aud, list) else [aud]):
        raise Refused(401, "That sign-in is for somewhere else.")
    if not isinstance(claims.get("exp"), (int, float)) or claims["exp"] + LEEWAY_S < now:
        raise Refused(401, "Your sign-in has expired. Reload the page.")
    if isinstance(claims.get("nbf"), (int, float)) and claims["nbf"] - LEEWAY_S > now:
        raise Refused(401, "That sign-in is not valid yet.")
    if not isinstance(claims.get("sub"), str) or not claims["sub"]:
        raise Refused(401, "That sign-in is not recognised.")
    return claims


_seen: dict[str, tuple[float, dict]] = {}   # grant hash -> (exp, caller): the page polls with one grant


def caller(grant: str, now: float | None = None) -> dict:
    """{sub, private, name} for a verified grant whose roles open this lab, or Refused."""
    now = time.time() if now is None else now
    key = hashlib.sha256(grant.encode()).hexdigest()
    hit = _seen.get(key)
    if hit and hit[0] + LEEWAY_S >= now:
        return hit[1]
    claims = verify(grant, now)
    roles = {r for r in claims.get("roles") or [] if isinstance(r, str)}
    private_roles = _roles("SITE_PRIVATE_ROLES", "owner")
    if not roles & (_roles("SITE_ROLES", "owner,team,preview") | private_roles):
        raise Refused(403, "Your sign-in does not include this lab.")
    out = {"sub": f"site-{claims['sub']}", "private": bool(roles & private_roles),
           "name": str(claims.get("name") or claims.get("email") or "")}
    if len(_seen) > 512:
        _seen.clear()
    _seen[key] = (float(claims["exp"]), out)
    return out
