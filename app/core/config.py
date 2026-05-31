from __future__ import annotations

import os
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Trading Simulation Backend"
    database_url: str = "sqlite:///./trading_sim.db"
    jwt_secret_key: str = Field(default="dev-change-me", validation_alias="JWT_SECRET_KEY")
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24
    initial_cash: float = 1_000_000.0
    market_tick_interval: float = 30.0
    market_data_timeout: float = 5.0
    market_data_max_age_seconds: float = 90.0
    strategy_tick_interval: float = 5.0
    serve_frontend_dist: bool = True

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def sqlite_connect_args(self) -> dict:
        if self.database_url.startswith("sqlite"):
            return {"check_same_thread": False}
        return {}


@lru_cache
def get_settings() -> Settings:
    # Preserve the existing environment names used by MarketService and the dev workflow.
    settings = Settings(
        market_tick_interval=float(os.getenv("MARKET_REFRESH_INTERVAL", os.getenv("MARKET_TICK_INTERVAL", "30.0"))),
        market_data_timeout=float(os.getenv("MARKET_DATA_TIMEOUT", "5.0")),
        market_data_max_age_seconds=float(os.getenv("MARKET_DATA_MAX_AGE_SECONDS", "90.0")),
        strategy_tick_interval=float(os.getenv("STRATEGY_TICK_INTERVAL", "5.0")),
        serve_frontend_dist=os.getenv("SERVE_FRONTEND_DIST", "1").strip().lower() in {"1", "true", "yes", "on"},
    )
    return settings


settings = get_settings()
