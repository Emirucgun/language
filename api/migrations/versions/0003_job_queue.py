"""job queue (procrastinate) in its own schema

Revision ID: 0003
Revises: 0002
Create Date: 2026-11-03 21:30:00

Procrastinate'in tabloları ve fonksiyonları `procrastinate` şemasına kurulur; uygulama
şemalarıyla (content, learning) karışmaz. Bağlantılar bu şemayı `search_path` ile görür
(app/jobs.py). Procrastinate sürüm yükseltmesinde kendi göç dosyaları yeni bir Alembic
göçüyle uygulanır.
"""

import os
from collections.abc import Sequence

from alembic import op
from procrastinate.schema import SchemaManager

revision: str = "0003"
down_revision: str | Sequence[str] | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

APP_ROLE = os.environ.get("APP_DB_ROLE", "teacher_app")
SCHEMA = "procrastinate"


def upgrade() -> None:
    op.execute(f"CREATE SCHEMA {SCHEMA}")
    # Şema SQL'i nitelenmemiş adlar kullanır; bu transaction'da hedef şemaya yönlendir.
    # Ham imleç: parametresiz çalışır, SQL içindeki % karakterleri yer tutucu sanılmaz.
    cursor = op.get_bind().connection.dbapi_connection.cursor()  # type: ignore[union-attr]
    cursor.execute(f"SELECT set_config('search_path', '{SCHEMA}', true)")
    cursor.execute(SchemaManager.get_schema())
    cursor.execute("SELECT set_config('search_path', '\"$user\", public', true)")

    # Kuyruk tabloları iş verisi değil: uygulama rolü işleri silebilir/temizleyebilir.
    op.execute(f"GRANT USAGE ON SCHEMA {SCHEMA} TO {APP_ROLE}")
    op.execute(
        f"GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA {SCHEMA} TO {APP_ROLE}"
    )
    op.execute(f"GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA {SCHEMA} TO {APP_ROLE}")
    op.execute(f"GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA {SCHEMA} TO {APP_ROLE}")


def downgrade() -> None:
    op.execute(f"DROP SCHEMA {SCHEMA} CASCADE")
