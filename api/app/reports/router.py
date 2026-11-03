from typing import Any

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from app.deps import ConsentedUser, Db
from app.reports.service import latest_report

router = APIRouter(prefix="/api/reports", tags=["reports"])


class ReportView(BaseModel):
    week_start: str
    metrics: dict[str, Any]


@router.get("/latest")
def get_latest(db: Db, user: ConsentedUser) -> ReportView:
    report = latest_report(db, user.id)
    if report is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Henüz haftalık rapor yok.")
    return ReportView(week_start=report.week_start.isoformat(), metrics=report.metrics)
