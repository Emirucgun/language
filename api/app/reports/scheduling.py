"""Haftalık değerlendirme kimin için şimdi çalışmalı?

Kural: kullanıcının kendi saat diliminde pazar ve saat 20:00'yi geçmiş, onboarding bitmiş
ve bu haftanın (pazartesi başlangıçlı) raporu henüz yazılmamış. Zamanlayıcı saatte bir
çalıştığı için pazar gecesi kaçan biri sonraki saatlerde yakalanır.
"""

import uuid
from datetime import date

from sqlalchemy import text
from sqlalchemy.orm import Session

REPORT_HOUR = 20

_DUE = text(
    """
    WITH local AS (
      SELECT u.id, now() AT TIME ZONE u.timezone AS ts
      FROM learning.users u
      WHERE u.deleted_at IS NULL AND u.consent_at IS NOT NULL AND u.is_adult_confirmed
        AND u.goal IS NOT NULL
    )
    SELECT l.id, (l.ts::date - (extract(isodow FROM l.ts)::int - 1)) AS week_start
    FROM local l
    WHERE extract(isodow FROM l.ts) = 7
      AND extract(hour FROM l.ts) >= :hour
      AND NOT EXISTS (
        SELECT 1 FROM learning.weekly_reports r
        WHERE r.user_id = l.id
          AND r.week_start = (l.ts::date - (extract(isodow FROM l.ts)::int - 1))
      )
    ORDER BY l.id
    """
)


def users_needing_review(db: Session) -> list[tuple[uuid.UUID, date]]:
    return [(row[0], row[1]) for row in db.execute(_DUE, {"hour": REPORT_HOUR})]
