"""test forms

Revision ID: 0006
Revises: 0005
Create Date: 2026-11-05 16:00:00

Ön ve son test aynı kişiye aynı soruları göstermesin diye iki paralel form (DZ-4). Ön mü
son mu olduğu forma değil kişiye bağlıdır; bu yüzden `pre`, `post` ve kişiye özel üretilen
`retention` (DZ-3) amaçları kalkar. Hiç kullanılmamışlardı.

Geri alma B formunu siler: eski şema (amaç, sürüm) çiftinde ikisini ayıramaz.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0006"
down_revision: str | Sequence[str] | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "fixed_tests",
        sa.Column("form", sa.String(length=1), server_default="A", nullable=False),
        schema="content",
    )
    op.create_check_constraint(
        op.f("ck_fixed_tests_form"), "fixed_tests", "form IN ('A','B')", schema="content"
    )
    op.drop_constraint(op.f("ck_fixed_tests_purpose"), "fixed_tests", schema="content")
    op.create_check_constraint(
        op.f("ck_fixed_tests_purpose"), "fixed_tests", "purpose = 'placement'", schema="content"
    )
    op.drop_index(op.f("ix_fixed_tests_purpose_version"), "fixed_tests", schema="content")
    op.create_index(
        op.f("ix_fixed_tests_purpose_form_version"),
        "fixed_tests",
        ["purpose", "form", "version"],
        unique=True,
        schema="content",
    )


def downgrade() -> None:
    op.execute("DELETE FROM content.fixed_tests WHERE form = 'B'")
    op.drop_index(op.f("ix_fixed_tests_purpose_form_version"), "fixed_tests", schema="content")
    op.create_index(
        op.f("ix_fixed_tests_purpose_version"),
        "fixed_tests",
        ["purpose", "version"],
        unique=True,
        schema="content",
    )
    op.drop_constraint(op.f("ck_fixed_tests_purpose"), "fixed_tests", schema="content")
    op.create_check_constraint(
        op.f("ck_fixed_tests_purpose"),
        "fixed_tests",
        "purpose IN ('placement','pre','post','retention')",
        schema="content",
    )
    op.drop_constraint(op.f("ck_fixed_tests_form"), "fixed_tests", schema="content")
    op.drop_column("fixed_tests", "form", schema="content")
