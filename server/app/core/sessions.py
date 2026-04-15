import hashlib
import json
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any

from redis import Redis
from redis.exceptions import RedisError

from app.core.settings import Settings, get_settings


class InMemorySessionStore:
    def __init__(self, settings: Settings):
        self._settings = settings
        self._sessions: dict[str, dict[str, Any]] = {}
        self._refresh_index: dict[str, str] = {}

    def create_session(self, *, user_id: str, role: str) -> tuple[str, str, datetime]:
        session_id = secrets.token_hex(16)
        refresh_token = secrets.token_urlsafe(32)
        expires_at = datetime.now(UTC) + timedelta(days=self._settings.refresh_token_ttl_days)
        self._sessions[session_id] = {
            "session_id": session_id,
            "user_id": user_id,
            "role": role,
            "refresh_hash": self._hash_token(refresh_token),
            "expires_at": expires_at.isoformat(),
        }
        self._refresh_index[self._hash_token(refresh_token)] = session_id
        return session_id, refresh_token, expires_at

    def get_session(self, session_id: str) -> dict[str, Any] | None:
        session = self._sessions.get(session_id)
        if session and datetime.fromisoformat(session["expires_at"]) > datetime.now(UTC):
            return session
        if session:
            self.revoke_session(session_id)
        return None

    def rotate_refresh_token(self, refresh_token: str) -> tuple[dict[str, Any] | None, str | None, datetime | None]:
        session = self.get_session_by_refresh_token(refresh_token)
        if session is None:
            return None, None, None
        old_hash = session["refresh_hash"]
        self._refresh_index.pop(old_hash, None)
        new_refresh_token = secrets.token_urlsafe(32)
        expires_at = datetime.now(UTC) + timedelta(days=self._settings.refresh_token_ttl_days)
        session["refresh_hash"] = self._hash_token(new_refresh_token)
        session["expires_at"] = expires_at.isoformat()
        self._refresh_index[session["refresh_hash"]] = session["session_id"]
        return session, new_refresh_token, expires_at

    def get_session_by_refresh_token(self, refresh_token: str) -> dict[str, Any] | None:
        refresh_hash = self._hash_token(refresh_token)
        session_id = self._refresh_index.get(refresh_hash)
        if not session_id:
            return None
        session = self.get_session(session_id)
        if session and session["refresh_hash"] == refresh_hash:
            return session
        return None

    def revoke_session(self, session_id: str) -> None:
        session = self._sessions.pop(session_id, None)
        if session is not None:
            self._refresh_index.pop(session["refresh_hash"], None)

    @staticmethod
    def _hash_token(token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()


class RedisSessionStore(InMemorySessionStore):
    def __init__(self, settings: Settings):
        super().__init__(settings)
        self._client = Redis.from_url(settings.redis_url, decode_responses=True)

    def create_session(self, *, user_id: str, role: str) -> tuple[str, str, datetime]:
        session_id, refresh_token, expires_at = super().create_session(user_id=user_id, role=role)
        self._persist(session_id, self._sessions[session_id], expires_at)
        return session_id, refresh_token, expires_at

    def get_session(self, session_id: str) -> dict[str, Any] | None:
        try:
            payload = self._client.get(self._session_key(session_id))
        except RedisError:
            return super().get_session(session_id)
        if not payload:
            return None
        session = json.loads(payload)
        if datetime.fromisoformat(session["expires_at"]) <= datetime.now(UTC):
            self.revoke_session(session_id)
            return None
        self._sessions[session_id] = session
        return session

    def rotate_refresh_token(self, refresh_token: str) -> tuple[dict[str, Any] | None, str | None, datetime | None]:
        session, new_refresh_token, expires_at = super().rotate_refresh_token(refresh_token)
        if session is None or new_refresh_token is None or expires_at is None:
            return None, None, None
        self._persist(session["session_id"], session, expires_at)
        return session, new_refresh_token, expires_at

    def get_session_by_refresh_token(self, refresh_token: str) -> dict[str, Any] | None:
        refresh_hash = self._hash_token(refresh_token)
        try:
            session_id = self._client.get(self._refresh_key(refresh_hash))
        except RedisError:
            return super().get_session_by_refresh_token(refresh_token)
        if not session_id:
            return None
        return self.get_session(session_id)

    def revoke_session(self, session_id: str) -> None:
        session = self.get_session(session_id) or self._sessions.get(session_id)
        super().revoke_session(session_id)
        try:
            self._client.delete(self._session_key(session_id))
            if session is not None:
                self._client.delete(self._refresh_key(session["refresh_hash"]))
        except RedisError:
            return

    def _persist(self, session_id: str, session: dict[str, Any], expires_at: datetime) -> None:
        ttl_seconds = max(int((expires_at - datetime.now(UTC)).total_seconds()), 1)
        refresh_hash = session["refresh_hash"]
        payload = json.dumps(session)
        self._client.setex(self._session_key(session_id), ttl_seconds, payload)
        self._client.setex(self._refresh_key(refresh_hash), ttl_seconds, session_id)

    @staticmethod
    def _session_key(session_id: str) -> str:
        return f"auth:session:{session_id}"

    @staticmethod
    def _refresh_key(refresh_hash: str) -> str:
        return f"auth:refresh:{refresh_hash}"


_session_store: InMemorySessionStore | None = None


def get_session_store() -> InMemorySessionStore:
    global _session_store
    if _session_store is not None:
        return _session_store

    settings = get_settings()
    try:
        _session_store = RedisSessionStore(settings)
    except RedisError:
        _session_store = InMemorySessionStore(settings)
    return _session_store
