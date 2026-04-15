from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = Field(default="QuantFlow Pro API", alias="QF_APP_NAME")
    env: str = Field(default="local", alias="QF_ENV")
    debug: bool = Field(default=True, alias="QF_DEBUG")
    api_v1_prefix: str = Field(default="/api/v1", alias="QF_API_V1_PREFIX")
    database_url: str = Field(
        default="postgresql+psycopg://quantflow:quantflow@localhost:5432/quantflow",
        alias="QF_DATABASE_URL",
    )
    redis_url: str = Field(default="redis://localhost:6379/0", alias="QF_REDIS_URL")
    jwt_secret: str = Field(default="quantflow-local-secret", alias="QF_JWT_SECRET")
    access_token_ttl_minutes: int = Field(default=15, alias="QF_ACCESS_TOKEN_TTL_MINUTES")
    refresh_token_ttl_days: int = Field(default=7, alias="QF_REFRESH_TOKEN_TTL_DAYS")
    alpaca_api_key: str = Field(default="", alias="QF_ALPACA_API_KEY")
    alpaca_secret_key: str = Field(default="", alias="QF_ALPACA_SECRET_KEY")
    alpaca_base_url: str = Field(default="https://paper-api.alpaca.markets", alias="QF_ALPACA_BASE_URL")
    alpaca_data_url: str = Field(default="https://data.alpaca.markets", alias="QF_ALPACA_DATA_URL")
    allowed_origins_raw: str = Field(
        default="http://localhost:5173,http://127.0.0.1:5173,http://localhost:5175,http://127.0.0.1:5175",
        alias="QF_ALLOWED_ORIGINS",
    )
    log_level: str = Field(default="INFO", alias="QF_LOG_LEVEL")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    @property
    def allowed_origins(self) -> list[str]:
        return [origin.strip() for origin in self.allowed_origins_raw.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
