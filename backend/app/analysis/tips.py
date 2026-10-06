"""Module 1 - rule engine that turns metrics into tips (problem / action / why)."""
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
            problem=f"True Peak liegt bei {m['true_peak_db']:.1f} dBTP.",
            action="Limiter-Ceiling auf -1.0 dBTP setzen (True-Peak-Modus).",
            why="Über -1 dBTP verzerren MP3/AAC-Codecs bei Streaming-Diensten hörbar.",
            params={"limiter_ceiling_dbtp": -1.0},
        ))

    diff = m["integrated_lufs"] - target_lufs
    if abs(diff) > 2:
        louder = diff < 0
        tips.append(Tip(
            id="loudness_target", severity="warning", category="loudness",
            problem=f"Lautheit {m['integrated_lufs']:.1f} LUFS, Ziel {target_lufs} LUFS.",
            action=("Gain/Limiter um ca. " if louder else "Pegel um ca. ")
            + f"{abs(diff):.1f} dB {'anheben' if louder else 'absenken'}.",
            why="Plattformen normalisieren auf ihr Ziel - zu laut kostet Dynamik, zu leise wirkt schwach.",
        ))

    if m["plr_db"] < 7:
        tips.append(Tip(
            id="over_compressed", severity="warning", category="dynamics",
            problem=f"Peak-to-Loudness-Ratio nur {m['plr_db']:.1f} dB.",
            action="Limiter/Bus-Kompressor entschärfen (weniger Gain Reduction).",
            why="Zu wenig Dynamik ermüdet und nimmt Worship-Songs die Build-Momente.",
        ))

    b = m["bands_db"]
    if b["low_mids"] - b["mids"] > 3:
        tips.append(Tip(
            id="muddy_low_mids", severity="warning", category="eq",
            problem="Zu viel Energie zwischen 250 und 500 Hz (Mulm).",
            action="Breiter Cut -2 bis -3 dB bei 250-350 Hz (Q ~1), v. a. Pads/Keys/Gitarren.",
            why="Low-Mids stauen sich schnell auf und machen den Mix undeutlich.",
            params={"eq": [{"freq": 300, "gain_db": -2.5, "q": 1.0, "type": "bell"}]},
        ))

    corr = m.get("stereo_correlation")
    if corr is not None and corr < 0:
        tips.append(Tip(
            id="phase_negative", severity="critical", category="phase",
            problem=f"Stereo-Korrelation negativ ({corr:.2f}).",
            action="Phasenlage prüfen (Polarität einzelner Spuren, Stereo-Widener).",
            why="In Mono (Handy, Livestream, manche PAs) löschen sich Signale aus.",
        ))

    if m["clipped_samples"] > 0:
        tips.append(Tip(
            id="clipping", severity="critical", category="loudness",
            problem=f"{m['clipped_samples']} geclippte Samples gefunden.",
            action="Pegel vor dem Bounce reduzieren bzw. Gain-Staging prüfen.",
            why="Digitales Clipping ist hörbare Verzerrung und nicht rückgängig zu machen.",
        ))
    return tips
