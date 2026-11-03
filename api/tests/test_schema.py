"""Şema kuralları: göç döngüsü, append-only olaylar, tekrar etmeyen içerik, salt okunur içerik."""

import psycopg
import pytest
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from sqlalchemy import create_engine

from app.models import Base
from tests.conftest import _libpq_url


def test_migration_roundtrip_and_models_in_sync(migrated_db: Config) -> None:
    command.downgrade(migrated_db, "base")
    command.upgrade(migrated_db, "head")

    engine = create_engine(migrated_db.get_main_option("sqlalchemy.url") or "")
    with engine.connect() as conn:
        context = MigrationContext.configure(
            conn,
            opts={
                "include_schemas": True,
                "include_name": lambda name, type_, _: (
                    type_ != "schema" or name in {"content", "learning"}
                ),
            },
        )
        diff = compare_metadata(context, Base.metadata)
    engine.dispose()
    assert diff == [], f"Modeller ile göç farklı: {diff}"


def _new_user(conn: psycopg.Connection) -> str:
    row = conn.execute(
        "INSERT INTO learning.users (email) VALUES (gen_random_uuid()::text || '@test') "
        "RETURNING id"
    ).fetchone()
    assert row is not None
    return str(row[0])


def _new_content(conn: psycopg.Connection, *, kind: str = "recall", shareable: bool = False) -> int:
    row = conn.execute(
        "INSERT INTO learning.activity_contents "
        "(content_hash, kind, item_ids, cefr_sub, content, validator_version, "
        " validator_result, status, shareable) "
        "VALUES (sha256(gen_random_uuid()::text::bytea), %s, '{}', 'A1.1', '{}', 'v1', '{}', "
        " 'approved', %s) "
        "RETURNING id",
        (kind, shareable),
    ).fetchone()
    assert row is not None
    return int(row[0])


def test_events_are_append_only_for_app_role(app_conn: psycopg.Connection) -> None:
    user_id = _new_user(app_conn)
    app_conn.execute(
        "INSERT INTO learning.events (user_id, type, occurred_at) "
        "VALUES (%s, 'report_viewed', now())",
        (user_id,),
    )

    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        app_conn.execute("UPDATE learning.events SET type = type")
    app_conn.rollback()

    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        app_conn.execute("DELETE FROM learning.events")


def test_app_role_cannot_delete_anything(app_conn: psycopg.Connection) -> None:
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        app_conn.execute("DELETE FROM learning.users")


def test_content_schema_is_read_only_for_app_role(app_conn: psycopg.Connection) -> None:
    app_conn.execute("SELECT count(*) FROM content.items").fetchone()
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        app_conn.execute(
            "INSERT INTO content.error_tags (code, name_tr, explanation_tr) VALUES ('x', 'x', 'x')"
        )


def test_same_content_is_never_shown_twice_to_a_user(app_conn: psycopg.Connection) -> None:
    user_id = _new_user(app_conn)
    content_id = _new_content(app_conn, shareable=True)
    insert = (
        "INSERT INTO learning.activities (user_id, content_id, origin, recommended) "
        "VALUES (%s, %s, 'session', true)"
    )
    app_conn.execute(insert, (user_id, content_id))
    # Başka bir kullanıcı aynı içeriği görebilir.
    app_conn.execute(insert, (_new_user(app_conn), content_id))

    with pytest.raises(psycopg.errors.UniqueViolation):
        app_conn.execute(insert, (user_id, content_id))


def test_only_short_kinds_can_be_shared(app_conn: psycopg.Connection) -> None:
    _new_content(app_conn, kind="new_item", shareable=True)
    _new_content(app_conn, kind="reading", shareable=False)
    with pytest.raises(psycopg.errors.CheckViolation):
        _new_content(app_conn, kind="reading", shareable=True)


def test_content_hash_is_unique(owner_conn: psycopg.Connection) -> None:
    insert = (
        "INSERT INTO learning.activity_contents "
        "(content_hash, kind, item_ids, cefr_sub, content, validator_version, "
        " validator_result, status) "
        "VALUES (%s, 'recall', '{}', 'A1.1', '{}', 'v1', '{}', 'approved')"
    )
    content_hash = b"\x01" * 32
    owner_conn.execute(insert, (content_hash,))
    with pytest.raises(psycopg.errors.UniqueViolation):
        owner_conn.execute(insert, (content_hash,))


def test_test_db_urls_point_at_test_database() -> None:
    # Testlerin geliştirme verisine dokunmadığından emin ol.
    assert _libpq_url("TEST_DATABASE_URL").endswith("/teacher_test")
    assert _libpq_url("TEST_APP_DATABASE_URL").endswith("/teacher_test")
