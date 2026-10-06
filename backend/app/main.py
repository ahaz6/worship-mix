"""Worship Mix - FastAPI entrypoint."""
from fastapi import FastAPI

from app.api.routes import router

app = FastAPI(title="Worship Mix", version="0.1.0")
app.include_router(router, prefix="/api")


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "app": "worship-mix"}
