from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time
from typing import Any

# Password hashing and token signing use only the Python standard library, so the
# project stays dependency-free (no passlib / bcrypt / python-jose). PBKDF2-SHA256
# is a standard, deliberately-slow password KDF; the token is a compact HS256-style
# JWT (base64url header.payload.signature, HMAC-SHA256 over the app secret).

_PBKDF2_ALGO = "sha256"
_PBKDF2_ITERATIONS = 240_000
_SALT_BYTES = 16


def hash_password(password: str) -> str:
    """Return ``pbkdf2_sha256$iterations$salt_hex$hash_hex`` for storage."""
    salt = os.urandom(_SALT_BYTES)
    digest = hashlib.pbkdf2_hmac(
        _PBKDF2_ALGO, password.encode("utf-8"), salt, _PBKDF2_ITERATIONS
    )
    return f"pbkdf2_{_PBKDF2_ALGO}${_PBKDF2_ITERATIONS}${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    """Constant-time check of ``password`` against a stored hash."""
    try:
        algo_label, iterations_raw, salt_hex, digest_hex = stored.split("$")
        iterations = int(iterations_raw)
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(digest_hex)
    except (ValueError, AttributeError):
        return False
    algo = algo_label.split("_", 1)[-1] or _PBKDF2_ALGO
    candidate = hashlib.pbkdf2_hmac(algo, password.encode("utf-8"), salt, iterations)
    return hmac.compare_digest(candidate, expected)


def create_token(subject: str, secret: str, ttl_hours: float) -> str:
    """Issue a signed token that proves ``subject`` for ``ttl_hours``."""
    header = {"alg": "HS256", "typ": "JWT"}
    now = int(time.time())
    payload = {"sub": subject, "iat": now, "exp": now + int(ttl_hours * 3600)}
    header_b64 = _b64url_encode(_compact_json(header))
    payload_b64 = _b64url_encode(_compact_json(payload))
    signing_input = f"{header_b64}.{payload_b64}"
    signature = _sign(signing_input, secret)
    return f"{signing_input}.{signature}"


def decode_token(token: str, secret: str) -> dict[str, Any] | None:
    """Return the payload if the signature is valid and unexpired, else ``None``."""
    try:
        header_b64, payload_b64, signature = token.split(".")
    except (ValueError, AttributeError):
        return None

    if not hmac.compare_digest(signature, _sign(f"{header_b64}.{payload_b64}", secret)):
        return None

    try:
        payload = json.loads(_b64url_decode(payload_b64))
    except (ValueError, json.JSONDecodeError):
        return None

    exp = payload.get("exp")
    if not isinstance(exp, (int, float)) or time.time() >= exp:
        return None
    return payload


def _compact_json(data: dict[str, Any]) -> bytes:
    return json.dumps(data, separators=(",", ":")).encode("utf-8")


def _sign(signing_input: str, secret: str) -> str:
    signature = hmac.new(
        secret.encode("utf-8"), signing_input.encode("ascii"), hashlib.sha256
    ).digest()
    return _b64url_encode(signature)


def _b64url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _b64url_decode(text: str) -> bytes:
    padding = "=" * (-len(text) % 4)
    return base64.urlsafe_b64decode(text + padding)
