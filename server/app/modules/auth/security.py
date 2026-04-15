from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import time


class TokenError(ValueError):
    pass


def _urlsafe_b64encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _urlsafe_b64decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)


def hash_password(password: str, salt: bytes | None = None, iterations: int = 310_000) -> str:
    salt_bytes = salt or secrets.token_bytes(16)
    derived_key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt_bytes, iterations)
    return "pbkdf2_sha256${}${}${}".format(
        iterations,
        _urlsafe_b64encode(salt_bytes),
        _urlsafe_b64encode(derived_key),
    )


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        scheme, iteration_text, salt_text, hash_text = stored_hash.split("$", 3)
    except ValueError:
        return False

    if scheme != "pbkdf2_sha256":
        return False

    try:
        iterations = int(iteration_text)
    except ValueError:
        return False

    salt = _urlsafe_b64decode(salt_text)
    expected_hash = _urlsafe_b64decode(hash_text)
    candidate = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return hmac.compare_digest(candidate, expected_hash)


def hash_token(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _serialize_segment(payload: dict[str, object]) -> str:
    raw = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return _urlsafe_b64encode(raw)


def _deserialize_segment(segment: str) -> dict[str, object]:
    raw = _urlsafe_b64decode(segment)
    return json.loads(raw.decode("utf-8"))


def encode_jwt(claims: dict[str, object], secret: str) -> str:
    header = {"alg": "HS256", "typ": "JWT"}
    header_segment = _serialize_segment(header)
    payload_segment = _serialize_segment(claims)
    signing_input = f"{header_segment}.{payload_segment}".encode("ascii")
    signature = hmac.new(secret.encode("utf-8"), signing_input, hashlib.sha256).digest()
    signature_segment = _urlsafe_b64encode(signature)
    return f"{header_segment}.{payload_segment}.{signature_segment}"


def decode_jwt(token: str, secret: str, expected_token_type: str | None = None) -> dict[str, object]:
    try:
        header_segment, payload_segment, signature_segment = token.split(".")
    except ValueError as exc:
        raise TokenError("Malformed token.") from exc

    signing_input = f"{header_segment}.{payload_segment}".encode("ascii")
    expected_signature = hmac.new(secret.encode("utf-8"), signing_input, hashlib.sha256).digest()
    provided_signature = _urlsafe_b64decode(signature_segment)
    if not hmac.compare_digest(expected_signature, provided_signature):
        raise TokenError("Invalid token signature.")

    header = _deserialize_segment(header_segment)
    if header.get("alg") != "HS256":
        raise TokenError("Unsupported token algorithm.")

    payload = _deserialize_segment(payload_segment)
    if expected_token_type and payload.get("token_type") != expected_token_type:
        raise TokenError("Invalid token type.")

    expires_at = payload.get("exp")
    if not isinstance(expires_at, int):
        raise TokenError("Missing expiration.")
    if expires_at <= int(time.time()):
        raise TokenError("Token expired.")

    return payload


def issue_token_pair(
    *,
    user_id: str,
    email: str,
    full_name: str,
    role: str,
    session_id: str,
    secret: str,
    access_token_ttl_minutes: int,
    refresh_token_ttl_days: int,
) -> tuple[str, str, int]:
    now = int(time.time())
    access_token = encode_jwt(
        {
            "sub": user_id,
            "email": email,
            "full_name": full_name,
            "role": role,
            "session_id": session_id,
            "token_type": "access",
            "iat": now,
            "exp": now + access_token_ttl_minutes * 60,
            "jti": secrets.token_urlsafe(16),
        },
        secret,
    )
    refresh_exp = now + refresh_token_ttl_days * 24 * 60 * 60
    refresh_token = encode_jwt(
        {
            "sub": user_id,
            "email": email,
            "full_name": full_name,
            "role": role,
            "session_id": session_id,
            "token_type": "refresh",
            "iat": now,
            "exp": refresh_exp,
            "jti": secrets.token_urlsafe(16),
        },
        secret,
    )
    return access_token, refresh_token, refresh_exp

