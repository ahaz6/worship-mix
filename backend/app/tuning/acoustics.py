"""Room acoustics from an impulse response: RT60 (T20/T30), C50, Schroeder frequency.

Why it matters for churches: long reverberation (often 1.5 - 3 s) blurs speech.
C50 (early-to-late energy ratio at 50 ms) is a direct indicator of sermon
intelligibility; RT60 tells the tech how much effect reverb is already "in the
room"; the Schroeder frequency tells the room EQ where modes stop dominating.
"""
from __future__ import annotations

import numpy as np
from scipy.signal import butter, sosfiltfilt

OCTAVES = [125, 250, 500, 1000, 2000, 4000]


def _band(ir: np.ndarray, fs: int, fc: float) -> np.ndarray:
    sos = butter(4, [fc / np.sqrt(2), min(fc * np.sqrt(2), fs / 2 * 0.95)], btype="band", fs=fs, output="sos")
    return sosfiltfilt(sos, ir)


def schroeder_curve_db(ir: np.ndarray) -> np.ndarray:
    e = np.cumsum((ir**2)[::-1])[::-1]
    return 10 * np.log10(e / (e[0] + 1e-30) + 1e-30)


def rt60(ir: np.ndarray, fs: int, start_db: float = -5.0, end_db: float = -25.0) -> float | None:
    """T20 by default (-5 to -25 dB, extrapolated to 60 dB)."""
    edc = schroeder_curve_db(ir)
    i0 = np.argmax(edc <= start_db)
    i1 = np.argmax(edc <= end_db)
    if i1 <= i0 or edc[i1] > end_db:
        return None
    t = np.arange(i0, i1) / fs
    slope, _ = np.polyfit(t, edc[i0:i1], 1)
    return float(-60 / slope) if slope < 0 else None


def c50(ir: np.ndarray, fs: int) -> float:
    p = int(np.argmax(np.abs(ir)))
    k = p + int(0.05 * fs)
    early, late = np.sum(ir[p:k] ** 2), np.sum(ir[k:] ** 2)
    return float(10 * np.log10((early + 1e-30) / (late + 1e-30)))


def schroeder_frequency(rt60_s: float, volume_m3: float) -> float:
    """f_s = 2000 * sqrt(T60 / V)."""
    return float(2000 * np.sqrt(rt60_s / volume_m3))


def analyze_room(ir: np.ndarray, fs: int, volume_m3: float | None = None) -> dict:
    bands = {}
    for fc in OCTAVES:
        b = _band(ir, fs, fc)
        t = rt60(b, fs)
        bands[str(fc)] = {"rt60_s": None if t is None else round(t, 2), "c50_db": round(c50(b, fs), 1)}
    mids = [v["rt60_s"] for k, v in bands.items() if k in ("500", "1000") and v["rt60_s"]]
    rt_mid = float(np.mean(mids)) if mids else None
    c50_speech = float(np.mean([bands[k]["c50_db"] for k in ("500", "1000", "2000")]))
    out = {
        "bands": bands,
        "rt60_mid_s": None if rt_mid is None else round(rt_mid, 2),
        "c50_speech_db": round(c50_speech, 1),
        "speech_rating": "good" if c50_speech >= 3 else "fair" if c50_speech >= 0 else "poor",
    }
    if volume_m3 and rt_mid:
        out["schroeder_hz"] = round(schroeder_frequency(rt_mid, volume_m3), 1)
    return out
