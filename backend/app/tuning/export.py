"""Room Tuning - filter export formats.

- miniDSP biquad coefficients (a0 normalised, a1/a2 sign-flipped)
- Equalizer APO / generic text PEQ (also readable by CamillaDSP front ends)
- CamillaDSP YAML snippet
- Impulse response WAV (32-bit float, mono) for convolution engines
- Console plan: GEQ 31 + PEQ steps; X32 main-bus OSC messages
"""
from __future__ import annotations

import io

import numpy as np
import soundfile as sf

from app.tuning.biquad import Filter, coefficients

APO_TYPE = {"peak": "PK", "low_shelf": "LSC", "high_shelf": "HSC"}


def minidsp_biquads(filters: list[Filter], fs: int) -> str:
    lines = []
    for i, f in enumerate(filters, start=1):
        b, a = coefficients(f, fs)
        lines += [f"biquad{i},", f"b0={b[0]:.15f},", f"b1={b[1]:.15f},", f"b2={b[2]:.15f},",
                  f"a1={-a[1]:.15f},", f"a2={-a[2]:.15f},"]
    if lines:
        lines[-1] = lines[-1].rstrip(",")
    return "\n".join(lines) + "\n"


def peq_text(filters: list[Filter], preamp_db: float = 0.0) -> str:
    out = [f"Preamp: {preamp_db:.1f} dB"]
    for i, f in enumerate(filters, start=1):
        out.append(f"Filter {i}: ON {APO_TYPE[f.type]} Fc {f.freq:.0f} Hz Gain {f.gain_db:.1f} dB Q {f.q:.2f}")
    return "\n".join(out) + "\n"


def camilladsp_yaml(filters: list[Filter]) -> str:
    kind = {"peak": "Peaking", "low_shelf": "Lowshelf", "high_shelf": "Highshelf"}
    out = ["filters:"]
    names = []
    for i, f in enumerate(filters, start=1):
        name = f"wm_room_{i}"
        names.append(name)
        out += [f"  {name}:", "    type: Biquad", "    parameters:", f"      type: {kind[f.type]}",
                f"      freq: {f.freq:.1f}", f"      gain: {f.gain_db:.2f}", f"      q: {f.q:.3f}"]
    out += ["pipeline:", "  - type: Filter", "    channels: [0, 1]", "    names:"]
    out += [f"      - {n}" for n in names]
    return "\n".join(out) + "\n"


def impulse_wav(ir: np.ndarray, fs: int) -> bytes:
    buf = io.BytesIO()
    sf.write(buf, np.asarray(ir, dtype=np.float32), fs, format="WAV", subtype="FLOAT")
    return buf.getvalue()


def console_plan(filters: list[Filter], geq: list[dict], console: str, preamp_db: float) -> dict:
    """Human steps for any console + machine messages where the protocol allows it."""
    steps = [
        (f"Insert the correction on the MAIN L/R bus (not on input channels). Lower main level by "
         f"{abs(preamp_db):.1f} dB if boosts were applied.")
    ]
    steps += [f"PEQ band {i}: {f.type.replace('_', ' ')} {f.freq:.0f} Hz, {f.gain_db:+.1f} dB, Q {f.q:.2f}"
              for i, f in enumerate(filters, start=1)]
    geq_steps = [f"GEQ {g['freq']} Hz: {g['gain_db']:+.1f} dB" for g in geq if g["gain_db"] != 0]
    plan = {"console": console, "peq_steps": steps, "geq_steps": geq_steps, "osc": []}
    if console == "behringer-x32":
        from app.consoles.x32 import x32_main_peq_messages
        plan["osc"] = x32_main_peq_messages(filters[:6])
        if len(filters) > 6:
            plan["peq_steps"].append("X32 main EQ has 6 bands: put the remaining filters into the main GEQ.")
    if console == "allen-heath-sq":
        plan["peq_steps"].append("SQ: processing is not exposed over MIDI. Enter these values on the LR PEQ/GEQ "
                                 "by hand (SQ-Rack: via SQ MixPad or SQ4You).")
    return plan


def room_eq_changes(filters: list[Filter], geq: list[dict], main_bands: int = 6) -> list:
    """Room correction as console changes: main PEQ bands first, GEQ for the rest/backup."""
    from app.consoles.changes import Change

    changes = [Change("main", "peq", {"band": i, "type": f.type, "freq": f.freq, "gain_db": f.gain_db, "q": f.q})
               for i, f in enumerate(filters[:main_bands], start=1)]
    if len(filters) > main_bands or any(b["gain_db"] for b in geq):
        changes.append(Change("main", "geq", {"bands": geq},
                              note="Use either the PEQ bands or the GEQ - not both."))
    return changes
