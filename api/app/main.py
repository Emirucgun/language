from fastapi import FastAPI

from app.config import settings

app = FastAPI(title="Teacher API", version="0.1.0")


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "env": settings.env}
