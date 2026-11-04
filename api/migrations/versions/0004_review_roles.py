"""reviewer role and review verdicts

Revision ID: 0004
Revises: 0003
Create Date: 2026-11-04 17:00:00

Inceleme ekranı için kullanıcı rolü ve dört kararlı `reviews`. `wrong_teaching` sütunu kalkar:
karar artık kendisi söylüyor. `source` H4 için gerekli: "sorun var" işaretli içerik rastgele
örneklem değildir, oran yalnızca `sample` kayıtlarından hesaplanır.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: str | Sequence[str] | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "learning"


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("role", sa.String(length=16), server_default="learner", nullable=False),
        schema=SCHEMA,
    )
    op.create_check_constraint(
        op.f("ck_users_role"), "users", "role IN ('learner','reviewer')", schema=SCHEMA
    )

    op.drop_constraint(op.f("ck_reviews_verdict"), "reviews", schema=SCHEMA)
    op.alter_column(
        "reviews", "verdict", type_=sa.String(length=16), existing_nullable=False, schema=SCHEMA
    )
    op.execute(
        "UPDATE learning.reviews SET verdict = CASE verdict "
        "WHEN 'ok' THEN 'correct' WHEN 'wrong' THEN 'wrong_teaching' ELSE 'unclear' END"
    )
    op.create_check_constraint(
        op.f("ck_reviews_verdict"),
        "reviews",
        "verdict IN ('correct','wrong_teaching','off_level','unclear')",
        schema=SCHEMA,
    )
    op.drop_column("reviews", "wrong_teaching", schema=SCHEMA)
    op.add_column(
        "reviews",
        sa.Column("source", sa.String(length=8), server_default="sample", nullable=False),
        schema=SCHEMA,
    )
    op.create_check_constraint(
        op.f("ck_reviews_source"), "reviews", "source IN ('sample','flag')", schema=SCHEMA
    )


def downgrade() -> None:
    op.drop_constraint(op.f("ck_reviews_source"), "reviews", schema=SCHEMA)
    op.drop_column("reviews", "source", schema=SCHEMA)
    op.add_column(
        "reviews",
        sa.Column("wrong_teaching", sa.Boolean(), server_default="false", nullable=False),
        schema=SCHEMA,
    )
    op.alter_column("reviews", "wrong_teaching", server_default=None, schema=SCHEMA)
    op.drop_constraint(op.f("ck_reviews_verdict"), "reviews", schema=SCHEMA)
    op.execute(
        "UPDATE learning.reviews SET wrong_teaching = verdict = 'wrong_teaching', "
        "verdict = CASE verdict WHEN 'correct' THEN 'ok' WHEN 'wrong_teaching' THEN 'wrong' "
        "ELSE 'minor' END"
    )
    op.alter_column(
        "reviews", "verdict", type_=sa.String(length=8), existing_nullable=False, schema=SCHEMA
    )
    op.create_check_constraint(
        op.f("ck_reviews_verdict"), "reviews", "verdict IN ('ok','minor','wrong')", schema=SCHEMA
    )

    op.drop_constraint(op.f("ck_users_role"), "users", schema=SCHEMA)
    op.drop_column("users", "role", schema=SCHEMA)
