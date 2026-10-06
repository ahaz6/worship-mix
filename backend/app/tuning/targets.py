"""Room Tuning - target curves ("house curves").

Curves are defined as (frequency Hz, gain dB) points and interpolated on a log
frequency axis. File format (import/export, also used for mic calibration):
one "frequency gain" pair per line, separated by space, tab or comma; lines
that don't start with a number are ignored; frequencies must ascend.

The built-in curves are Worship Mix's own starting points - not copies of any
published research curve. Tolerance band is +/- 3 dB.
"""
from __future__ import annotations

import re

import numpy as np

TOLERANCE_DB = 3.0

BUILTIN: dict[str, dict] = {
    "flat": {
        "label": "Flat",
        "use": "Reference and studio monitors.",
        "points": [(20, 0), (20000, 0)],
    },
    "gentle_tilt": {
        "label": "Gentle tilt",
        "use": "Hi-fi or playback in small rooms: about -1 dB per octave.",
        "points": [(20, 5), (40, 4), (80, 3), (160, 2), (320, 1), (640, 0), (1280, -1), (2560, -2),
                   (5120, -3), (10240, -4), (20000, -5)],
    },
    "worship_warm": {
        "label": "Worship warm",
        "use": "Main PA for contemporary worship: full low end, smooth highs.",
        "points": [(20, 4), (40, 6), (63, 6), (100, 5), (160, 3), (250, 1.5), (500, 0), (1000, 0),
                   (2000, -0.5), (4000, -1.5), (8000, -3), (12000, -4.5), (20000, -7)],
    },
    "live_band": {
        "label": "Live band",
        "use": "Energetic sets with kick and bass driven by subs.",
        "points": [(20, 4), (35, 8), (50, 9), (80, 8), (125, 5), (200, 2), (400, 0), (1000, 0),
                   (3000, -1), (6000, -2.5), (10000, -4), (20000, -7)],
    },
    "speech": {
        "label": "Speech clarity",
        "use": "Sermons, announcements, prayer: less low end, clear presence.",
        "points": [(20, -12), (60, -8), (100, -3), (160, 0), (500, 0), (1000, 0), (2500, 1),
                   (4000, 1), (8000, -2), (12000, -5), (20000, -9)],
    },
}


def parse_curve(text: str) -> tuple[np.ndarray, np.ndarray]:
    pts = []
    for line in text.splitlines():
        line = line.strip()
        if not line or not re.match(r"^[+-]?\d", line):
            continue
        parts = [p for p in re.split(r"[\s,;]+", line) if p]
        if len(parts) >= 2:
            pts.append((float(parts[0]), float(parts[1])))
    if len(pts) < 2:
        raise ValueError("A curve file needs at least two 'frequency gain' lines.")
    f, g = np.array(pts).T
    if np.any(np.diff(f) <= 0):
        raise ValueError("Frequencies in a curve file must ascend.")
    return f, g


def format_curve(freqs, gains) -> str:
    return "\n".join(f"{f:.2f} {g:.2f}" for f, g in zip(freqs, gains)) + "\n"


def interpolate(freqs, gains, grid: np.ndarray) -> np.ndarray:
    """Log-frequency interpolation; flat extension outside the defined range."""
    return np.interp(np.log(grid), np.log(np.asarray(freqs, float)), np.asarray(gains, float))


def target_on_grid(name: str, grid: np.ndarray) -> np.ndarray:
    f, g = zip(*BUILTIN[name]["points"])
    return interpolate(f, g, grid)


def fit_offset(measured_db: np.ndarray, target_db: np.ndarray, grid: np.ndarray,
               fmin: float = 200.0, fmax: float = 2000.0) -> float:
    """Automatic target fit: level offset so the target sits on the measurement mid band."""
    sel = (grid >= fmin) & (grid <= fmax) & np.isfinite(measured_db)
    return float(np.mean(measured_db[sel] - target_db[sel]))
