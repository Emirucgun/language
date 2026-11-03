from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Uygulama ayarları; değerler ortam değişkenlerinden ya da api/.env dosyasından okunur."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    env: str = "dev"
    database_url: str = "postgresql+psycopg://teacher_app@localhost:5432/teacher_dev"
    anthropic_api_key: SecretStr | None = None

    # Model bir ayardır (Technical MVP, Bölüm 6.1).
    llm_model_generation: str = "claude-haiku-5-5"
    llm_model_feedback: str = "claude-sonnet-5-5"
    llm_model_curriculum: str = "claude-sonnet-5-5"
    llm_daily_call_limit_per_user: int = 20


settings = Settings()
