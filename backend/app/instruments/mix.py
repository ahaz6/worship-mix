"""Instrument Tuning - whole-mix analysis.

- Balance: loudness of each channel relative to the lead vocal vs. profile targets
  -> fader suggestions (the congregation must hear melody and words first).
- Masking: per octave band, how often two instruments are loud at the same time
  with similar energy -> EQ carving or sidechain/ducking.
- Sidechain rules for worship:
    kick -> bass            (low-end clarity, punch)
    lead vocal -> keys/pad/guitars (dynamic EQ dip at 2-3 kHz while singing)
    speech -> pad/tracks/keys (pastor talks over the pad: duck the music)
- Master bus: spectrum vs. target curve, loudness, bus compressor, limiter.
"""
from __future__ import annotations

import numpy as np
import pyloudnorm as pyln

from app.consoles.changes import Change
from app.instruments.channel import envelope_db
from app.instruments.profiles import Profile
from app.tuning.targets import target_on_grid

OCT = [63, 125, 250, 500, 1000, 2000, 4000, 8000]
PRIORITY = {"lead_vocal": 0, "speech": 0, "kick": 1, "bass": 1, "snare": 2, "bgv": 2, "keys": 3, "acoustic": 3,
            "egtr": 3, "melody": 3, "pad": 5, "tracks": 4, "tom": 4, "overheads": 4, "hihat": 5, "cajon": 3,
            "perc": 5, "samples": 4}


def loudness(x: np.ndarray, fs: int) -> float:
    try:
        v = pyln.Meter(fs).integrated_loudness(np.asarray(x, float))
    except ValueError:
        v = float("-inf")
    if not np.isfinite(v):
        v = 10 * np.log10(np.mean(np.asarray(x, float) ** 2) + 1e-12) - 0.691
    return float(v)


def band_frames(x: np.ndarray, fs: int, n: int = 4096) -> np.ndarray:
    """Power per octave band per frame -> shape (frames, bands)."""
    hop = n // 2
    if len(x) < n:
        x = np.pad(x, (0, n - len(x)))
    frames = np.lib.stride_tricks.sliding_window_view(x, n)[::hop] * np.hanning(n)
    spec = np.abs(np.fft.rfft(frames, axis=1)) ** 2
    f = np.fft.rfftfreq(n, 1 / fs)
    out = np.zeros((spec.shape[0], len(OCT)))
    for j, fc in enumerate(OCT):
        sel = (f >= fc / np.sqrt(2)) & (f < fc * np.sqrt(2))
        out[:, j] = spec[:, sel].sum(axis=1)
    return out


def masking(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Per band 0..1: share of frames where both are active with energies within 6 dB."""
    la, lb = 10 * np.log10(a + 1e-20), 10 * np.log10(b + 1e-20)
    act_a = la > la.max(axis=0) - 25
    act_b = lb > lb.max(axis=0) - 25
    close = np.abs(la - lb) < 6
    return np.mean(act_a & act_b & close, axis=0)


def _main_bands(b: np.ndarray, within_db: float = 15.0) -> np.ndarray:
    """Bands that carry the instrument's main energy (within 15 dB of its loudest band)."""
    lv = 10 * np.log10(b.mean(axis=0) + 1e-20)
    return lv >= lv.max() - within_db


def analyze_mix(channels: list[dict], audio: dict[int, np.ndarray], fs: int, profiles: dict[int, Profile],
                target: str = "worship_warm") -> dict:
    """channels: results from analyze_channel (index-aligned with audio/profiles keys)."""
    idx = list(audio)
    lufs = {i: loudness(audio[i], fs) for i in idx}
    ref_i = next((i for i in idx if profiles[i].role in ("lead_vocal", "speech")), max(idx, key=lambda i: lufs[i]))
    ref = lufs[ref_i]

    # USB/direct outs are pre-fader: suggest START fader positions (lead = 0 dB)
    balance, fader = [], {}
    for i in idx:
        p = profiles[i]
        rel = lufs[i] - ref
        fdb = 0.0 if i == ref_i else float(np.clip(p.balance_lu - rel, -40, 10))
        fader[i] = fdb
        balance.append({"channel": i, "name": channels[idx.index(i)]["name"], "relative_lu": round(rel, 1),
                        "target_lu": p.balance_lu, "fader_db": round(fdb, 1)})

    # everything below works on the balanced mix
    audio = {i: audio[i] * 10 ** (fader[i] / 20) for i in idx}
    bands = {i: band_frames(audio[i], fs) for i in idx}
    main_bands = {i: _main_bands(bands[i]) for i in idx}
    conflicts = []
    for a_pos, i in enumerate(idx):
        for j in idx[a_pos + 1:]:
            m = masking(bands[i], bands[j])
            for k, fc in enumerate(OCT):
                if m[k] >= 0.35 and main_bands[i][k] and main_bands[j][k]:
                    pi, pj = PRIORITY.get(profiles[i].role, 4), PRIORITY.get(profiles[j].role, 4)
                    keep, give = (i, j) if pi <= pj else (j, i)
                    conflicts.append({"band_hz": fc, "score": round(float(m[k]), 2), "keep": keep, "give": give,
                                      "keep_name": channels[idx.index(keep)]["name"],
                                      "give_name": channels[idx.index(give)]["name"],
                                      "action": f"Cut {channels[idx.index(give)]['name']} by 2-3 dB around {fc} Hz "
                                                f"(Q 1.4) to make room for {channels[idx.index(keep)]['name']}."})
    # one entry per instrument pair (its strongest band), most important first
    best: dict[tuple[int, int], dict] = {}
    for c in sorted(conflicts, key=lambda c: -c["score"]):
        best.setdefault((c["keep"], c["give"]), c)
    conflicts = sorted(best.values(), key=lambda c: (-c["score"], PRIORITY.get(profiles[c["keep"]].role, 4)))

    roles = {profiles[i].role: i for i in idx}
    sidechains = []

    def name(i: int) -> str:
        return channels[idx.index(i)]["name"]

    def cc(i: int) -> int | None:
        return channels[idx.index(i)].get("console_channel")

    if "kick" in roles and "bass" in roles:
        k, b = roles["kick"], roles["bass"]
        if masking(bands[k], bands[b])[:2].max() >= 0.2:
            sidechains.append({"key": name(k), "target": name(b), "key_channel": cc(k), "target_channel": cc(b),
                               "settings": {"ratio": 4.0, "attack_ms": 1, "release_ms": 80, "gr_db": 3},
                               "why": "Kick and bass hit the same low frequencies. Ducking the bass for a moment on each "
                                      "kick keeps the low end punchy instead of boomy."})
    lead = roles.get("lead_vocal")
    if lead is not None:
        for i in idx:
            if profiles[i].role in ("keys", "pad", "acoustic", "egtr") and masking(bands[lead], bands[i])[4:7].max() >= 0.2:
                sidechains.append({"key": name(lead), "target": name(i), "key_channel": cc(lead), "target_channel": cc(i),
                                   "settings": {"type": "dynamic_eq", "freq": 2500, "q": 1.4, "max_cut_db": 3,
                                                "attack_ms": 10, "release_ms": 150},
                                   "why": "While the lead sings, a small dip at 2.5 kHz on this instrument keeps the words "
                                          "clear. No dynamic EQ? Use a compressor keyed from the vocal, 2:1, 2 dB."})
    sp = roles.get("speech")
    if sp is not None:
        for i in idx:
            if profiles[i].role in ("pad", "tracks", "keys"):
                sidechains.append({"key": name(sp), "target": name(i), "key_channel": cc(sp), "target_channel": cc(i),
                                   "settings": {"ratio": 4.0, "attack_ms": 20, "release_ms": 600, "gr_db": 8},
                                   "why": "When the pastor speaks over music, the music steps back automatically."})

    # master bus
    mix = np.sum([audio[i] for i in idx], axis=0)
    mix_lufs = loudness(mix, fs)
    peak = float(20 * np.log10(np.max(np.abs(mix)) + 1e-12))
    mb = band_frames(mix, fs).mean(axis=0)
    mdb = 10 * np.log10(mb + 1e-20)
    tgt = target_on_grid(target, np.array(OCT, float))
    # octave-band power is already integrated per octave (pink = flat), so compare shapes directly
    dev = (mdb - mdb.mean()) - (tgt - tgt.mean())
    master_eq = [{"freq": fc, "gain_db": round(float(np.clip(-d, -2, 2)), 1)} for fc, d in zip(OCT, dev) if abs(d) > 3]
    master = {
        "lufs": round(mix_lufs, 1), "peak_dbfs": round(peak, 1), "plr_db": round(peak - mix_lufs, 1),
        "eq": master_eq,
        "bus_comp": {"ratio": 2.0, "attack_ms": 30, "release_ms": 150, "gr_db": 2,
                     "threshold_db": round(float(np.percentile(envelope_db(mix, fs), 95)) - 4, 0),
                     "why": "Glues the band together; 1-2 dB of gain reduction is enough."},
        "limiter": {"ceiling_dbtp": -1.0, "why": "Protects the PA and the livestream from peaks."},
        "stream": {"target_lufs": -16, "why": "Typical livestream loudness; use a separate stream bus with its own mix."},
    }
    return {"reference": name(ref_i), "balance": balance, "conflicts": conflicts[:12], "sidechains": sidechains,
            "master": master}


def sidechain_changes(sidechains: list[dict]) -> list[Change]:
    """Compressor-based sidechains as console changes (dynamic EQ stays manual)."""
    out = []
    for s in sidechains:
        st = s["settings"]
        if st.get("type") == "dynamic_eq" or not s.get("target_channel"):
            continue
        out.append(Change(f"ch:{s['target_channel']}", "comp",
                          {"threshold_db": -30, "ratio": st["ratio"], "attack_ms": st["attack_ms"],
                           "release_ms": st["release_ms"], "key": s["key"], "key_channel": s.get("key_channel")},
                          note=f"Sidechain: {s['key']} ducks {s['target']}"))
    return out
