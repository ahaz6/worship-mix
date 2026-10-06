"""Synthetic worship band for demos and tests (no copyrighted audio).

8 s at 120 BPM with deliberately planted problems the analyzer must find:
- snare ring at 330 Hz, tom ring at 220 Hz, kick/bass low-end overlap
- muddy pad and keys (extra 250-400 Hz), sibilant lead vocal (6-8 kHz bursts)
- bleed on the drum mics, a quiet acoustic guitar with body boom
"""
from __future__ import annotations

import numpy as np
from scipy.signal import butter, sosfilt

FS = 48000
BPM = 120.0


def _t(sec: float) -> np.ndarray:
    return np.arange(int(sec * FS)) / FS


def _bp(x, lo, hi, order=2):
    return sosfilt(butter(order, [lo, hi], "band", fs=FS, output="sos"), x)


def _decay(n, tau):
    return np.exp(-np.arange(n) / FS / tau)


def _place(out, sig, t0):
    i = int(t0 * FS)
    seg = sig[: max(0, min(len(sig), len(out) - i))]
    out[i : i + len(seg)] += seg


def kick_hit(rng):
    n = int(0.5 * FS)
    t = np.arange(n) / FS
    f = 50 + 70 * np.exp(-t / 0.03)
    body = np.sin(2 * np.pi * np.cumsum(f) / FS) * _decay(n, 0.12)
    click = _bp(rng.standard_normal(n), 2500, 5000) * _decay(n, 0.004) * 0.4
    return 0.8 * body + click


def snare_hit(rng):
    n = int(0.6 * FS)
    t = np.arange(n) / FS
    noise = _bp(rng.standard_normal(n), 1500, 8000) * _decay(n, 0.06) * 0.35
    body = np.sin(2 * np.pi * 200 * t) * _decay(n, 0.05) * 0.5
    ring = np.sin(2 * np.pi * 330 * t) * _decay(n, 0.35) * 0.30          # planted ring
    return noise + body + ring


def tom_hit(freq, rng):
    n = int(0.9 * FS)
    t = np.arange(n) / FS
    stick = _bp(rng.standard_normal(n), 2000, 6000) * _decay(n, 0.005) * 0.2
    return np.sin(2 * np.pi * freq * t) * _decay(n, 0.3) * 0.7 + stick


def demo_band(seconds: float = 8.0, seed: int = 3) -> dict[str, tuple[str, np.ndarray]]:
    rng = np.random.default_rng(seed)
    n = int(seconds * FS)
    beat = 60 / BPM
    kick, snare, tom1 = np.zeros(n), np.zeros(n), np.zeros(n)
    for b in range(int(seconds / beat)):
        _place(kick, kick_hit(rng), b * beat)
        if b % 2 == 1:
            _place(snare, snare_hit(rng), b * beat)
    for t0 in (seconds - 2 * beat, seconds - 1.5 * beat):
        _place(tom1, tom_hit(220, rng), t0)                                  # fill at the end

    t = _t(seconds)
    roots = [55.0, 41.2, 49.0, 36.7]                                         # A, E, G, D
    bar = 4 * beat
    root = np.array([roots[int(x / bar) % 4] for x in t])
    phase = np.cumsum(root) / FS
    bass = 0.35 * (2 * (phase % 1) - 1)
    bass = sosfilt(butter(2, 700, "low", fs=FS, output="sos"), bass)
    bass *= 0.6 + 0.4 * np.abs(np.sin(np.pi * t / beat))                     # plucked feel

    # lead vocal: sung vowel 110-165 Hz with vibrato + formants + sibilant bursts
    f0 = np.where((t % (2 * bar)) < bar, 147.0, 165.0) * (1 + 0.01 * np.sin(2 * np.pi * 5.5 * t))
    ph = 2 * np.pi * np.cumsum(f0) / FS
    voice = sum(np.sin(k * ph) / k for k in range(1, 30))
    voice = _bp(voice, 300, 900) * 0.9 + _bp(voice, 2200, 3500) * 0.5 + _bp(voice, 100, 300) * 0.4
    voice *= (np.sin(np.pi * (t % beat) / beat) ** 0.3)
    sib = np.zeros(n)
    for s0 in np.arange(0.4, seconds, 1.3):
        _place(sib, _bp(rng.standard_normal(int(0.09 * FS)), 6000, 8500, 4) * 1.6, s0)
    vocal = 0.25 * voice / (np.max(np.abs(voice)) + 1e-9) + 0.25 * sib

    chord = [220.0, 277.2, 329.6, 440.0]
    keys = sum(np.sin(2 * np.pi * f * t) * 0.08 for f in chord)
    keys += _bp(rng.standard_normal(n), 250, 400) * 0.25                     # planted mud
    keys *= 0.7 + 0.3 * np.abs(np.sin(np.pi * t / beat))
    pad = sum(np.sin(2 * np.pi * f * t + i) * 0.05 for i, f in enumerate([110, 165, 220, 330, 440]))
    pad += _bp(rng.standard_normal(n), 220, 420) * 0.3                       # planted mud

    ag = np.zeros(n)
    for b in range(int(seconds / beat * 2)):
        for i, f in enumerate([110.0, 146.8, 196.0, 246.9]):
            m = int(0.6 * FS)
            tt = np.arange(m) / FS
            _place(ag, np.sin(2 * np.pi * f * tt) * _decay(m, 0.25) * 0.05 * (1 + (i == 0)), b * beat / 2 + i * 0.01)
    ag += _bp(rng.standard_normal(n), 90, 130) * 0.05                        # body boom
    ag *= 0.5                                                                # too quiet on purpose

    noise = lambda: rng.standard_normal(n) * 10 ** (-70 / 20)
    return {
        "Kick": ("kick", kick * 0.9 + snare * 0.05 + noise()),
        "Snare": ("snare", snare * 0.8 + kick * 0.06 + noise()),
        "Tom 1": ("tom1", tom1 * 0.8 + snare * 0.03 + kick * 0.03 + noise()),
        "Bass": ("bass", bass + noise()),
        "Lead vocal": ("lead_vocal_m", vocal + noise()),
        "Keys": ("keys", keys + noise()),
        "Pad": ("pad", pad + noise()),
        "Acoustic": ("acoustic_guitar", ag + noise()),
    }
