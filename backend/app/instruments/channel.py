"""Instrument Tuning - per-channel analysis and settings recommendation.

Pipeline per channel:
  audio -> envelope (50 ms RMS, 10 ms hop) -> level stats, hits, decay
        -> long-term spectrum (Welch) -> fitted spectral tilt -> band deviations
        -> resonances (only for drums / percussion / speech / acoustic guitar,
           because narrow peaks on tonal instruments are *notes*, not problems)
  -> settings: gain, HPF/LPF, EQ (max 4 bands), gate, compressor, de-esser, FX, pan
  -> console-neutral changes (app.consoles.changes.Change)

Rules are deliberately conservative: cuts preferred, boosts <= 3 dB, every
suggestion carries problem / action / why (English UI copy).
"""
from __future__ import annotations

import numpy as np
from scipy.signal import find_peaks, welch

from app.consoles.changes import Change
from app.instruments.profiles import Profile

TARGET_PEAK_DBFS = -12.0
RESONANCE_GROUPS = {"drums", "percussion"}
RESONANCE_ROLES = {"speech"}          # tonal instruments: narrow peaks are notes, not problems
HARSH_GROUPS = {"vocals", "guitars", "strings", "keys"}


# ------------------------------------------------------------------ features --

def envelope_db(x: np.ndarray, fs: int, win_s: float = 0.05, hop_s: float = 0.01) -> np.ndarray:
    win, hop = int(win_s * fs), int(hop_s * fs)
    if len(x) < win:
        return np.array([-120.0])
    frames = np.lib.stride_tricks.sliding_window_view(x, win)[::hop]
    return 10 * np.log10(np.mean(frames**2, axis=1) + 1e-12)


def _db(v: float) -> float:
    return float(20 * np.log10(max(v, 1e-9)))


def spectrum(x: np.ndarray, fs: int) -> tuple[np.ndarray, np.ndarray]:
    f, p = welch(x, fs, nperseg=min(8192, len(x)), noverlap=None)
    return f[1:], 10 * np.log10(p[1:] + 1e-20)


def smooth_oct(f: np.ndarray, db: np.ndarray, fraction: float) -> np.ndarray:
    half = 2 ** (1 / (2 * fraction))
    p = 10 ** (db / 10)
    cs = np.concatenate([[0], np.cumsum(p)])
    lo = np.searchsorted(f, f / half)
    hi = np.searchsorted(f, f * half, side="right")
    return 10 * np.log10((cs[hi] - cs[lo]) / np.maximum(hi - lo, 1) + 1e-20)


def hits(env: np.ndarray, hop_s: float = 0.01, rise_db: float = 15.0) -> tuple[np.ndarray, float | None]:
    """Transient peaks and median decay time (ms) to -20 dB after each hit."""
    floor = np.percentile(env, 20)
    peaks, _ = find_peaks(env, height=floor + rise_db, distance=int(0.08 / hop_s), prominence=rise_db * 0.6)
    decays = []
    for p in peaks:
        tail = env[p:p + int(1.5 / hop_s)]
        below = np.nonzero(tail <= env[p] - 20)[0]
        if below.size:
            decays.append(below[0] * hop_s * 1000)
    return peaks, (float(np.median(decays)) if decays else None)


def analyze_features(x: np.ndarray, fs: int, profile: Profile) -> dict:
    x = np.asarray(x, dtype=float)
    env = envelope_db(x, fs)
    peak = float(np.max(np.abs(x))) if x.size else 0.0
    noise = float(np.percentile(env, 10))
    loud = float(np.percentile(env, 95))
    active = env > noise + 10
    f, s = spectrum(x, fs)
    sm = smooth_oct(f, s, 3)
    total = np.sum(10 ** (s / 10))
    cum = np.cumsum(10 ** (s / 10)) / (total + 1e-30)
    low_start = float(f[np.searchsorted(cum, 0.005)]) if total > 0 else 20.0

    # spectral tilt over the instrument's useful range
    lo = profile.fundamental[0]
    hi = (profile.presence or (2000, 5000))[1]
    sel = (f >= lo) & (f <= hi)
    coef = np.polyfit(np.log2(f[sel]), sm[sel], 1) if sel.sum() > 4 else np.array([0.0, float(np.mean(sm))])
    fit = np.polyval(coef, np.log2(f))

    def dev(band: tuple[float, float] | None) -> float | None:
        if band is None:
            return None
        b = (f >= band[0]) & (f <= band[1])
        return float(np.mean(sm[b] - fit[b])) if b.any() else None

    feats = {
        "peak_dbfs": round(_db(peak), 1),
        "loud_dbfs": round(loud, 1),
        "noise_dbfs": round(noise, 1),
        "crest_db": round(_db(peak) - loud, 1),
        "active_pct": round(float(np.mean(active)) * 100, 0),
        "clipped": int(np.sum(np.abs(x) >= 0.999)),
        "low_content_hz": round(low_start, 0),
        "tilt_db_per_oct": round(float(coef[0]), 1),
        "dev": {k: (None if v is None else round(v, 1)) for k, v in {
            "mud": dev(profile.mud), "box": dev(profile.box), "presence": dev(profile.presence),
            "air": dev(profile.air), "harsh": dev((2500, 4500)),
            "boom": dev((max(profile.hpf, 30.0), profile.fundamental[0])) if profile.fundamental[0] > 60 else None,
        }.items()},
        "resonances": [],
    }

    if profile.group in RESONANCE_GROUPS or profile.role in RESONANCE_ROLES:
        floor = s.max() - 60
        fine = smooth_oct(f, np.maximum(s, floor), 24)
        broad = smooth_oct(f, np.maximum(s, floor), 1.5)
        height = fine - broad
        # a resonance must be strong (within 20 dB of the loudest part) and outside the
        # instrument's own fundamental (that's the drum's tone; its ring is handled by gate/release)
        ok = ((f >= 80) & (f <= 6000) & (fine > fine.max() - 20)
              & ~((f >= profile.fundamental[0]) & (f <= profile.fundamental[1])))
        idx, props = find_peaks(np.where(ok, height, -99), height=6, distance=8)
        top = sorted(zip(idx, props["peak_heights"]), key=lambda t: -t[1])[:2]
        feats["resonances"] = [{"freq": round(float(f[i]), 0), "prominence_db": round(float(min(h, 24)), 1)}
                               for i, h in top]

    if profile.gate is not None or profile.group == "drums":
        pk, decay = hits(env)
        feats["hits"] = len(pk)
        feats["hit_level_dbfs"] = round(float(np.median(env[pk])), 1) if len(pk) else None
        feats["bleed_dbfs"] = round(float(np.percentile(env, 25)), 1)
        feats["decay_ms"] = None if decay is None else round(decay, 0)

    if profile.deesser:
        b = (f >= profile.deesser[0]) & (f <= profile.deesser[1])
        if b.any():
            feats["sibilance_freq"] = round(float(f[b][np.argmax(sm[b] - fit[b])]), 0)
            feats["sibilance_db"] = round(float(np.max(sm[b] - fit[b])), 1)
    return feats


# ---------------------------------------------------------- recommendations --

def _note(problem: str, action: str, why: str, severity: str = "info") -> dict:
    return {"severity": severity, "problem": problem, "action": action, "why": why}


def recommend(feats: dict, profile: Profile, room_rt60: float | None = None, bpm: float | None = None) -> dict:
    notes: list[dict] = []
    s: dict = {}

    # gain staging
    trim = float(np.clip(TARGET_PEAK_DBFS - feats["peak_dbfs"], -18, 18))
    s["gain"] = {"trim_db": round(trim, 1), "ok": abs(trim) < 3}
    if feats["clipped"]:
        notes.append(_note(f"{feats['clipped']} samples clipped.", "Lower the preamp gain until peaks stay below -6 dBFS.",
                           "Clipping is distortion that no plugin can repair.", "critical"))
    elif not s["gain"]["ok"]:
        notes.append(_note(f"Peaks at {feats['peak_dbfs']:.0f} dBFS.",
                           f"{'Raise' if trim > 0 else 'Lower'} gain by about {abs(trim):.0f} dB (target peaks around -12 dBFS).",
                           "Good gain staging keeps noise low and leaves headroom for loud moments.", "warning"))

    # high-pass / low-pass
    hpf = profile.hpf
    if feats["low_content_hz"] > profile.hpf * 1.3:
        hpf = min(profile.hpf_range[1], feats["low_content_hz"] * 0.8)
    hpf = float(np.clip(hpf, *profile.hpf_range))
    s["hpf"] = {"freq": round(hpf, 0)}
    if profile.lpf:
        s["lpf"] = {"freq": profile.lpf}
    boom = feats["dev"].get("boom")
    if boom is not None and boom > 3:
        notes.append(_note("Low rumble below the instrument's range.", f"High-pass at {hpf:.0f} Hz.",
                           "Rumble and stage noise eat headroom and muddy the PA.", "warning"))

    # EQ (max 4 bands; cuts first)
    eq: list[dict] = []
    d = feats["dev"]
    for r in feats["resonances"]:
        if r["prominence_db"] >= 6 and len(eq) < 2:
            g = -float(np.clip(r["prominence_db"] * 0.6, 2, 6))
            eq.append({"type": "peak", "freq": r["freq"], "gain_db": round(g, 1), "q": 6.0, "why": "resonance / ring"})
            notes.append(_note(f"Ringing resonance at {r['freq']:.0f} Hz.", f"Narrow cut {g:.0f} dB at {r['freq']:.0f} Hz (Q 6).",
                               "Rings and boominess make drums and voices sound boxy and feed back first.", "warning"))
    if profile.mud and d.get("mud") is not None and d["mud"] > 3 and len(eq) < 4:
        fc = float(np.sqrt(profile.mud[0] * profile.mud[1]))
        g = -float(np.clip(d["mud"], 2, 5))
        eq.append({"type": "peak", "freq": round(fc, 0), "gain_db": round(g, 1), "q": 1.2, "why": "mud"})
        notes.append(_note(f"Muddy low mids around {fc:.0f} Hz (+{d['mud']:.0f} dB).", f"Wide cut {g:.0f} dB at {fc:.0f} Hz.",
                           "Low mids from many instruments pile up and cover the vocals.", "warning"))
    if profile.box and d.get("box") is not None and d["box"] > 3 and len(eq) < 4:
        fc = float(np.sqrt(profile.box[0] * profile.box[1]))
        eq.append({"type": "peak", "freq": round(fc, 0), "gain_db": -3.0, "q": 1.5, "why": "boxy/nasal"})
    if profile.group in HARSH_GROUPS and d.get("harsh") is not None and d["harsh"] > 4 and len(eq) < 4:
        eq.append({"type": "peak", "freq": 3200.0, "gain_db": -2.5, "q": 1.4, "why": "harsh"})
        notes.append(_note("Harsh upper mids (2.5-4.5 kHz).", "Cut 2-3 dB around 3.2 kHz.",
                           "This range is tiring at worship volumes.", "info"))
    if (profile.presence and d.get("presence") is not None and d["presence"] < -4 and len(eq) < 4
            and profile.group in ("vocals", "guitars", "strings")):
        fc = float(np.sqrt(profile.presence[0] * profile.presence[1]))
        eq.append({"type": "peak", "freq": round(fc, 0), "gain_db": 2.0, "q": 1.0, "why": "lacks presence"})
        notes.append(_note("Lacks presence.", f"Gentle boost +2 dB at {fc:.0f} Hz.",
                           "Presence makes words and attack understandable.", "info"))
    if (profile.air and d.get("air") is not None and d["air"] < -6 and len(eq) < 4
            and profile.group in ("vocals", "strings") and profile.role != "speech"):
        eq.append({"type": "high_shelf", "freq": 10000.0, "gain_db": 2.0, "q": 0.7, "why": "air"})
    s["eq"] = eq

    # gate
    if profile.gate is not None and feats.get("hit_level_dbfs") is not None:
        hit, bleed = feats["hit_level_dbfs"], feats["bleed_dbfs"]
        if hit - bleed < 10:
            s["gate"] = None
            notes.append(_note("Too much bleed for a clean gate.", "Leave the gate off or move the mic closer to the drum.",
                               "A gate with too little difference between hit and bleed chatters.", "info"))
        else:
            rel = float(np.clip((feats.get("decay_ms") or profile.gate.release_ms), 60, 800))
            s["gate"] = {"threshold_db": round(bleed + 0.4 * (hit - bleed), 0), "range_db": profile.gate.range_db,
                         "attack_ms": profile.gate.attack_ms, "hold_ms": profile.gate.hold_ms, "release_ms": round(rel, 0)}
    else:
        s["gate"] = None

    # compressor: threshold for the target gain reduction on loud passages
    if profile.comp is not None:
        c = profile.comp
        thr = feats["loud_dbfs"] - c.target_gr_db * c.ratio / (c.ratio - 1)
        rel = c.release_ms
        if profile.group == "drums" and feats.get("decay_ms"):
            rel = float(np.clip(feats["decay_ms"] * 0.8, 50, 300))
        attack = c.attack_ms if feats["crest_db"] < 18 else max(c.attack_ms, 15)
        s["comp"] = {"threshold_db": round(float(thr), 0), "ratio": c.ratio, "attack_ms": attack,
                     "release_ms": round(rel, 0), "makeup_db": round(c.target_gr_db * 0.5, 1),
                     "target_gr_db": c.target_gr_db}
    else:
        s["comp"] = None

    # de-esser
    if profile.deesser and feats.get("sibilance_db") is not None and feats["sibilance_db"] > 2:
        s["deesser"] = {"freq": feats["sibilance_freq"], "reduction_db": round(min(6.0, feats["sibilance_db"]), 1)}
        notes.append(_note(f"Sharp 'S' sounds around {feats['sibilance_freq'] / 1000:.1f} kHz.",
                           f"De-esser at {feats['sibilance_freq'] / 1000:.1f} kHz, 3-6 dB (or a dynamic EQ band).",
                           "Sibilance gets painful on the PA and on the livestream.", "info"))
    else:
        s["deesser"] = None

    # effects - shorter in reverberant rooms
    reverb = profile.reverb
    if room_rt60 and room_rt60 > 1.6 and reverb != "none":
        reverb = {"long": "medium", "medium": "short", "short": "short"}[reverb]
        notes.append(_note(f"The room already rings ({room_rt60:.1f} s).", "Use a shorter, lower reverb send.",
                           "Room reverb plus effect reverb blurs the words.", "info"))
    fx = {"reverb": reverb, "reverb_time_s": {"none": 0, "short": 1.0, "medium": 1.6, "long": 2.4}[reverb]}
    if profile.delay:
        fx["delay_ms"] = round(60000 / bpm, 0) if bpm else None
        fx["delay_note"] = "quarter note" if bpm else "set the tempo to sync the delay"
    s["fx"] = fx
    s["pan"] = profile.pan
    return {"settings": s, "notes": notes}


def to_changes(settings: dict, console_channel: int | None, name: str | None = None) -> list[Change]:
    if not console_channel:
        return []
    t = f"ch:{console_channel}"
    out: list[Change] = []
    if name:
        out.append(Change(t, "name", {"name": name}))
    g = settings["gain"]
    if not g["ok"]:
        out.append(Change(t, "trim", {"db": g["trim_db"]}, note="Soundcheck only - never during the service."))
    out.append(Change(t, "hpf", {"freq": settings["hpf"]["freq"], "on": True}))
    for i, b in enumerate(settings["eq"][:4], start=1):
        out.append(Change(t, "peq", {"band": i, "type": b["type"], "freq": b["freq"], "gain_db": b["gain_db"], "q": b["q"]}))
    if settings.get("gate"):
        out.append(Change(t, "gate", settings["gate"]))
    if settings.get("comp"):
        out.append(Change(t, "comp", {k: v for k, v in settings["comp"].items() if k != "target_gr_db"}))
    return out


def analyze_channel(x: np.ndarray, fs: int, profile: Profile, console_channel: int | None = None,
                    name: str | None = None, room_rt60: float | None = None, bpm: float | None = None) -> dict:
    feats = analyze_features(x, fs, profile)
    rec = recommend(feats, profile, room_rt60, bpm)
    return {"name": name or profile.label, "profile": profile.key, "label": profile.label, "group": profile.group,
            "console_channel": console_channel, "metrics": feats, **rec,
            "changes": [c.to_dict() for c in to_changes(rec["settings"], console_channel, name)]}
