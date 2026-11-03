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

    # Giriş (Technical MVP, Bölüm 5)
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
