"""Geliştirme veritabanına taslak içerik yükler (tekrar çalıştırılabilir).

İçerik şeması uygulama rolüne kapalı olduğu için sahip rolüyle bağlanır.

    cd api
    uv run python -m scripts.seed_dev_content
"""

import os

from dotenv import load_dotenv
from sqlalchemy import create_engine, text

from scripts.dev_content import ERROR_TAGS, ITEMS

load_dotenv()


def main() -> None:
    engine = create_engine(os.environ["MIGRATIONS_DATABASE_URL"])
    with engine.begin() as conn:
        for code, name, explanation in ERROR_TAGS:
            conn.execute(
                text(
                    "INSERT INTO content.error_tags (code, name_tr, explanation_tr) "
                    "VALUES (:c, :n, :e) ON CONFLICT (code) DO UPDATE "
                    "SET name_tr = :n, explanation_tr = :e"
                ),
                {"c": code, "n": name, "e": explanation},
            )
        existing = set(
            conn.scalars(text("SELECT text_en FROM content.items WHERE pool_version = 'dev-seed'"))
        )
        for kind, en, tr, forms in ITEMS:
            if en in existing:
                continue
            conn.execute(
                text(
                    "INSERT INTO content.items (pool_version, kind, text_en, text_tr, cefr, forms) "
                    "VALUES ('dev-seed', :k, :en, :tr, 'A1', :f)"
                ),
                {"k": kind, "en": en, "tr": tr, "f": forms},
            )
    engine.dispose()
    print(f"{len(ERROR_TAGS)} hata etiketi, {len(ITEMS)} öğe yüklendi.")
    print("Seviye sözlüğü için: uv run python -m scripts.import_cefrj")


if __name__ == "__main__":
    main()
