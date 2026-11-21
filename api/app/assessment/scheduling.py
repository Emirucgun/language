"""Kime hatırlama testi açılmalı? (docs/architecture/jobs.md)

Ön eleme: 14 günden eski çalışması olan, açık testi olmayan, son testi en az bir hafta önce
açılmış kullanıcılar. Asıl karar `create_test` içindedir: yeterli öğe yoksa test açılmaz.
LLM yok; maliyetsiz olduğu için aktiflik şartı aranmaz, öğrenci döndüğünde test onu bekler.
"""

import uuid

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.scheduler.retention import STUDY_DAYS

TEST_GAP_DAYS = 7

_DUE = text(
    """
    SELECT u.id
    FROM learning.users u
    WHERE u.deleted_at IS NULL
      AND u.consent_at IS NOT NULL
      AND EXISTS (
        SELECT 1 FROM learning.events e
        WHERE e.user_id = u.id AND e.rating IS NOT NULL
          AND e.occurred_at <= now() - make_interval(days => :study)
      )
      AND NOT EXISTS (
        SELECT 1 FROM learning.events c
        WHERE c.user_id = u.id AND c.type = 'retention_test_created'
          AND (
            c.occurred_at > now() - make_interval(days => :gap)
            OR NOT EXISTS (
              SELECT 1 FROM learning.events d
              WHERE d.user_id = u.id AND d.type = 'retention_test_completed'
                AND d.payload->>'test_id' = c.payload->>'test_id'
            )
          )
      )
    ORDER BY u.id
    """
)


def users_needing_retention_test(db: Session) -> list[uuid.UUID]:
    return list(db.scalars(_DUE, {"study": STUDY_DAYS, "gap": TEST_GAP_DAYS}))
