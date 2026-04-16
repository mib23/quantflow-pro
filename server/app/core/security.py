import base64
import hashlib
import hmac
import json
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from app.core.exceptions import ApiException
from app.core.settings import Settings


def _b64url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _b64url_decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(f"{value}{padding}".encode("ascii"))


def hash_password(password: str, iterations: int = 600_000) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), iterations)
    return f"pbkdf2_sha256${iterations}${salt}${digest.hex()}"


def verify_password(password: str, password_hash: str) -> bool:
    try:
        algorithm, iteration_value, salt, stored_hash = password_hash.split("$", 3)
    except ValueError:
        return False
    if algorithm != "pbkdf2_sha256":
        return False
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), int(iteration_value))
    return hmac.compare_digest(digest.hex(), stored_hash)


@dataclass(slots=True)
class TokenPayload:
    subject: str
    role: str
    session_id: str
    token_type: str
    expires_at: datetime


class TokenService:
    def __init__(self, settings: Settings):
        self._secret = settings.jwt_secret.encode("utf-8")
        self._access_ttl = timedelta(minutes=settings.access_token_ttl_minutes)

    def create_access_token(self, *, user_id: str, role: str, session_id: str) -> tuple[str, datetime]:
        expires_at = datetime.now(UTC) + self._access_ttl
        payload = {
            "sub": user_id,
            "role": role,
            "session_id": session_id,
            "typ": "access",
            "iat": int(datetime.now(UTC).timestamp()),
            "exp": int(expires_at.timestamp()),
        }
        return self._encode(payload), expires_at

    def decode_token(self, token: str, *, token_type: str = "access") -> TokenPayload:
        try:
            header_segment, payload_segment, signature_segment = token.split(".")
        except ValueError as exc:
            raise ApiException("AUTH_INVALID_TOKEN", "Invalid token format.", 401) from exc

        signing_input = f"{header_segment}.{payload_segment}".encode("ascii")
        expected_signature = _b64url_encode(hmac.new(self._secret, signing_input, hashlib.sha256).digest())
        if not hmac.compare_digest(signature_segment, expected_signature):
            raise ApiException("AUTH_INVALID_TOKEN", "Invalid token signature.", 401)

        payload = json.loads(_b64url_decode(payload_segment))
        if payload.get("typ") != token_type:
            raise ApiException("AUTH_INVALID_TOKEN", "Unexpected token type.", 401)

        expires_at = datetime.fromtimestamp(payload["exp"], tz=UTC)
        if expires_at <= datetime.now(UTC):
            raise ApiException("AUTH_TOKEN_EXPIRED", "Token has expired.", 401)

        return TokenPayload(
            subject=payload["sub"],
            role=payload["role"],
            session_id=payload["session_id"],
            token_type=payload["typ"],
            expires_at=expires_at,
        )

    def _encode(self, payload: dict[str, Any]) -> str:
        header = {"alg": "HS256", "typ": "JWT"}
        header_segment = _b64url_encode(json.dumps(header, separators=(",", ":"), sort_keys=True).encode("utf-8"))
        payload_segment = _b64url_encode(json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8"))
        signing_input = f"{header_segment}.{payload_segment}".encode("ascii")
        signature = _b64url_encode(hmac.new(self._secret, signing_input, hashlib.sha256).digest())
        return f"{header_segment}.{payload_segment}.{signature}"
