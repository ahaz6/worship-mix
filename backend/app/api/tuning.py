"""Room Tuning API (module 6)."""
from __future__ import annotations

import io

import numpy as np
import soundfile as sf
from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel, Field

from app.tuning import store
from app.tuning.acoustics import analyze_room
from app.tuning.alignment import align, match_levels, suggest_crossover
from app.tuning.biquad import Filter
from app.tuning.eq import EqSettings, fit_peq, geq31, min_phase_fir
from app.tuning.export import (
    camilladsp_yaml,
    console_plan,
    impulse_wav,
    minidsp_biquads,
    peq_text,
    room_eq_changes,
)
from app.tuning.measure import MeasurementError, average, measure
from app.tuning.signals import FS, PINK_PERIOD, pink_noise, pink_period, test_signal
from app.tuning.targets import (
    BUILTIN,
    TOLERANCE_DB,
    fit_offset,
    interpolate,
    parse_curve,
    target_on_grid,
)

router = APIRouter(prefix="/tuning", tags=["room tuning"])


def _wav(x: np.ndarray, name: str) -> Response:
    buf = io.BytesIO()
    sf.write(buf, x.astype(np.float32), FS, format="WAV", subtype="FLOAT")
    return Response(buf.getvalue(), media_type="audio/wav",
                    headers={"Content-Disposition": f'attachment; filename="{name}"'})


@router.get("/test-signal.wav")
def get_test_signal() -> Response:
    return _wav(test_signal(), "WorshipMix-TestSignal.wav")


@router.get("/pink-noise.wav")
def get_pink_noise(seconds: float = 60.0) -> Response:
    return _wav(pink_noise(min(seconds, 300.0)), "WorshipMix-PinkNoise.wav")


@router.get("/pink-period.f32")
def get_pink_period() -> Response:
    """Raw little-endian float32 samples of one period (48 kHz) for the browser analyzer."""
    return Response(pink_period().astype("<f4").tobytes(), media_type="application/octet-stream",
                    headers={"X-Sample-Rate": str(FS), "X-Period": str(PINK_PERIOD), "Cache-Control": "max-age=86400"})


class ImportResponseIn(BaseModel):
    label: str = "Real-time capture"
    freqs: list[float]
    magnitude_db: list[float | None]
    phase_deg: list[float | None] | None = None
    coherence: list[float | None] | None = None


@router.post("/import-response")
def import_response(body: ImportResponseIn) -> dict:
    """Store a browser real-time transfer function as a measurement (usable by Equalize)."""
    from app.tuning.measure import Measurement, freq_grid

    f = np.asarray(body.freqs, float)
    if len(f) < 8 or np.any(np.diff(f) <= 0):
        raise HTTPException(400, "Frequencies must ascend.")

    def col(v: list | None, fill: float) -> np.ndarray:
        a = np.array([fill if x is None else x for x in (v or [fill] * len(f))], float)
        return a

    grid = freq_grid()
    lg = np.log(grid)
    lf = np.log(f)
    mag = np.interp(lg, lf, col(body.magnitude_db, -120.0))
    phase = np.interp(lg, lf, col(body.phase_deg, 0.0))
    coh = np.clip(np.interp(lg, lf, col(body.coherence, 0.0)), 0, 0.9999)
    snr = 10 * np.log10(coh / (1 - coh) + 1e-12)        # coherence -> SNR
    snr[(grid < f[0]) | (grid > f[-1])] = -99.0
    m = Measurement(grid, mag, phase, np.zeros_like(grid), snr, np.zeros(1024), FS, 0.0,
                    meta={"source": "realtime"})
    return _summary(store.add(body.label, m, {}))


@router.get("/targets")
def targets() -> dict:
    out = {k: {"label": v["label"], "use": v["use"], "points": v["points"], "builtin": True} for k, v in BUILTIN.items()}
    for k, (f, g) in store.CUSTOM_CURVES.items():
        out[k] = {"label": k, "use": "Custom curve", "points": list(zip(f.tolist(), g.tolist())), "builtin": False}
    return {"tolerance_db": TOLERANCE_DB, "curves": out}


@router.post("/targets")
async def upload_target(name: str = Form(...), file: UploadFile = File(...)) -> dict:
    try:
        store.CUSTOM_CURVES[name] = parse_curve((await file.read()).decode("utf-8", "ignore"))
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    return {"saved": name}


@router.post("/mic-calibration")
async def upload_mic_cal(file: UploadFile | None = None) -> dict:
    if file is None:
        store.MIC_CAL["active"] = None
        return {"calibration": None}
    try:
        store.MIC_CAL["active"] = parse_curve((await file.read()).decode("utf-8", "ignore"))
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    return {"calibration": file.filename}


def _summary(mid: str) -> dict:
    e = store.MEASUREMENTS[mid]
    return {"id": mid, "label": e["label"], "room": e["room"], **e["m"].to_dict()}


@router.post("/measure")
async def post_measure(file: UploadFile = File(...), label: str = Form("Position"),
                       remove_delay: bool = Form(True), room_volume_m3: float | None = Form(None)) -> dict:
    audio, fs = sf.read(io.BytesIO(await file.read()), always_2d=False)
    try:
        m = measure(np.asarray(audio, dtype=float), fs, remove_delay=remove_delay, mic_cal=store.MIC_CAL["active"])
    except MeasurementError as e:
        raise HTTPException(422, str(e)) from e
    room = analyze_room(m.ir, m.fs, room_volume_m3)
    room["volume_m3"] = room_volume_m3
    return _summary(store.add(label, m, room))


@router.get("/measurements")
def list_measurements() -> list[dict]:
    return [_summary(mid) for mid in store.MEASUREMENTS]


@router.delete("/measurements/{mid}")
def delete_measurement(mid: str) -> dict:
    store.MEASUREMENTS.pop(mid, None)
    return {"deleted": mid}


class AverageIn(BaseModel):
    ids: list[str]
    label: str = "Listening area average"


@router.post("/average")
def post_average(body: AverageIn) -> dict:
    try:
        ms = [store.get(i) for i in body.ids]
    except KeyError as e:
        raise HTTPException(404, f"Unknown measurement {e}") from e
    m = average(ms)
    volume = next((store.MEASUREMENTS[i]["room"].get("volume_m3") for i in body.ids
                   if store.MEASUREMENTS[i]["room"].get("volume_m3")), None)
    room = analyze_room(m.ir, m.fs, volume)
    room["volume_m3"] = volume
    return _summary(store.add(body.label, m, room))


class EqualizeIn(BaseModel):
    measurement_id: str
    target: str = "worship_warm"
    target_offset_db: float | None = None    # None = automatic fit
    fmin: float = 30.0
    fmax: float = 12000.0
    max_gain_db: float = Field(9.0, ge=1, le=15)
    max_boost_db: float = Field(4.0, ge=0, le=15)
    allow_only_cuts: bool = False
    max_filters: int = Field(8, ge=1, le=20)
    max_q: float = Field(8.0, ge=0.5, le=20)
    allow_shelves: bool = True
    schroeder_hz: float = 300.0
    fs: int = 48000
    console: str = "generic"


def _target(name: str, grid: np.ndarray) -> np.ndarray:
    if name in BUILTIN:
        return target_on_grid(name, grid)
    if name in store.CUSTOM_CURVES:
        f, g = store.CUSTOM_CURVES[name]
        return interpolate(f, g, grid)
    raise HTTPException(404, f"Unknown target curve '{name}'")


def _equalize(body: EqualizeIn) -> tuple[dict, dict]:
    try:
        m = store.get(body.measurement_id)
    except KeyError as e:
        raise HTTPException(404, "Unknown measurement") from e
    grid = m.freqs
    tgt = _target(body.target, grid)
    offset = fit_offset(m.magnitude_db, tgt, grid) if body.target_offset_db is None else body.target_offset_db
    tgt = tgt + offset
    s = EqSettings(fmin=body.fmin, fmax=body.fmax, max_gain_db=body.max_gain_db, max_boost_db=body.max_boost_db,
                   allow_only_cuts=body.allow_only_cuts, max_filters=body.max_filters, max_q=body.max_q,
                   allow_shelves=body.allow_shelves, schroeder_hz=body.schroeder_hz, fs=body.fs)
    r = fit_peq(grid, m.magnitude_db, tgt, s, m.snr_db)
    geq = geq31(grid, r["correction_db"])
    preamp = -round(r["max_boost_db"], 1)
    ok = m.snr_db >= 10.0

    def blank(a: np.ndarray) -> list:
        return [round(float(v), 2) if k else None for v, k in zip(a, ok)]

    out = {
        "freqs": grid.round(2).tolist(),
        "measured_db": blank(m.magnitude_db),
        "target_db": tgt.round(2).tolist(),
        "target_offset_db": round(offset, 2),
        "tolerance_db": TOLERANCE_DB,
        "correction_db": r["correction_db"].round(2).tolist(),
        "predicted_db": blank(r["predicted_db"]),
        "filters": [f.to_dict() for f in r["filters"]],
        "geq31": geq,
        "max_boost_db": round(r["max_boost_db"], 2),
        "preamp_db": preamp,
        "rms_error_before_db": round(r["rms_error_before_db"], 2),
        "rms_error_after_db": round(r["rms_error_after_db"], 2),
        "within_tolerance_pct": round(r["within_tolerance_pct"], 1),
        "console_plan": console_plan(r["filters"], geq, body.console, preamp),
        "console_changes": [c.to_dict() for c in room_eq_changes(r["filters"], geq)],
    }
    return out, {"filters": r["filters"], "grid": grid, "correction": r["correction_db"], "preamp": preamp}


@router.post("/equalize")
def post_equalize(body: EqualizeIn) -> dict:
    return _equalize(body)[0]


class ExportIn(EqualizeIn):
    format: str = "peq_text"   # peq_text | minidsp | camilladsp | fir_wav | console


@router.post("/export")
def post_export(body: ExportIn) -> Response:
    out, raw = _equalize(body)
    filters: list[Filter] = raw["filters"]
    if body.format == "minidsp":
        return _text(minidsp_biquads(filters, body.fs), f"WorshipMix-biquads-{body.fs}.txt")
    if body.format == "peq_text":
        return _text(peq_text(filters, raw["preamp"]), "WorshipMix-PEQ.txt")
    if body.format == "camilladsp":
        return _text(camilladsp_yaml(filters), "WorshipMix-camilladsp.yml")
    if body.format == "fir_wav":
        fir = min_phase_fir(raw["grid"], raw["correction"], fs=body.fs, fmin=body.fmin, fmax=body.fmax)
        return Response(impulse_wav(fir, body.fs), media_type="audio/wav",
                        headers={"Content-Disposition": f'attachment; filename="WorshipMix-FIR-minphase-{body.fs}.wav"'})
    if body.format == "console":
        plan = out["console_plan"]
        text = "\n".join(["Worship Mix room correction", "", *plan["peq_steps"], "", "GEQ (31 band):",
                          *(plan["geq_steps"] or ["(no changes)"])])
        return _text(text + "\n", "WorshipMix-console-steps.txt")
    raise HTTPException(400, "Unknown export format")


def _text(s: str, name: str) -> Response:
    return Response(s, media_type="text/plain", headers={"Content-Disposition": f'attachment; filename="{name}"'})


class AlignIn(BaseModel):
    main_id: str
    sub_id: str
    crossover_hz: float | None = None


@router.post("/align")
def post_align(body: AlignIn) -> dict:
    try:
        main, sub = store.get(body.main_id), store.get(body.sub_id)
    except KeyError as e:
        raise HTTPException(404, "Unknown measurement") from e
    xo = suggest_crossover(main, sub)
    f = body.crossover_hz or xo.get("suggested_hz") or 100.0
    return {"crossover": xo, "alignment": align(main, sub, f), "levels": match_levels(main, sub, f)}
