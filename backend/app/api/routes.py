from __future__ import annotations

import io

import soundfile as sf
from fastapi import APIRouter, File, UploadFile
from pydantic import BaseModel

from app.analysis.metrics import analyze
from app.analysis.tips import generate_tips
from app.consoles.registry import ADAPTERS
from app.mastering.pipeline import LOUDNESS_TARGETS
from app.presets.loader import build_scene, load_presets

router = APIRouter()


@router.post("/analyze")
async def analyze_upload(file: UploadFile = File(...), target_lufs: float = -14.0) -> dict:
    audio, sr = sf.read(io.BytesIO(await file.read()), always_2d=True)
    metrics = analyze(audio, sr)
    return {"metrics": metrics, "tips": [t.model_dump() for t in generate_tips(metrics, target_lufs)]}


@router.get("/consoles/types")
def console_types() -> list[dict]:
    return [{"name": n, "capabilities": sorted(a.__new__(a).capabilities())} for n, a in ADAPTERS.items()]


@router.get("/mastering/targets")
def mastering_targets() -> dict:
    return LOUDNESS_TARGETS


@router.get("/presets")
def presets() -> dict:
    return load_presets()


class LineupItem(BaseModel):
    name: str
    instrument: str


@router.post("/scenes/generate")
def scenes_generate(lineup: list[LineupItem]) -> list[dict]:
    return build_scene([i.model_dump() for i in lineup])
