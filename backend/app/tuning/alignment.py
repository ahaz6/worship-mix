"""Sub/main time alignment, crossover suggestion and level matching.

Measure each source with remove_delay=False and the chirp on the same full
range speaker, so arrival times share one reference.
"""
from __future__ import annotations

import numpy as np

from app.tuning.measure import Measurement


def _at(m: Measurement, arr: np.ndarray, f: float) -> float:
    return float(np.interp(np.log(f), np.log(m.freqs), arr))


def gated_phase_deg(m: Measurement, f: float, gate_ms: float) -> float:
    """Phase at f from a time-gated IR: direct sound + early part only.

    In reverberant rooms the full 500 ms IR is dominated by reflections at low
    frequencies; gating keeps the phase stable (standard practice for alignment).
    """
    n = int(gate_ms / 1000 * m.fs)
    ir = m.ir[:n].copy()
    k = max(1, n // 3)
    ir[-k:] *= 0.5 + 0.5 * np.cos(np.linspace(0, np.pi, k))
    t = np.arange(n) / m.fs
    return float(np.degrees(np.angle(np.sum(ir * np.exp(-2j * np.pi * f * t)))))


def align(main: Measurement, sub: Measurement, crossover_hz: float) -> dict:
    """Delay (ms) to add to the earlier source so both are in phase at the crossover."""
    period_ms = 1000.0 / crossover_hz
    gate_ms = max(20.0, max(main.arrival_ms, sub.arrival_ms, 0.0) + 2.5 * period_ms)
    dphi = (gated_phase_deg(main, crossover_hz, gate_ms) - gated_phase_deg(sub, crossover_hz, gate_ms) + 180) % 360 - 180
    # dphi > 0 means the sub lags the mains at the crossover.
    lag_ms = dphi / 360.0 * period_ms
    arrival_ms = sub.arrival_ms - main.arrival_ms
    # phase is ambiguous by whole periods: pick the solution closest to the measured arrival difference
    lag = min((lag_ms + k * period_ms for k in range(-4, 5)), key=lambda c: abs(c - arrival_ms))
    flip = abs(dphi) > 120 and abs(arrival_ms) < period_ms / 4
    return {
        "crossover_hz": crossover_hz,
        "phase_difference_deg": round(dphi, 1),
        "gate_ms": round(gate_ms, 1),
        "arrival_difference_ms": round(arrival_ms, 2),
        "sub_lag_ms": round(lag, 2),
        "delay_main_ms": round(max(lag, 0.0), 2),
        "delay_sub_ms": round(max(-lag, 0.0), 2),
        "consider_polarity_flip": bool(flip),
        "one_wavelength_ms": round(period_ms, 2),
        "note": (f"One wavelength at {crossover_hz:.0f} Hz is {period_ms:.1f} ms; flipping polarity equals half "
                 f"a wavelength ({period_ms / 2:.1f} ms). Re-measure after every change."),
    }


def _passband(m: Measurement, lo: float, hi: float) -> float:
    sel = (m.freqs >= lo) & (m.freqs <= hi)
    return float(np.mean(m.magnitude_db[sel]))


def suggest_crossover(main: Measurement, sub: Measurement) -> dict:
    """Crossover range where both measured responses still have output (-6 dB points)."""
    ref_main = _passband(main, 200, 2000)
    ref_sub = _passband(sub, 40, 80)
    main_low = next((f for f, v in zip(main.freqs, main.magnitude_db) if f >= 30 and v >= ref_main - 6), None)
    sub_high = next((f for f, v in zip(main.freqs[::-1], sub.magnitude_db[::-1]) if v >= ref_sub - 6), None)
    if main_low is None or sub_high is None:
        return {"range_hz": None, "note": "Measurements don't overlap. Check both sources."}
    lo, hi = sorted([main_low, sub_high])
    return {
        "mains_minus6_hz": round(float(main_low), 1),
        "sub_minus6_hz": round(float(sub_high), 1),
        "range_hz": [round(float(lo), 0), round(float(hi), 0)],
        "suggested_hz": round(float(np.sqrt(lo * hi)), 0),
        "overlap": bool(sub_high >= main_low),
    }


def match_levels(main: Measurement, sub: Measurement, crossover_hz: float) -> dict:
    """Level offset (dB) for the sub so both meet at the same passband level."""
    main_lvl = _passband(main, crossover_hz * 1.5, crossover_hz * 6)
    sub_lvl = _passband(sub, crossover_hz / 2.5, crossover_hz / 1.2)
    return {"sub_gain_db": round(main_lvl - sub_lvl, 1), "main_level_db": round(main_lvl, 1),
            "sub_level_db": round(sub_lvl, 1)}
