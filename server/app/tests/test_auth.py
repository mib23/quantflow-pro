from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from redis.exceptions import ConnectionError as RedisConnectionError
from sqlalchemy import create_engine, text
from sqlalchemy.pool import StaticPool

from app.main import app
from app.modules.auth import dependencies as auth_dependencies
from app.modules.auth.dependencies import get_auth_service
from app.modules.auth.repository import StoredUser, UserRepository
from app.modules.auth.security import hash_password
from app.modules.auth.service import AuthConfig, AuthService
from app.modules.auth.session_store import InMemorySessionStore


class FakeRepository:
    def __init__(self, users_by_email: dict[str, StoredUser], users_by_id: dict[str, StoredUser]) -> None:
        self.users_by_email = users_by_email
        self.users_by_id = users_by_id

    def get_by_email(self, email: str) -> StoredUser | None:
        return self.users_by_email.get(email.lower())

    def get_by_id(self, user_id: str) -> StoredUser | None:
        return self.users_by_id.get(user_id)


@pytest.fixture()
def auth_service() -> AuthService:
    password_hash = hash_password("quantflow-demo")
    user = StoredUser(
        id="usr_admin_001",
        email="alex@quantflow.local",
        full_name="Alex Johnson",
        password_hash=password_hash,
        role="ADMIN",
        status="ACTIVE",
    )
    repository = FakeRepository(
        users_by_email={user.email.lower(): user},
        users_by_id={user.id: user},
    )
    session_store = InMemorySessionStore()
    config = AuthConfig(jwt_secret="test-secret", access_token_ttl_minutes=5, refresh_token_ttl_days=7)
    return AuthService(repository, session_store, config)


def test_login_refresh_me_and_logout_flow(auth_service: AuthService) -> None:
    app.dependency_overrides[get_auth_service] = lambda: auth_service
    client = TestClient(app)
    try:
        login_response = client.post(
            "/api/v1/auth/login",
            json={"email": "alex@quantflow.local", "password": "quantflow-demo"},
        )
        assert login_response.status_code == 200
        payload = login_response.json()["data"]
        assert payload["token_type"] == "bearer"
        assert payload["user"]["email"] == "alex@quantflow.local"

        access_token = payload["access_token"]
        refresh_token = payload["refresh_token"]

        me_response = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {access_token}"})
        assert me_response.status_code == 200
        assert me_response.json()["data"]["full_name"] == "Alex Johnson"

        refresh_response = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
        assert refresh_response.status_code == 200
        refreshed_payload = refresh_response.json()["data"]
        assert refreshed_payload["access_token"] != access_token
        assert refreshed_payload["refresh_token"] != refresh_token

        logout_response = client.post(
            "/api/v1/auth/logout",
            json={"refresh_token": refreshed_payload["refresh_token"]},
            headers={"Authorization": f"Bearer {refreshed_payload['access_token']}"},
        )
        assert logout_response.status_code == 200
        assert logout_response.json()["data"]["revoked"] is True

        revoked_response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {refreshed_payload['access_token']}"},
        )
        assert revoked_response.status_code == 401
        assert revoked_response.json()["error"]["code"] == "AUTH_UNAUTHORIZED"
    finally:
        app.dependency_overrides.clear()


def test_login_rejects_bad_password(auth_service: AuthService) -> None:
    app.dependency_overrides[get_auth_service] = lambda: auth_service
    client = TestClient(app)
    try:
        response = client.post(
            "/api/v1/auth/login",
            json={"email": "alex@quantflow.local", "password": "wrong-password"},
        )
        assert response.status_code == 401
        assert response.json()["error"]["code"] == "AUTH_INVALID_CREDENTIALS"
    finally:
        app.dependency_overrides.clear()


def test_user_repository_reads_from_sqlite() -> None:
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                CREATE TABLE users (
                    id TEXT PRIMARY KEY,
                    email TEXT NOT NULL UNIQUE,
                    full_name TEXT NOT NULL,
                    password_hash TEXT NOT NULL,
                    role TEXT NOT NULL,
                    status TEXT NOT NULL
                )
                """
            )
        )
        connection.execute(
            text(
                """
                INSERT INTO users (id, email, full_name, password_hash, role, status)
                VALUES (:id, :email, :full_name, :password_hash, :role, :status)
                """
            ),
            {
                "id": "usr_001",
                "email": "test@example.com",
                "full_name": "Test User",
                "password_hash": hash_password("secret"),
                "role": "TRADER",
                "status": "ACTIVE",
            },
        )

    repository = UserRepository(engine)
    user = repository.get_by_email("test@example.com")
    assert user is not None
    assert user.email == "test@example.com"
    assert user.role == "TRADER"


def test_get_auth_session_store_falls_back_to_memory_when_local_redis_is_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    class UnavailableRedisSessionStore:
        def __init__(self, *_args, **_kwargs) -> None:
            pass

        def ping(self) -> bool:
            raise RedisConnectionError("redis unavailable")

    auth_dependencies.get_auth_session_store.cache_clear()
    monkeypatch.setattr(
        auth_dependencies,
        "get_settings",
        lambda: SimpleNamespace(env="local", redis_url="redis://localhost:6379/0"),
    )
    monkeypatch.setattr(auth_dependencies, "RedisSessionStore", UnavailableRedisSessionStore)

    try:
        store = auth_dependencies.get_auth_session_store()
        assert isinstance(store, InMemorySessionStore)
    finally:
        auth_dependencies.get_auth_session_store.cache_clear()
