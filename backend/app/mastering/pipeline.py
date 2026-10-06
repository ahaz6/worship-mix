"""Module 2 - reference mastering pipeline (WORSHIP_MIX.md ch. 7).

Requires extras: pip install -e ".[mastering]"
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pyloudnorm as pyln
import soundfile as sf

from app.analysis.metrics import true_peak_db

LOUDNESS_TARGETS = {
    "spotify": -14.0,
    "apple_music": -16.0,
    "youtube": -14.0,
    "livestream_ebu": -23.0,
    "worship_loud": -10.0,
    "service_playback": -18.0,
}


def normalize_to(audio: np.ndarray, sr: int, target_lufs: float, ceiling_dbtp: float = -1.0) -> np.ndarray:
    """Gain to target LUFS, then safety limiter to the true-peak ceiling."""
    meter = pyln.Meter(sr)
    lufs = meter.integrated_loudness(audio)
    out = audio * 10 ** ((target_lufs - lufs) / 20)
    try:
        from pedalboard import Limiter, Pedalboard
        board = Pedalboard([Limiter(threshold_db=ceiling_dbtp - 0.3, release_ms=100)])
        out = board(out.T.astype(np.float32), sr).T
    except ImportError:
        out = np.clip(out, -1.0, 1.0)
    # final guard on true peak
    tp = true_peak_db(out)
    if tp > ceiling_dbtp:
        out *= 10 ** ((ceiling_dbtp - tp) / 20)
    return out


def master(track: Path, reference: Path | None, out_dir: Path, targets: list[str]) -> dict[str, str]:
    out_dir.mkdir(parents=True, exist_ok=True)
    src = track
    if reference is not None:
        import matchering as mg  # optional dependency
        matched = out_dir / "matched.wav"
        mg.process(target=str(track), reference=str(reference), results=[mg.pcm24(str(matched))])
        src = matched
    audio, sr = sf.read(src, always_2d=True)
    results = {}
    for t in targets:
        y = normalize_to(audio, sr, LOUDNESS_TARGETS[t])
        p = out_dir / f"{track.stem}_{t}.wav"
        sf.write(p, y, sr, subtype="PCM_24")
        results[t] = str(p)
    return results
