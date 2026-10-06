"""Instrument Tuning API (module 03)."""
from __future__ import annotations

import io
import json

import numpy as np
import soundfile as sf
from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

from app.instruments.demo import BPM, demo_band
from app.instruments.demo import FS as DEMO_FS
from app.instruments.live import LIVE, ChannelMap, LiveSession, list_devices, run_analysis
from app.instruments.profiles import PROFILES, as_dict

router = APIRouter(prefix="/instruments", tags=["instrument tuning"])


@router.get("/profiles")
def profiles() -> list[dict]:
    return [as_dict(p) for p in PROFILES.values()]


@router.get("/devices")
def devices() -> list[dict]:
    return list_devices()


@router.post("/demo")
def demo(room_rt60: float | None = 1.8) -> dict:
    band = demo_band()
    tracks, mapping = {}, []
    for i, (name, (profile, x)) in enumerate(band.items()):
        tracks[i] = x
        mapping.append(ChannelMap(i, profile, name, console_channel=i + 1))
    return {"demo": True, "mapping": [m.__dict__ for m in mapping],
            **run_analysis(tracks, DEMO_FS, mapping, room_rt60, BPM)}


@router.post("/analyze")
async def analyze(files: list[UploadFile] = File(...), mapping: str = Form(...),
                  room_rt60: float | None = Form(None), bpm: float | None = Form(None)) -> dict:
    """Upload one multichannel WAV or one file per channel.

    mapping: JSON list of {input_index, profile, name, console_channel?}
    (input_index = channel inside the multichannel file, or file position).
    """
    try:
        maps = [ChannelMap(**m) for m in json.loads(mapping)]
    except (ValueError, TypeError) as e:
        raise HTTPException(400, "Mapping is not valid JSON.") from e
    for m in maps:
        if m.profile not in PROFILES:
            raise HTTPException(400, f"Unknown instrument '{m.profile}'.")
    tracks: dict[int, np.ndarray] = {}
    fs = None
    if len(files) == 1:
        data, fs = sf.read(io.BytesIO(await files[0].read()), always_2d=True)
        tracks = {i: data[:, i] for i in range(data.shape[1])}
    else:
        for i, f in enumerate(files):
            data, rate = sf.read(io.BytesIO(await f.read()), always_2d=True)
            if fs is not None and rate != fs:
                raise HTTPException(400, "All files need the same sample rate.")
            fs = rate
            tracks[i] = data.mean(axis=1)
    n = min(len(x) for x in tracks.values())
    tracks = {i: x[:n] for i, x in tracks.items()}
    return run_analysis(tracks, int(fs), maps, room_rt60, bpm)


class LiveStartIn(BaseModel):
    device: int | str | None = None
    mapping: list[dict]
    room_rt60: float | None = None
    bpm: float | None = None


@router.post("/live/start")
def live_start(body: LiveStartIn) -> dict:
    for s in LIVE.values():
        s.stop()
    LIVE.clear()
    sess = LiveSession(body.device, [ChannelMap(**m) for m in body.mapping], room_rt60=body.room_rt60, bpm=body.bpm)
    try:
        sess.start()
    except RuntimeError as e:
        raise HTTPException(503, str(e)) from e
    LIVE["current"] = sess
    return {"running": True}


@router.get("/live/latest")
def live_latest() -> dict:
    s = LIVE.get("current")
    if s is None:
        return {"running": False}
    return {"running": True, "levels": s.levels, "error": s.error, **s.latest}


@router.post("/live/stop")
def live_stop() -> dict:
    s = LIVE.pop("current", None)
    if s:
        s.stop()
    return {"running": False}
