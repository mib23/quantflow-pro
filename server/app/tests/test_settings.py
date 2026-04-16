from app.core.settings import Settings


def test_settings_load_from_aliases() -> None:
    settings = Settings(
        QF_APP_NAME="QuantFlow Test API",
        QF_ENV="test",
        QF_ALLOWED_ORIGINS="http://localhost:5173,http://localhost:4173",
    )

    assert settings.app_name == "QuantFlow Test API"
    assert settings.env == "test"
    assert settings.allowed_origins == ["http://localhost:5173", "http://localhost:4173"]
