from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from typing import Protocol

from redis import Redis


SESSION_KEY_PREFIX = "qf:auth:session:"


def _utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()


@dataclass(slots=True)
class AuthSession:
    session_id: str
    user_id: str
    email: str
    full_name: str
    role: str
    refresh_token_hash: str
    status: str
    created_at: str
    updated_at: str
    expires_at: int


class SessionStore(Protocol):
    def create_session(self, session: AuthSession) -> None: ...

    def get_session(self, session_id: str) -> AuthSession | None: ...

    def rotate_refresh_token(self, session_id: str, refresh_token_hash: str, expires_at: int) -> None: ...

    def delete_session(self, session_id: str) -> None: ...


class RedisSessionStore:
    def __init__(self, redis_url: str) -> None:
        self._client = Redis.from_url(redis_url)

    def create_session(self, session: AuthSession) -> None:
        ttl_seconds = max(session.expires_at - int(datetime.now(UTC).timestamp()), 1)
        self._client.setex(self._key(session.session_id), ttl_seconds, json.dumps(asdict(session)))

    def get_session(self, session_id: str) -> AuthSession | None:
        raw_value = self._client.get(self._key(session_id))
        if raw_value is None:
            return None

        payload = json.loads(raw_value)
        return AuthSession(**payload)

    def rotate_refresh_token(self, session_id: str, refresh_token_hash: str, expires_at: int) -> None:
        session = self.get_session(session_id)
        if session is None:
            return

        session.refresh_token_hash = refresh_token_hash
        session.updated_at = _utc_now_iso()
        session.expires_at = expires_at
        ttl_seconds = max(expires_at - int(datetime.now(UTC).timestamp()), 1)
        self._client.setex(self._key(session_id), ttl_seconds, json.dumps(asdict(session)))

    def delete_session(self, session_id: str) -> None:
        self._client.delete(self._key(session_id))

    @staticmethod
    def _key(session_id: str) -> str:
        return f"{SESSION_KEY_PREFIX}{session_id}"


class InMemorySessionStore:
    def __init__(self) -> None:
        self._sessions: dict[str, AuthSession] = {}

    def create_session(self, session: AuthSession) -> None:
        self._sessions[session.session_id] = session

    def get_session(self, session_id: str) -> AuthSession | None:
        return self._sessions.get(session_id)

    def rotate_refresh_token(self, session_id: str, refresh_token_hash: str, expires_at: int) -> None:
        session = self._sessions.get(session_id)
        if session is None:
            return

        session.refresh_token_hash = refresh_token_hash
        session.updated_at = _utc_now_iso()
        session.expires_at = expires_at

    def delete_session(self, session_id: str) -> None:
        self._sessions.pop(session_id, None)

