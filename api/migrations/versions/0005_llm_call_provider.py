"""llm call provider

Revision ID: 0005
Revises: 0004
Create Date: 2026-11-05 10:00:00

Sağlayıcı karşılaştırması ve karma yönlendirme için. Mevcut kayıtların hepsi Claude'dan.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005"
down_revision: str | Sequence[str] | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "llm_calls",
        sa.Column("provider", sa.String(length=16), server_default="anthropic", nullable=False),
        schema="learning",
    )


def downgrade() -> None:
    op.drop_column("llm_calls", "provider", schema="learning")
