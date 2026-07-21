from fastapi import FastAPI

from app.config import settings

app = FastAPI(title="Manuens")


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/readyz")
def readyz() -> dict[str, str]:
    settings.validate_ready()
    return {"status": "ready"}
