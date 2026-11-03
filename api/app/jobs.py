"""Arka plan işleri (procrastinate, Postgres tabanlı kuyruk; Technical MVP, 7).

Çalıştırma: `uv run python -m app.worker`. Kuyruk tabloları `procrastinate` şemasında
(göç 0003); bağlantı bu şemayı `search_path` ile görür.
"""

import asyncio
import uuid
from datetime import date

from procrastinate import App, PsycopgConnector, RetryStrategy
from procrastinate.exceptions import AlreadyEnqueued

from app import models  # noqa: F401 - tüm tabloları kaydeder
from app.auth.models import User
from app.config import settings
from app.db import SessionLocal
from app.deps import get_llm_client
from app.reports.scheduling import users_needing_review
from app.reports.weekly import weekly_review
from app.sessions.generation import ensure_session
from app.sessions.scheduling import users_needing_session

app = App(
    connector=PsycopgConnector(
        conninfo=settings.database_url.replace("+psycopg", ""),
        kwargs={"options": "-c search_path=procrastinate"},
    )
)


def _due() -> list[tuple[uuid.UUID, date]]:
    with SessionLocal() as db:
        return users_needing_session(db)


@app.periodic(cron="*/15 * * * *", periodic_id="schedule_sessions")
@app.task(name="schedule_sessions", queueing_lock="schedule_sessions")
async def schedule_sessions(timestamp: int) -> int:
    """15 dakikada bir: oturumu hazır olmayan kullanıcılar için üretim işi kuyruğa alınır."""
    queued = 0
    for user_id, local_date in await asyncio.to_thread(_due):
        try:
            # Aynı kullanıcı + gün için kuyrukta tek iş: tekrar eden zamanlayıcı çoğaltmaz.
            await generate_session.configure(
                queueing_lock=f"session:{user_id}:{local_date}"
            ).defer_async(user_id=str(user_id), local_date=local_date.isoformat())
            queued += 1
        except AlreadyEnqueued:
            pass
    return queued


def _due_reviews() -> list[tuple[uuid.UUID, date]]:
    with SessionLocal() as db:
        return users_needing_review(db)


@app.periodic(cron="5 * * * *", periodic_id="schedule_weekly_reviews")
@app.task(name="schedule_weekly_reviews", queueing_lock="schedule_weekly_reviews")
async def schedule_weekly_reviews(timestamp: int) -> int:
    """Saatte bir: pazar akşamı raporu yazılmamış kullanıcılar için değerlendirme işi."""
    queued = 0
    for user_id, week_start in await asyncio.to_thread(_due_reviews):
        try:
            await weekly_review_job.configure(
                queueing_lock=f"review:{user_id}:{week_start}"
            ).defer_async(user_id=str(user_id), week_start=week_start.isoformat())
            queued += 1
        except AlreadyEnqueued:
            pass
    return queued


@app.task(name="weekly_review", retry=RetryStrategy(max_attempts=3, wait=300))
def weekly_review_job(user_id: str, week_start: str) -> str:
    """Rapor + (aktifse) yeniden planlama; aynı hafta için tekrar çalışması bir şey yapmaz."""
    with SessionLocal() as db:
        user = db.get_one(User, uuid.UUID(user_id))
        report = weekly_review(db, get_llm_client(), user, date.fromisoformat(week_start))
        db.commit()
        return str(report.week_start)


@app.task(name="generate_session", retry=RetryStrategy(max_attempts=3, wait=120))
def generate_session(user_id: str, local_date: str) -> str:
    """Bir kullanıcının o günkü oturumunu üretir. `ensure_session` tekrar çağrılmaya dayanıklı."""
    with SessionLocal() as db:
        user = db.get_one(User, uuid.UUID(user_id))
        study = ensure_session(db, get_llm_client(), user, date.fromisoformat(local_date))
        db.commit()
        return study.status
