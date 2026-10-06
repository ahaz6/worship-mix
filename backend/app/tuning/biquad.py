"""RBJ Audio-EQ-Cookbook biquads (peaking, low shelf, high shelf)."""
from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np
from scipy.signal import freqz


@dataclass
class Filter:
    type: str        # "peak" | "low_shelf" | "high_shelf"
    freq: float
    gain_db: float
    q: float

    def to_dict(self) -> dict:
        return {k: (round(v, 2) if isinstance(v, float) else v) for k, v in asdict(self).items()}


def coefficients(f: Filter, fs: int) -> tuple[np.ndarray, np.ndarray]:
    a_ = 10 ** (f.gain_db / 40)
    w0 = 2 * np.pi * f.freq / fs
    cw, sw = np.cos(w0), np.sin(w0)
    alpha = sw / (2 * f.q)
    if f.type == "peak":
        b = [1 + alpha * a_, -2 * cw, 1 - alpha * a_]
        a = [1 + alpha / a_, -2 * cw, 1 - alpha / a_]
    elif f.type in ("low_shelf", "high_shelf"):
        s = 1 if f.type == "low_shelf" else -1
        sq = 2 * np.sqrt(a_) * alpha
        b = [a_ * ((a_ + 1) - s * (a_ - 1) * cw + sq), s * 2 * a_ * ((a_ - 1) - s * (a_ + 1) * cw),
             a_ * ((a_ + 1) - s * (a_ - 1) * cw - sq)]
        a = [(a_ + 1) + s * (a_ - 1) * cw + sq, -s * 2 * ((a_ - 1) + s * (a_ + 1) * cw),
             (a_ + 1) + s * (a_ - 1) * cw - sq]
    else:
        raise ValueError(f"unknown filter type {f.type}")
    b, a = np.array(b), np.array(a)
    return b / a[0], a / a[0]


def response_db(filters: list[Filter], grid: np.ndarray, fs: int = 48000) -> np.ndarray:
    total = np.zeros_like(grid)
    for f in filters:
        b, a = coefficients(f, fs)
        _, h = freqz(b, a, worN=grid, fs=fs)
        total += 20 * np.log10(np.abs(h) + 1e-20)
    return total
