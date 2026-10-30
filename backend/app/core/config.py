from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    GOOGLE_CLIENT_ID: str
    JWT_SECRET: str
    DATABASE_URL: str
    CORS_ORIGINS: list[str] = Field(default_factory=lambda: ["http://localhost:3000"])

    model_config = SettingsConfigDict(
        env_file=".env"
    )


settings = Settings()