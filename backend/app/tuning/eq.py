"""Room Tuning - automatic room EQ (PEQ fit, 31-band GEQ, minimum-phase FIR).

Tuning rules (WORSHIP_MIX.md ch. 11a):
- Below the Schroeder frequency (~300 Hz in small rooms, lower in large
  churches) room modes dominate: correct peaks with narrow filters.
- Above it, only correct broad regions (an octave or more): Q is capped.
- Never chase narrow dips (position-dependent cancellations): no boost where a
  dip is narrower than 1/3 octave, and never boost where SNR is too low.
- Above `fmax` (default 12 kHz) nothing is corrected.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.optimize import least_squares

from app.tuning.biquad import Filter, response_db

BOOST_Q_LIMIT = 4.3  # ~1/3 octave

ISO_31 = [20, 25, 31.5, 40, 50, 63, 80, 100, 125, 160, 200, 250, 315, 400, 500, 630, 800, 1000, 1250,
          1600, 2000, 2500, 3150, 4000, 5000, 6300, 8000, 10000, 12500, 16000, 20000]


@dataclass
class EqSettings:
    fmin: float = 30.0
    fmax: float = 12000.0
    max_gain_db: float = 9.0
    max_boost_db: float = 4.0       # boosts are risky live (headroom, feedback)
    allow_only_cuts: bool = False
    max_filters: int = 8
    max_q: float = 8.0
    allow_shelves: bool = True
    schroeder_hz: float = 300.0
    broad_q_limit: float = 2.0      # max Q above Schroeder
    stop_below_db: float = 1.0      # stop adding filters when residual is this small
    min_snr_db: float = 10.0
    fs: int = 48000


def _smooth_db(grid: np.ndarray, db: np.ndarray, fraction: float) -> np.ndarray:
    half = 2 ** (1 / (2 * fraction))
    p = 10 ** (db / 10)
    return np.array([10 * np.log10(p[(grid >= f / half) & (grid <= f * half)].mean()) for f in grid])


def correction_error(grid, measured_db, target_db, s: EqSettings) -> np.ndarray:
    """Deviation to correct: fine below Schroeder (1/6 oct), broad above (1 oct)."""
    fine = _smooth_db(grid, measured_db, 6)
    broad = _smooth_db(grid, measured_db, 1)
    blend = np.clip((np.log2(grid / s.schroeder_hz) + 0.5), 0, 1)  # crossfade over one octave
    smoothed = fine * (1 - blend) + broad * blend
    return smoothed - target_db


def _bandwidth_q(grid, err, idx) -> float:
    half = err[idx] / 2
    sign = np.sign(err[idx])
    lo = idx
    while lo > 0 and sign * err[lo] > sign * half:
        lo -= 1
    hi = idx
    while hi < len(err) - 1 and sign * err[hi] > sign * half:
        hi += 1
    bw = max(np.log2(grid[hi] / grid[lo]), 0.05)
    return float(np.sqrt(2**bw) / (2**bw - 1))


def fit_peq(grid, measured_db, target_db, s: EqSettings | None = None, snr_db=None) -> dict:
    s = s or EqSettings()
    err = correction_error(grid, measured_db, target_db, s)
    band = (grid >= s.fmin) & (grid <= s.fmax)
    valid = band.copy()
    if snr_db is not None:
        valid &= snr_db >= s.min_snr_db
    max_boost = 0.0 if s.allow_only_cuts else min(s.max_boost_db, s.max_gain_db)

    def q_cap(freq):
        return s.max_q if freq < s.schroeder_hz else min(s.max_q, s.broad_q_limit)

    filters: list[Filter] = []
    # 1) broad tilt via shelves
    if s.allow_shelves:
        hi_sel = valid & (grid >= 5000)
        if hi_sel.any() and abs(err[hi_sel].mean()) > 1.5:
            g = float(np.clip(-err[hi_sel].mean(), -s.max_gain_db, max_boost))
            if g != 0:
                filters.append(Filter("high_shelf", 5000.0, g, 0.7))

    # 2) greedy peak placement
    for _ in range(64):
        if len(filters) >= s.max_filters:
            break
        resid = err + response_db(filters, grid, s.fs)
        cand = np.where(valid, resid, 0.0)
        # dips: only broad ones may be boosted
        order = np.argsort(-np.abs(cand))
        placed = False
        for idx in order[:40]:
            r = cand[idx]
            if abs(r) < s.stop_below_db:
                break
            q = _bandwidth_q(grid, resid, idx)
            if r < 0 and (max_boost <= 0 or q > BOOST_Q_LIMIT):  # narrow dip -> leave it
                continue
            gain = float(np.clip(-r, -s.max_gain_db, max_boost))
            filters.append(Filter("peak", float(grid[idx]), gain, float(np.clip(q, 0.5, q_cap(grid[idx])))))
            placed = True
            break
        if not placed:
            break

    # 3) joint refinement
    if filters:
        filters = _refine(filters, grid, err, valid, s, max_boost, q_cap)
    filters = [f for f in filters if abs(f.gain_db) >= 0.3]
    corr = response_db(filters, grid, s.fs)
    resid = err + corr
    inside = valid if valid.any() else band
    return {
        "filters": filters,
        "correction_db": corr,
        "predicted_db": measured_db + corr,
        "max_boost_db": float(max(0.0, corr[band].max())) if band.any() else 0.0,
        "rms_error_before_db": float(np.sqrt(np.mean(err[inside] ** 2))),
        "rms_error_after_db": float(np.sqrt(np.mean(resid[inside] ** 2))),
        "within_tolerance_pct": float(np.mean(np.abs(resid[valid]) <= 3.0) * 100) if valid.any() else 0.0,
    }


def _refine(filters, grid, err, valid, s: EqSettings, max_boost, q_cap):
    x0, lo, hi = [], [], []
    for f in filters:
        boost = f.gain_db > 0
        qmax = 1.0 if f.type != "peak" else q_cap(f.freq)
        if boost:
            qmax = min(qmax, BOOST_Q_LIMIT)   # never turn a boost into a narrow notch-filler
        qmin = 0.5
        g_lo, g_hi = (0.0, max_boost + 1e-6) if boost else (-s.max_gain_db, 1e-6)
        x0 += [np.log(f.freq), f.gain_db, np.log(np.clip(f.q, qmin, qmax))]
        lo += [np.log(max(s.fmin, f.freq / 1.5)), g_lo, np.log(qmin)]
        hi += [np.log(min(s.fmax, f.freq * 1.5)), g_hi, np.log(qmax) + 1e-6]
    x0 = np.clip(x0, lo, hi)
    w = valid.astype(float)

    def build(x):
        return [Filter(f.type, float(np.exp(x[3 * i])), float(x[3 * i + 1]), float(np.exp(x[3 * i + 2])))
                for i, f in enumerate(filters)]

    def resid(x):
        return (err + response_db(build(x), grid, s.fs)) * w

    sol = least_squares(resid, x0, bounds=(lo, hi), max_nfev=200)
    return build(sol.x)


def geq31(grid, correction_db, max_gain_db: float = 12.0, step_db: float = 0.5) -> list[dict]:
    """Map a correction curve onto ISO 1/3-octave GEQ bands (for console main GEQs)."""
    out = []
    half = 2 ** (1 / 6)
    for fc in ISO_31:
        sel = (grid >= fc / half) & (grid <= fc * half)
        g = float(np.mean(correction_db[sel])) if sel.any() else 0.0
        g = float(np.clip(np.round(g / step_db) * step_db, -max_gain_db, max_gain_db))
        out.append({"freq": fc, "gain_db": 0.0 if g == 0 else g})
    return out


def min_phase_fir(grid, correction_db, fs: int = 48000, taps: int = 4096, fmin=30.0, fmax=12000.0) -> np.ndarray:
    """Minimum-phase FIR from a magnitude correction (cepstrum method).

    Zero latency (peak at sample 0) - suitable for live PA processors, unlike
    linear/mixed-phase FIRs that add hundreds of ms of delay.
    """
    n = taps * 4
    f = np.fft.rfftfreq(n, 1 / fs)
    fade = np.clip(np.minimum(np.log2(np.maximum(f, 1) / fmin), np.log2(fmax / np.maximum(f, 1))) + 1, 0, 1)
    mag_db = np.interp(np.log(np.maximum(f, 1)), np.log(grid), correction_db) * fade
    log_mag = np.log(10 ** (mag_db / 20))
    cep = np.fft.irfft(log_mag, n)
    fold = np.zeros(n)
    fold[0] = cep[0]
    fold[1 : n // 2] = 2 * cep[1 : n // 2]
    fold[n // 2] = cep[n // 2]
    h = np.fft.irfft(np.exp(np.fft.rfft(fold)), n)[:taps]
    win = np.ones(taps)
    k = taps // 8
    win[-k:] = 0.5 + 0.5 * np.cos(np.linspace(0, np.pi, k))
    return (h * win).astype(np.float32)
