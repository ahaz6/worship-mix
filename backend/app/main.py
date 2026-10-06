"""Worship Mix - FastAPI entrypoint."""
from fastapi import FastAPI

from app.api.consoles import router as consoles_router
from app.api.instruments import router as instruments_router
from app.api.routes import router
from app.api.tuning import router as tuning_router

app = FastAPI(title="Worship Mix", version="0.1.0")
app.include_router(router, prefix="/api")
app.include_router(tuning_router, prefix="/api")
app.include_router(consoles_router, prefix="/api")
app.include_router(instruments_router, prefix="/api")


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "app": "worship-mix"}
