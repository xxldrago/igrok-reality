"""Application configuration loaded from environment variables."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Pydantic Settings class — reads from .env file or environment."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )

    # Telegram
    BOT_TOKEN: str = ""
    BOT_USERNAME: str = ""
    MASTER_CHANNEL_ID: int = 0
    QUEST_CHANNEL_ID: int = 0
    PAYMENT_CHANNEL_ID: int = 0

    # TMA (Telegram Mini App)
    TMA_BOT_TOKEN: str = ""  # Falls back to BOT_TOKEN if empty
    TMA_WEBAPP_URL: str = "https://localhost:8000"

    @property
    def effective_tma_token(self) -> str:
        """Return TMA_BOT_TOKEN or fall back to BOT_TOKEN."""
        return self.TMA_BOT_TOKEN or self.BOT_TOKEN

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://igrok:igrok@postgres:5432/igrok"

    # Redis
    REDIS_URL: str = "redis://redis:6379/0"

    # Platega.io
    PLATEGA_MERCHANT_ID: str = ""
    PLATEGA_SECRET: str = ""
    PLATEGA_WEBHOOK_URL: str = ""

    # Commission
    COMMISSION_RATE: float = 0.10

    # JWT Auth
    JWT_SECRET: str = "change-me-in-production"
    ADMIN_USERNAME: str = "admin"
    ADMIN_PASSWORD: str = "admin"

    # Application
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"
    TZ: str = "Europe/Moscow"


settings = Settings()
