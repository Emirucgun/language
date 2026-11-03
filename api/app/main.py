from fastapi import FastAPI

from app import models  # noqa: F401 - tüm tabloları kaydeder; ilişkiler (FK) çözülebilsin
from app.auth.router import router as auth_router
from app.config import settings
from app.events.router import router as events_router
from app.feedback.router import router as feedback_router
from app.onboarding.router import router as onboarding_router

app = FastAPI(title="Teacher API", version="0.1.0")
app.include_router(auth_router)
app.include_router(onboarding_router)
app.include_router(feedback_router)
app.include_router(events_router)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "env": settings.env}
