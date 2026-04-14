from fastapi.testclient import TestClient

from app.main import app


def test_liveness() -> None:
    client = TestClient(app)
    response = client.get("/health/liveness")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_readiness_with_mocked_dependencies(monkeypatch) -> None:
    monkeypatch.setattr("app.api.routers.health.check_database_connection", lambda _: True)
    monkeypatch.setattr("app.api.routers.health.check_redis_connection", lambda _: True)

    client = TestClient(app)
    response = client.get("/health/readiness")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
