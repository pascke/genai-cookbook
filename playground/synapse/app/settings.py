from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):

    APP_NAME: str = "Synapse"
    DATABASE_URL: str
    OPENAI_API_KEY: str
    ECHO_SQL: bool = True
    EMBED_MODEL: str = "text-embedding-3-small" # 1536 dims

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
        env_file_encoding="utf-8"
    )

settings = Settings()