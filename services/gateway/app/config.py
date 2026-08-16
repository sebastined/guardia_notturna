from __future__ import annotations

import secrets

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="GN_", env_file=".env", extra="ignore")

    env: str = "development"
    port: int = 8000

    # Generated per-process when unset, which invalidates tokens on restart.
    # That is the correct failure mode: it is loud in development and forces a
    # real secret to be supplied in production rather than shipping a default.
    jwt_secret: str = ""
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 1440

    kafka_bootstrap: str = "kafka:9092"
    opensearch_url: str = "http://opensearch:9200"

    cors_origins: list[str] = ["http://localhost:3000"]

    def model_post_init(self, __context) -> None:
        if not self.jwt_secret:
            if self.env == "production":
                raise RuntimeError("GN_JWT_SECRET must be set in production.")
            object.__setattr__(self, "jwt_secret", secrets.token_urlsafe(48))


settings = Settings()
