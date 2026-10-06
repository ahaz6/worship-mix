"""Module 1 - core audio metrics (see WORSHIP_MIX.md ch. 6 & 12)."""
from __future__ import annotations

import numpy as np
import pyloudnorm as pyln
from scipy.signal import resample_poly

# Frequency bands from WORSHIP_MIX.md 12.2
BANDS: dict[str, tuple[float, float]] = {
    "sub": (20, 60),
    "bass": (60, 250),
    "low_mids": (250, 500),
    "mids": (500, 2000),
    "high_mids": (2000, 5000),
    "presence": (5000, 8000),
    "air": (8000, 20000),
}


def _to_2d(audio: np.ndarray) -> np.ndarray:
    """Return shape (samples, channels)."""
    return audio[:, None] if audio.ndim == 1 else audio


def db(x: float) -> float:
    return float(20 * np.log10(max(x, 1e-12)))


def integrated_lufs(audio: np.ndarray, sr: int) -> float:
    meter = pyln.Meter(sr)  # ITU-R BS.1770-4
    return float(meter.integrated_loudness(_to_2d(audio)))


def sample_peak_db(audio: np.ndarray) -> float:
    return db(float(np.max(np.abs(audio))))


def true_peak_db(audio: np.ndarray, oversample: int = 4) -> float:
    """Approximate true peak via 4x oversampling (BS.1770 Annex 2 style)."""
    up = resample_poly(_to_2d(audio), oversample, 1, axis=0)
    return db(float(np.max(np.abs(up))))


def band_energies_db(audio: np.ndarray, sr: int) -> dict[str, float]:
    """Relative energy per band in dB (normalised to total energy)."""
    mono = _to_2d(audio).mean(axis=1)
    spec = np.abs(np.fft.rfft(mono * np.hanning(len(mono)))) ** 2
    freqs = np.fft.rfftfreq(len(mono), 1 / sr)
    total = spec.sum() + 1e-20
    out = {}
    for name, (lo, hi) in BANDS.items():
        e = spec[(freqs >= lo) & (freqs < hi)].sum()
        out[name] = float(10 * np.log10(e / total + 1e-20))
    return out


def stereo_correlation(audio: np.ndarray) -> float | None:
    a = _to_2d(audio)
    if a.shape[1] < 2:
        return None
    l, r = a[:, 0], a[:, 1]
    if np.std(l) == 0 or np.std(r) == 0:
        return None
    return float(np.corrcoef(l, r)[0, 1])


def clipped_samples(audio: np.ndarray, threshold: float = 0.999) -> int:
    return int(np.sum(np.abs(audio) >= threshold))


def analyze(audio: np.ndarray, sr: int) -> dict:
    lufs = integrated_lufs(audio, sr)
    tp = true_peak_db(audio)
    return {
        "integrated_lufs": lufs,
        "sample_peak_db": sample_peak_db(audio),
        "true_peak_db": tp,
        "plr_db": tp - lufs,
        "bands_db": band_energies_db(audio, sr),
        "stereo_correlation": stereo_correlation(audio),
        "clipped_samples": clipped_samples(audio),
    }
