from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    GOOGLE_CLIENT_ID: str
    JWT_SECRET: str
    DATABASE_URL: str

    model_config = SettingsConfigDict(
        env_file=".env"
    )


settings = Settings()