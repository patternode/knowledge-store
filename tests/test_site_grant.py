"""The website's grant (knowledge_store.site_grant): the P-256 verifier against the cryptography
package's signatures, and the claims checks."""

from __future__ import annotations

import base64
import json
import os
import time

import pytest
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.utils import decode_dss_signature

from knowledge_store import site_grant

ISSUER = "https://site.example"


def b64(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode()


def jws_sig(key, data: bytes) -> bytes:
    r, s = decode_dss_signature(key.sign(data, ec.ECDSA(hashes.SHA256())))
    return r.to_bytes(32, "big") + s.to_bytes(32, "big")


def public(key) -> tuple[int, int]:
    n = key.public_key().public_numbers()
    return n.x, n.y


def jwk(key, kid="k1") -> dict:
    x, y = public(key)
    return {"kty": "EC", "crv": "P-256", "kid": kid, "use": "sig", "alg": "ES256",
            "x": b64(x.to_bytes(32, "big")), "y": b64(y.to_bytes(32, "big"))}


def mint(key, claims: dict, kid="k1", alg="ES256") -> str:
    head = b64(json.dumps({"alg": alg, "kid": kid, "typ": "JWT"}).encode())
    body = b64(json.dumps(claims).encode())
    return f"{head}.{body}.{b64(jws_sig(key, f'{head}.{body}'.encode()))}"


@pytest.fixture
def site(monkeypatch):
    key = ec.generate_private_key(ec.SECP256R1())
    monkeypatch.setenv("SITE_GRANT_ISSUER", ISSUER)
    monkeypatch.setenv("SITE_GRANT_JWKS", json.dumps({"keys": [jwk(key)]}))
    monkeypatch.setenv("SITE_GRANT_LAB", "knowledge")
    monkeypatch.delenv("SITE_ROLES", raising=False)
    monkeypatch.delenv("SITE_PRIVATE_ROLES", raising=False)
    site_grant._seen.clear()
    return key


def claims(**kw) -> dict:
    now = int(time.time())
    return {"iss": ISSUER, "aud": "lab:knowledge", "sub": "u1", "exp": now + 900, "iat": now,
            "roles": ["team"], "name": "Ada", **kw}


def test_verifier_matches_cryptography():
    for i in range(40):
        key = ec.generate_private_key(ec.SECP256R1())
        msg = os.urandom(i * 7)
        sig = jws_sig(key, msg)
        assert site_grant.es256_verify(public(key), msg, sig)
        assert not site_grant.es256_verify(public(key), msg + b"x", sig)
        bad = bytearray(sig)
        bad[i % 64] ^= 1
        assert not site_grant.es256_verify(public(key), msg, bytes(bad))
        other = ec.generate_private_key(ec.SECP256R1())
        assert not site_grant.es256_verify(public(other), msg, sig)


def test_verifier_refuses_out_of_range_signatures():
    key = ec.generate_private_key(ec.SECP256R1())
    sig = jws_sig(key, b"m")
    r, s = sig[:32], sig[32:]
    n = site_grant._N.to_bytes(32, "big")
    zero = bytes(32)
    for bad in (zero + s, r + zero, n + s, r + n, sig[:63], sig + b"\0"):
        assert not site_grant.es256_verify(public(key), b"m", bad)


def test_a_key_off_the_curve_is_ignored(monkeypatch):
    k = {"kty": "EC", "crv": "P-256", "kid": "bad", "x": b64((1).to_bytes(32, "big")), "y": b64((2).to_bytes(32, "big"))}
    monkeypatch.setenv("SITE_GRANT_JWKS", json.dumps({"keys": [k]}))
    assert site_grant.keys() == {}


def test_a_good_grant_names_the_caller(site):
    who = site_grant.caller(mint(site, claims()))
    assert who == {"sub": "site-u1", "private": False, "name": "Ada"}
    assert site_grant.caller(mint(site, claims(roles=["owner"])))["private"] is True


def test_roles_are_the_labs_to_map(site, monkeypatch):
    with pytest.raises(site_grant.Refused) as e:
        site_grant.caller(mint(site, claims(roles=["visitor"])))
    assert e.value.status == 403
    monkeypatch.setenv("SITE_PRIVATE_ROLES", "team")
    assert site_grant.caller(mint(site, claims(sub="u2")))["private"] is True


@pytest.mark.parametrize("bad", [
    {"iss": "https://elsewhere.example"},
    {"aud": "lab:earnings"},
    {"exp": int(time.time()) - 120},
    {"nbf": int(time.time()) + 600},
    {"sub": ""},
])
def test_claims_are_checked(site, bad):
    with pytest.raises(site_grant.Refused) as e:
        site_grant.caller(mint(site, claims(**bad)))
    assert e.value.status == 401


def test_signature_key_and_algorithm_are_checked(site):
    other = ec.generate_private_key(ec.SECP256R1())
    head, body, sig = mint(site, claims()).split(".")
    forged_body = b64(json.dumps(claims(roles=["owner"])).encode())
    for grant in (mint(other, claims()), mint(site, claims(), kid="unknown"), mint(site, claims(), alg="HS256"),
                  f"{head}.{forged_body}.{sig}", "", "a.b", "x" * 5000):
        with pytest.raises(site_grant.Refused):
            site_grant.caller(grant)


def test_off_without_configuration(monkeypatch):
    monkeypatch.delenv("SITE_GRANT_ISSUER", raising=False)
    assert not site_grant.enabled()
    with pytest.raises(site_grant.Refused):
        site_grant.verify("a.b.c")
