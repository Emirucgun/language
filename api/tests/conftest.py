import os
from collections.abc import Iterator
from pathlib import Path

import psycopg
import pytest
from alembic import command
from alembic.config import Config
from dotenv import load_dotenv

API_DIR = Path(__file__).resolve().parents[1]
load_dotenv(API_DIR / ".env")


def _libpq_url(name: str) -> str:
    url = os.environ.get(name)
    if not url:
        pytest.skip(f"{name} tanımlı değil; veritabanı testleri atlandı")
    return url.replace("+psycopg", "")


@pytest.fixture(scope="session")
def alembic_config() -> Config:
    """teacher_test'i hedefleyen Alembic ayarı (sahip rolüyle)."""
    test_url = os.environ.get("TEST_DATABASE_URL")
    if not test_url:
        pytest.skip("TEST_DATABASE_URL tanımlı değil; veritabanı testleri atlandı")
    # migrations/env.py bu değişkeni okur; load_dotenv mevcut değeri ezmez.
    os.environ["MIGRATIONS_DATABASE_URL"] = test_url
    config = Config(str(API_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(API_DIR / "migrations"))
    return config


@pytest.fixture(scope="session")
def migrated_db(alembic_config: Config) -> Config:
    command.downgrade(alembic_config, "base")
    command.upgrade(alembic_config, "head")
    return alembic_config


@pytest.fixture
def owner_conn(migrated_db: Config) -> Iterator[psycopg.Connection]:
    with psycopg.connect(_libpq_url("TEST_DATABASE_URL")) as conn:
        yield conn
        conn.rollback()


@pytest.fixture
def app_conn(migrated_db: Config) -> Iterator[psycopg.Connection]:
    """Çalışma zamanı rolü; her test sonunda geri alınır."""
    with psycopg.connect(_libpq_url("TEST_APP_DATABASE_URL")) as conn:
        yield conn
        conn.rollback()
