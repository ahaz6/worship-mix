"""Module 4 - feedback detector (WORSHIP_MIX.md ch. 9).

Criteria: narrow dominant peak, stable frequency, growing amplitude.
Feed consecutive frames via `process()`; returns alerts.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np


@dataclass
class Candidate:
    freq: float
    levels: list[float] = field(default_factory=list)


class FeedbackDetector:
    def __init__(self, sr: int = 48000, n_fft: int = 8192, prominence_db: float = 15.0,
                 min_frames: int = 6, freq_tol_hz: float = 8.0, min_growth_db: float = 1.0) -> None:
        self.sr, self.n_fft = sr, n_fft
        self.prominence_db = prominence_db
        self.min_frames = min_frames
        self.freq_tol = freq_tol_hz
        self.min_growth = min_growth_db
        self.window = np.hanning(n_fft)
        self.candidates: list[Candidate] = []

    def _peaks(self, frame: np.ndarray) -> list[tuple[float, float]]:
        spec = np.abs(np.fft.rfft(frame[: self.n_fft] * self.window)) + 1e-12
        mag = 20 * np.log10(spec)
        # local average over ~1/3 octave-ish neighbourhood
        k = 40
        kernel = np.ones(2 * k + 1) / (2 * k + 1)
        avg = np.convolve(mag, kernel, mode="same")
        out = []
        for i in np.argsort(mag)[-5:]:  # top 5 bins
            if 2 < i < len(mag) - 2 and mag[i] - avg[i] > self.prominence_db \
                    and mag[i] >= mag[i - 1] and mag[i] >= mag[i + 1]:
                a, b, c = mag[i - 1], mag[i], mag[i + 1]
                p = 0.5 * (a - c) / (a - 2 * b + c + 1e-12)  # quadratic interpolation
                out.append(((i + p) * self.sr / self.n_fft, float(b)))
        return out

    def process(self, frame: np.ndarray) -> list[dict]:
        peaks = self._peaks(frame)
        next_cands: list[Candidate] = []
        for f, lvl in peaks:
            match = next((c for c in self.candidates if abs(c.freq - f) < self.freq_tol), None)
            c = match or Candidate(freq=f)
            c.freq = 0.7 * c.freq + 0.3 * f
            c.levels.append(lvl)
            next_cands.append(c)
        self.candidates = next_cands

        alerts = []
        for c in self.candidates:
            if len(c.levels) >= self.min_frames:
                growth = c.levels[-1] - c.levels[-self.min_frames]
                if growth >= self.min_growth:
                    alerts.append({
                        "type": "feedback", "freq_hz": round(c.freq, 1), "growth_db": round(growth, 1),
                        "suggested_notch": {"freq": round(c.freq, 1), "gain_db": -4.0, "q": 10.0},
                    })
        return alerts
