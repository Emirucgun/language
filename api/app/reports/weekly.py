"""Pazar akşamı haftalık değerlendirme: rapor + (aktif öğrencide) yeniden planlama.

Haftada hiç gelmemiş öğrenci için LLM'e para harcanmaz: rapor yine yazılır, plan aynı
kalır. Aynı hafta için ikinci çağrı hiçbir şey yapmaz (rapor tek kez yazılır).
"""

from datetime import date

from sqlalchemy.orm import Session

from app.auth.models import User
from app.curriculum.service import ensure_curriculum
from app.llm.client import LLMClient
from app.reports.models import WeeklyReport
from app.reports.service import compute, latest_report, save


def weekly_review(db: Session, client: LLMClient, user: User, week_start: date) -> WeeklyReport:
    current = latest_report(db, user.id)
    if current is not None and current.week_start == week_start:
        return current

    metrics = compute(db, user, week_start)
    extra: dict[str, object] = {"plan_changed": False}
    if metrics.active_days > 0:
        curriculum = ensure_curriculum(db, client, user, reason="weekly", progress=metrics)
        extra = {
            "plan_changed": True,
            "plan_change_tr": curriculum.skill_weights.get("summary_tr"),
            "curriculum_version": curriculum.version,
        }
    return save(db, user, metrics, extra)
