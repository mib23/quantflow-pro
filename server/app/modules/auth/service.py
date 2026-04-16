from __future__ import annotations
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import uuid4

from app.core.exceptions import ApiException

from .repository import StoredUser, UserRepository
from .session_store import AuthSession, SessionStore
from .security import TokenError, decode_jwt, hash_token, issue_token_pair, verify_password


def _utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()


@dataclass(slots=True)
class AuthConfig:
    jwt_secret: str
    access_token_ttl_minutes: int = 15
    refresh_token_ttl_days: int = 30


@dataclass(slots=True)
class AuthenticatedUser:
    id: str
    email: str
    full_name: str
    role: str

    def to_public_dict(self) -> dict[str, str]:
        return {
            "id": self.id,
            "email": self.email,
            "full_name": self.full_name,
            "role": self.role,
        }


@dataclass(slots=True)
class TokenPair:
    access_token: str
    refresh_token: str
    token_type: str
    user: AuthenticatedUser


@dataclass(slots=True)
class LogoutResult:
    revoked: bool
    session_id: str | None


class AuthService:
    def __init__(self, repository: UserRepository, session_store: SessionStore, config: AuthConfig) -> None:
        self._repository = repository
        self._session_store = session_store
        self._config = config

    @classmethod
    def from_settings(cls) -> "AuthService":
        from .dependencies import get_auth_repository, get_auth_session_store, get_auth_config

        return cls(get_auth_repository(), get_auth_session_store(), get_auth_config())

    def login(self, email: str, password: str) -> TokenPair:
        user = self._repository.get_by_email(email)
        if user is None or user.status.upper() != "ACTIVE" or not verify_password(password, user.password_hash):
            raise ApiException("AUTH_INVALID_CREDENTIALS", "Invalid email or password.", status_code=401)

        return self._issue_session(user)

    def refresh(self, refresh_token: str) -> TokenPair:
        claims = self._decode_refresh_token(refresh_token)
        session = self._load_session(claims["session_id"])
        if session is None:
            raise ApiException("AUTH_UNAUTHORIZED", "Session is not active.", status_code=401)

        if session.user_id != str(claims["sub"]):
            raise ApiException("AUTH_UNAUTHORIZED", "Session does not match token.", status_code=401)

        if session.refresh_token_hash != hash_token(refresh_token):
            raise ApiException("AUTH_UNAUTHORIZED", "Refresh token has been rotated.", status_code=401)

        user = self._repository.get_by_id(session.user_id)
        if user is None or user.status.upper() != "ACTIVE":
            raise ApiException("AUTH_USER_INACTIVE", "User is not active.", status_code=401)

        return self._rotate_session(user, session.session_id)

    def logout(self, refresh_token: str | None = None, access_token: str | None = None) -> LogoutResult:
        session_id = self._resolve_session_id(refresh_token=refresh_token, access_token=access_token)
        self._session_store.delete_session(session_id)
        return LogoutResult(revoked=True, session_id=session_id)

    def get_current_user(self, access_token: str) -> AuthenticatedUser:
        claims = self._decode_access_token(access_token)
        session = self._load_session(claims["session_id"])
        if session is None:
            raise ApiException("AUTH_UNAUTHORIZED", "Session is not active.", status_code=401)

        if session.user_id != str(claims["sub"]):
            raise ApiException("AUTH_UNAUTHORIZED", "Session does not match token.", status_code=401)

        user = self._repository.get_by_id(session.user_id)
        if user is None or user.status.upper() != "ACTIVE":
            raise ApiException("AUTH_USER_INACTIVE", "User is not active.", status_code=401)

        return AuthenticatedUser(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            role=user.role,
        )

    def _issue_session(self, user: StoredUser) -> TokenPair:
        session_id = str(uuid4())
        access_token, refresh_token, refresh_expires_at = issue_token_pair(
            user_id=user.id,
            email=user.email,
            full_name=user.full_name,
            role=user.role,
            session_id=session_id,
            secret=self._config.jwt_secret,
            access_token_ttl_minutes=self._config.access_token_ttl_minutes,
            refresh_token_ttl_days=self._config.refresh_token_ttl_days,
        )

        now_iso = _utc_now_iso()
        session = AuthSession(
            session_id=session_id,
            user_id=user.id,
            email=user.email,
            full_name=user.full_name,
            role=user.role,
            refresh_token_hash=hash_token(refresh_token),
            status="ACTIVE",
            created_at=now_iso,
            updated_at=now_iso,
            expires_at=refresh_expires_at,
        )
        self._session_store.create_session(session)
        return TokenPair(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            user=AuthenticatedUser(id=user.id, email=user.email, full_name=user.full_name, role=user.role),
        )

    def _rotate_session(self, user: StoredUser, session_id: str) -> TokenPair:
        access_token, refresh_token, refresh_expires_at = issue_token_pair(
            user_id=user.id,
            email=user.email,
            full_name=user.full_name,
            role=user.role,
            session_id=session_id,
            secret=self._config.jwt_secret,
            access_token_ttl_minutes=self._config.access_token_ttl_minutes,
            refresh_token_ttl_days=self._config.refresh_token_ttl_days,
        )
        self._session_store.rotate_refresh_token(session_id, hash_token(refresh_token), refresh_expires_at)
        return TokenPair(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            user=AuthenticatedUser(id=user.id, email=user.email, full_name=user.full_name, role=user.role),
        )

    def _decode_access_token(self, token: str) -> dict[str, object]:
        try:
            return decode_jwt(token, self._config.jwt_secret, expected_token_type="access")
        except TokenError as exc:
            raise ApiException("AUTH_UNAUTHORIZED", str(exc), status_code=401) from exc

    def _decode_refresh_token(self, token: str) -> dict[str, object]:
        try:
            return decode_jwt(token, self._config.jwt_secret, expected_token_type="refresh")
        except TokenError as exc:
            raise ApiException("AUTH_UNAUTHORIZED", str(exc), status_code=401) from exc

    def _load_session(self, session_id: object) -> AuthSession | None:
        if not isinstance(session_id, str):
            return None
        return self._session_store.get_session(session_id)

    def _resolve_session_id(self, refresh_token: str | None, access_token: str | None) -> str:
        if access_token:
            try:
                claims = self._decode_access_token(access_token)
                session_id = claims.get("session_id")
                if isinstance(session_id, str):
                    return session_id
            except ApiException:
                if refresh_token is None:
                    raise

        if refresh_token:
            claims = self._decode_refresh_token(refresh_token)
            session_id = claims.get("session_id")
            if isinstance(session_id, str):
                return session_id

        raise ApiException("AUTH_UNAUTHORIZED", "Authentication token required.", status_code=401)
