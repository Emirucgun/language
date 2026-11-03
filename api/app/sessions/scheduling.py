"""Hangi kullanıcının oturumu şimdi ön üretilmeli? (Technical MVP, 7)

Kural: kullanıcının kendi saat diliminde saat 03:00'ü geçtiyse ve bugünün oturumu henüz
hazır değilse üret. Zamanlayıcı 15 dakikada bir çalıştığı için gece kaçan bir kullanıcı
(sunucu kapalıydı, iş hata verdi) ya da gün içinde kaydolan biri de kısa sürede yakalanır.

Maliyet koruması: onboarding'i bitirmemiş ya da 7 gündür hiç gelmemiş kullanıcı için
LLM'e para harcanmaz; geri döndüğünde oturumu istek anında üretilir.
"""

import uuid
from datetime import date

from sqlalchemy import text
from sqlalchemy.orm import Session

GENERATION_HOUR = 3
INACTIVE_DAYS = 7

_DUE = text(
    """
    SELECT u.id, (now() AT TIME ZONE u.timezone)::date AS local_date
    FROM learning.users u
    WHERE u.deleted_at IS NULL
      AND u.consent_at IS NOT NULL
      AND u.is_adult_confirmed
      AND u.goal IS NOT NULL
      AND extract(hour FROM now() AT TIME ZONE u.timezone) >= :hour
      AND (
        u.created_at > now() - make_interval(days => :inactive)
        OR EXISTS (
          SELECT 1 FROM learning.events e
          WHERE e.user_id = u.id AND e.recorded_at > now() - make_interval(days => :inactive)
        )
      )
      AND NOT EXISTS (
        SELECT 1 FROM learning.study_sessions s
        WHERE s.user_id = u.id
          AND s.local_date = (now() AT TIME ZONE u.timezone)::date
          AND s.status IN ('ready', 'completed')
      )
    ORDER BY u.id
    """
)


def users_needing_session(db: Session) -> list[tuple[uuid.UUID, date]]:
    rows = db.execute(_DUE, {"hour": GENERATION_HOUR, "inactive": INACTIVE_DAYS})
    return [(row[0], row[1]) for row in rows]
