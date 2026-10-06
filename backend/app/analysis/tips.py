"""Module 1 - rule engine that turns metrics into tips (problem / action / why).

User-facing strings are English: the Worship Suite UI is English-only (Design-Art.md 12).
"""
from __future__ import annotations

from pydantic import BaseModel


class Tip(BaseModel):
    id: str
    severity: str  # info | warning | critical
    category: str
    targets: list[str] = []
    problem: str
    action: str
    why: str
    params: dict = {}
    confidence: float = 0.8


def generate_tips(m: dict, target_lufs: float = -14.0) -> list[Tip]:
    tips: list[Tip] = []

    if m["true_peak_db"] > -1.0:
        tips.append(Tip(
            id="true_peak_over", severity="critical", category="loudness",
            problem=f"True peak is {m['true_peak_db']:.1f} dBTP.",
            action="Set the limiter ceiling to -1.0 dBTP (true-peak mode).",
            why="Above -1 dBTP, MP3/AAC encoding on streaming services distorts audibly.",
            params={"limiter_ceiling_dbtp": -1.0},
        ))

    diff = m["integrated_lufs"] - target_lufs
    if abs(diff) > 2:
        louder = diff < 0
        tips.append(Tip(
            id="loudness_target", severity="warning", category="loudness",
            problem=f"Loudness is {m['integrated_lufs']:.1f} LUFS, target is {target_lufs} LUFS.",
            action=f"{'Raise' if louder else 'Lower'} the level by about {abs(diff):.1f} dB.",
            why="Platforms normalise to their target: too loud costs dynamics, too quiet sounds weak.",
        ))

    if m["plr_db"] < 7:
        tips.append(Tip(
            id="over_compressed", severity="warning", category="dynamics",
            problem=f"Peak-to-loudness ratio is only {m['plr_db']:.1f} dB.",
            action="Ease off the limiter or bus compressor (less gain reduction).",
            why="Too little dynamics is tiring and flattens the builds in worship songs.",
        ))

    b = m["bands_db"]
    if b["low_mids"] - b["mids"] > 3:
        tips.append(Tip(
            id="muddy_low_mids", severity="warning", category="eq",
            problem="Too much energy between 250 and 500 Hz (mud).",
            action="Wide cut of -2 to -3 dB at 250-350 Hz (Q ~1), mainly on pads, keys and guitars.",
            why="Low mids build up quickly and blur the mix.",
            params={"eq": [{"freq": 300, "gain_db": -2.5, "q": 1.0, "type": "bell"}]},
        ))

    corr = m.get("stereo_correlation")
    if corr is not None and corr < 0:
        tips.append(Tip(
            id="phase_negative", severity="critical", category="phase",
            problem=f"Stereo correlation is negative ({corr:.2f}).",
            action="Check phase: polarity of single tracks and stereo wideners.",
            why="In mono (phones, livestream, some PAs) parts of the mix cancel out.",
        ))

    if m["clipped_samples"] > 0:
        tips.append(Tip(
            id="clipping", severity="critical", category="loudness",
            problem=f"{m['clipped_samples']} clipped samples found.",
            action="Lower the level before bouncing and check gain staging.",
            why="Digital clipping is audible distortion and cannot be undone.",
        ))
    return tips
