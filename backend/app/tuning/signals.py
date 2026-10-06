"""Room Tuning - test signals (WORSHIP_MIX.md ch. 11a).

Test signal layout (mono, 48 kHz):
    [0.5 s silence][chirp 60 ms][1.0 s gap][log sine sweep][1.5 s tail]

The chirp is a band-limited down-chirp (8 kHz -> 500 Hz) timing reference: any full-range
speaker can play it. Because chirp and sweep have a fixed offset inside the
file, the measured impulse response keeps the true acoustic arrival time
relative to the chirp - which is what makes time alignment possible when the
chirp runs on a different speaker than the sweep (e.g. sweep on the sub).
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

FS = 48000


@dataclass(frozen=True)
class SignalLayout:
    fs: int = FS
    lead_s: float = 0.5
    chirp_s: float = 0.06
    gap_s: float = 1.0
    sweep_s: float = 5.0
    tail_s: float = 1.5
    f1: float = 20.0
    f2: float = 20000.0
    level_dbfs: float = -12.0

    @property
    def chirp_start(self) -> int:
        return int(self.lead_s * self.fs)

    @property
    def sweep_start(self) -> int:
        return int((self.lead_s + self.chirp_s + self.gap_s) * self.fs)

    @property
    def sweep_len(self) -> int:
        return int(self.sweep_s * self.fs)


LAYOUT = SignalLayout()


def log_sweep(layout: SignalLayout = LAYOUT) -> np.ndarray:
    """Exponential (Farina) sine sweep with 10 ms raised-cosine fades."""
    n = layout.sweep_len
    t = np.arange(n) / layout.fs
    k = np.log(layout.f2 / layout.f1)
    x = np.sin(2 * np.pi * layout.f1 * layout.sweep_s / k * (np.exp(t / layout.sweep_s * k) - 1))
    return _fade(x, layout.fs) * 10 ** (layout.level_dbfs / 20)


def chirp(layout: SignalLayout = LAYOUT, f0: float = 8000.0, f1: float = 500.0) -> np.ndarray:
    """Down-chirp: nearly orthogonal to the up-sweep, so detection never locks onto the sweep."""
    n = int(layout.chirp_s * layout.fs)
    t = np.arange(n) / layout.fs
    x = np.sin(2 * np.pi * (f0 * t + (f1 - f0) / (2 * layout.chirp_s) * t**2))
    return x * np.hanning(n) * 10 ** (layout.level_dbfs / 20)


def test_signal(layout: SignalLayout = LAYOUT) -> np.ndarray:
    total = layout.sweep_start + layout.sweep_len + int(layout.tail_s * layout.fs)
    out = np.zeros(total)
    c = chirp(layout)
    out[layout.chirp_start : layout.chirp_start + len(c)] = c
    out[layout.sweep_start : layout.sweep_start + layout.sweep_len] = log_sweep(layout)
    return out


def pink_noise(seconds: float = 60.0, fs: int = FS, level_dbfs: float = -18.0, seed: int = 1) -> np.ndarray:
    """Pink noise (-3 dB/octave), 20 Hz - 20 kHz, RMS normalised to level_dbfs."""
    n = int(seconds * fs)
    rng = np.random.default_rng(seed)
    spec = np.fft.rfft(rng.standard_normal(n))
    f = np.fft.rfftfreq(n, 1 / fs)
    shape = np.zeros_like(f)
    band = (f >= 20) & (f <= 20000)
    shape[band] = 1 / np.sqrt(f[band])
    x = np.fft.irfft(spec * shape, n)
    x /= np.sqrt(np.mean(x**2)) + 1e-20
    return _fade(x * 10 ** (level_dbfs / 20), fs)


def _fade(x: np.ndarray, fs: int, ms: float = 10.0) -> np.ndarray:
    n = int(fs * ms / 1000)
    w = 0.5 - 0.5 * np.cos(np.linspace(0, np.pi, n))
    x = x.copy()
    x[:n] *= w
    x[-n:] *= w[::-1]
    return x
