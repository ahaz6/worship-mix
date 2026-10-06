"""Room Tuning - measurement: chirp detection, deconvolution, response, SNR.

Pipeline:
  recording -> find chirp (cross-correlation) -> cut sweep region
  -> regularised spectral division  -> impulse response (IR)
  -> window IR -> magnitude / phase / group delay on a log grid
  -> noise floor from the silence before the chirp -> SNR -> blanking mask
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from scipy.signal import fftconvolve

from app.tuning.signals import LAYOUT, SignalLayout, chirp, log_sweep

PRE_S = 0.05      # IR keeps 50 ms before the expected arrival (pre-delay / earlier speakers)
IR_S = 0.5        # analysis window length
GRID_POINTS = 480 # log grid 20 Hz - 20 kHz (~1/48 octave)


class MeasurementError(RuntimeError):
    """User-facing measurement problem (English, Design-Art 12)."""


def freq_grid(n: int = GRID_POINTS) -> np.ndarray:
    return np.geomspace(20, 20000, n)


@dataclass
class Measurement:
    freqs: np.ndarray
    magnitude_db: np.ndarray
    phase_deg: np.ndarray            # wrapped, -180..180
    group_delay_ms: np.ndarray
    snr_db: np.ndarray
    ir: np.ndarray
    fs: int
    arrival_ms: float                # IR peak relative to the chirp timing reference
    meta: dict = field(default_factory=dict)

    def to_dict(self, blank_below_snr: float | None = 10.0) -> dict:
        mask = np.ones_like(self.freqs, dtype=bool) if blank_below_snr is None else self.snr_db >= blank_below_snr

        def arr(a: np.ndarray) -> list:
            return [round(float(v), 3) if m else None for v, m in zip(a, mask)]

        return {
            "freqs": [round(float(f), 2) for f in self.freqs],
            "magnitude_db": arr(self.magnitude_db),
            "phase_deg": arr(self.phase_deg),
            "group_delay_ms": arr(self.group_delay_ms),
            "snr_db": [round(float(v), 1) for v in self.snr_db],
            "arrival_ms": round(self.arrival_ms, 2),
            "meta": self.meta,
        }


def find_chirp(recording: np.ndarray, layout: SignalLayout = LAYOUT, window_s: float = 0.25) -> int:
    """Sample index where the chirp starts in the recording.

    Two stages, robust in reverberant churches:
    1. Coarse: locate the whole test signal via the 5 s sweep (huge processing gain).
    2. Fine: search the chirp only within +/- window_s of where it must be.
       Delays between speakers are far below 250 ms (~85 m), so this window is safe.
    """
    sweep = log_sweep(layout)
    if len(recording) < len(sweep):
        raise MeasurementError("The recording is too short. Record the whole test signal.")
    coarse = np.abs(fftconvolve(recording, sweep[::-1], mode="valid"))
    if coarse.max() / (np.median(coarse) + 1e-12) < 8:
        raise MeasurementError("No test signal heard. Check the speaker routing and turn the system up.")
    expected = int(np.argmax(coarse)) - (layout.sweep_start - layout.chirp_start)

    ref = chirp(layout)
    w = int(window_s * layout.fs)
    lo = max(0, expected - w)
    hi = min(len(recording), expected + w + len(ref))
    env = np.abs(fftconvolve(recording[lo:hi], ref[::-1], mode="valid"))
    if env.size == 0 or env.max() / (np.median(env) + 1e-12) < 4:
        raise MeasurementError("The timing chirp was not heard. Route the chirp to a full-range speaker.")
    # first strong hit = direct sound (later hits are reflections)
    peak = float(env.max())
    first = int(np.argmax(env >= 0.5 * peak))
    k = int(0.005 * layout.fs)
    return lo + first + int(np.argmax(env[first : first + k]))


def deconvolve(response: np.ndarray, layout: SignalLayout = LAYOUT) -> np.ndarray:
    """Impulse response via regularised division Y·X* / (|X|² + eps) (band-limited)."""
    x = log_sweep(layout)
    n = 1 << int(np.ceil(np.log2(len(response) + len(x))))
    X = np.fft.rfft(x, n)
    Y = np.fft.rfft(response, n)
    f = np.fft.rfftfreq(n, 1 / layout.fs)
    power = np.abs(X) ** 2
    eps = np.where((f >= layout.f1 * 1.05) & (f <= layout.f2 * 0.95), 1e-6, 1e2) * power.max()
    return np.fft.irfft(Y * np.conj(X) / (power + eps), n)


def fractional_octave_smooth(freqs: np.ndarray, values_power: np.ndarray, grid: np.ndarray, fraction: float) -> np.ndarray:
    """Average power values in a 1/fraction-octave window around each grid point."""
    out = np.empty_like(grid)
    half = 2 ** (1 / (2 * fraction))
    for i, fc in enumerate(grid):
        sel = (freqs >= fc / half) & (freqs <= fc * half)
        out[i] = values_power[sel].mean() if sel.any() else np.interp(fc, freqs, values_power)
    return out


def response_from_ir(ir: np.ndarray, fs: int, smoothing: float = 48.0) -> tuple[np.ndarray, ...]:
    """IR (time zero at index 0) -> grid freqs, magnitude dB, wrapped phase, group delay ms."""
    n = len(ir)
    H = np.fft.rfft(ir)
    f = np.fft.rfftfreq(n, 1 / fs)
    grid = freq_grid()
    mag = 10 * np.log10(fractional_octave_smooth(f, np.abs(H) ** 2, grid, smoothing) + 1e-20)
    # complex smoothing for phase (vector average within the band)
    re = fractional_octave_smooth(f, H.real, grid, smoothing)
    im = fractional_octave_smooth(f, H.imag, grid, smoothing)
    phase = np.degrees(np.angle(re + 1j * im))
    unwrapped = np.unwrap(np.angle(H))
    gd = -np.gradient(unwrapped, 2 * np.pi * f) * 1000
    gd_grid = np.interp(grid, f, _moving_median(gd, 31))
    return grid, mag, phase, gd_grid


def _moving_median(x: np.ndarray, k: int) -> np.ndarray:
    from scipy.ndimage import median_filter
    return median_filter(x, size=k, mode="nearest")


def measure(recording: np.ndarray, fs: int, layout: SignalLayout = LAYOUT, remove_delay: bool = True,
            mic_cal: tuple[np.ndarray, np.ndarray] | None = None) -> Measurement:
    if fs != layout.fs:
        from scipy.signal import resample_poly
        g = np.gcd(fs, layout.fs)
        recording = resample_poly(recording, layout.fs // g, fs // g)
        fs = layout.fs
    rec = recording if recording.ndim == 1 else recording.mean(axis=1)
    if np.max(np.abs(rec)) >= 0.999:
        raise MeasurementError("The microphone clipped. Lower the system volume or move the mic further away.")

    c0 = find_chirp(rec, layout)
    sweep_at = c0 + (layout.sweep_start - layout.chirp_start)
    pre = int(PRE_S * fs)
    seg_len = layout.sweep_len + int(layout.tail_s * fs)
    start = sweep_at - pre
    if start < 0 or start + seg_len > len(rec):
        raise MeasurementError("The recording ended too early. Keep listening until the sweep has finished.")
    full_ir = deconvolve(rec[start : start + seg_len], layout)

    # noise reference: silence before the chirp, tiled to the same length
    noise_len = max(int(0.3 * fs), min(c0, int(layout.lead_s * fs)) - int(0.05 * fs))
    noise = rec[max(0, c0 - noise_len - int(0.05 * fs)) : c0 - int(0.05 * fs)]
    if len(noise) < int(0.1 * fs):
        noise = np.zeros(int(0.1 * fs)) + 1e-9
    noise_ir = deconvolve(np.resize(noise, seg_len), layout)

    win = int(IR_S * fs)
    peak = int(np.argmax(np.abs(full_ir[: pre + int(0.3 * fs)])))
    arrival_ms = (peak - pre) / fs * 1000
    # remove_delay: start 2 ms before the peak (needed for averaging positions).
    # otherwise IR index 0 == arrival time of the chirp reference (needed for alignment).
    t0 = max(0, peak - int(0.002 * fs)) if remove_delay else pre
    ir = full_ir[t0 : t0 + win] * _half_window(win, fs)
    nir = noise_ir[t0 : t0 + win] * _half_window(win, fs)

    grid, mag, phase, gd = response_from_ir(ir, fs)
    _, nmag, _, _ = response_from_ir(nir, fs, smoothing=6)
    if mic_cal is not None:
        mag = mag - np.interp(np.log(grid), np.log(mic_cal[0]), mic_cal[1])
    snr = mag - nmag
    # outside the sweep's clean band the deconvolution is meaningless -> always blanked
    snr[(grid < layout.f1 * 1.1) | (grid > layout.f2 * 0.9)] = -99.0
    if np.median(snr[(grid > 100) & (grid < 10000)]) < 10:
        raise MeasurementError("Low measurement coherence. Reduce background noise or raise the volume.")
    return Measurement(grid, mag, phase, gd, snr, ir, fs, arrival_ms,
                       meta={"remove_delay": remove_delay, "chirp_at_s": round(c0 / fs, 3)})


def _half_window(n: int, fs: int, fade_ms: float = 50.0) -> np.ndarray:
    w = np.ones(n)
    k = int(fs * fade_ms / 1000)
    w[-k:] = 0.5 + 0.5 * np.cos(np.linspace(0, np.pi, k))
    return w


def average(ms: list[Measurement]) -> Measurement:
    """dB average for magnitude, vector average for phase, arithmetic for group delay."""
    if not ms:
        raise MeasurementError("Nothing to average.")
    mag = np.mean([m.magnitude_db for m in ms], axis=0)
    vec = np.mean([10 ** (m.magnitude_db / 20) * np.exp(1j * np.radians(m.phase_deg)) for m in ms], axis=0)
    gd = np.mean([m.group_delay_ms for m in ms], axis=0)
    snr = np.min([m.snr_db for m in ms], axis=0)
    ir = np.mean([m.ir for m in ms], axis=0)
    return Measurement(ms[0].freqs, mag, np.degrees(np.angle(vec)), gd, snr, ir, ms[0].fs,
                       float(np.mean([m.arrival_ms for m in ms])), meta={"averaged": len(ms)})
