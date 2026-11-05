from typing import Literal

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Uygulama ayarları; değerler ortam değişkenlerinden ya da api/.env dosyasından okunur."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    env: str = "dev"
    database_url: str = "postgresql+psycopg://teacher_app@localhost:5432/teacher_dev"
    anthropic_api_key: SecretStr | None = None

    # Model bir ayardır (docs/architecture/llm.md).
    llm_model_generation: str = "claude-haiku-5-5"
    llm_model_feedback: str = "claude-sonnet-5-5"
    llm_model_curriculum: str = "claude-sonnet-5-5"
    llm_daily_call_limit_per_user: int = 20

    # Sağlayıcı amaç grubu başına seçilir; OA-5 kararına kadar varsayılan Claude.
    llm_provider_generation: Literal["anthropic", "openai"] = "anthropic"
    llm_provider_feedback: Literal["anthropic", "openai"] = "anthropic"
    llm_provider_curriculum: Literal["anthropic", "openai"] = "anthropic"
    openai_model_generation: str = "gpt-6-luna"
    openai_model_feedback: str = "gpt-6.1-sol"
    openai_model_curriculum: str = "gpt-6.1-sol"

    # Ses. Yeni ses tanıma kodu yalnızca gpt-transcribe kullanır (OA-7).
    openai_api_key: SecretStr | None = None
    tts_model: str = "gpt-realtime-2.1-mini"
    tts_voice: str = "marin"
    tts_speed: float = 0.8  # A1 için yavaş ve net; kesin değer Işıl'ın dinlemesinden sonra
    transcribe_model: str = "gpt-transcribe"

    # Giriş (docs/architecture/security-privacy.md)
    app_origin: str = "http://localhost:3000"  # magic link bu adrese gider
    login_token_ttl_minutes: int = 15
    login_requests_per_hour: int = 5
    session_ttl_days: int = 30
    session_cookie_name: str = "session"
    consent_version: str = "2026-11-v1"

    # E-posta (Brevo SMTP; sağlayıcıdan bağımsız). smtp_host boşsa bağlantı loga yazılır.
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_user: str | None = None
    smtp_password: SecretStr | None = None
    mail_from: str = "giris@example.com"  # doğrulanmış alan adından olmalı (SPF/DKIM)
    mail_from_name: str = "İngilizce Öğretmenim"

    @property
    def cookie_secure(self) -> bool:
        # Yerelde http; diğer tüm ortamlarda çerez yalnızca https üzerinden gider.
        return self.env != "dev"


settings = Settings()
