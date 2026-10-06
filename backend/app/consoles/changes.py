"""Console-independent change sets.

The analyzers (Room Tuning, Instrument Tuning) produce *semantic* changes like
"channel 5 HPF 120 Hz" or "main PEQ band 2 ...". Each console translates them:
- OSC consoles (X32/M32, Wing later) -> (address, value) messages that can be written
- consoles without processing control (Allen & Heath SQ) -> clear manual steps
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field


@dataclass
class Change:
    target: str            # "main" or "ch:<n>"
    param: str             # trim | hpf | peq | gate | comp | geq | name
    value: dict = field(default_factory=dict)
    note: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @property
    def channel(self) -> int | None:
        return int(self.target.split(":")[1]) if self.target.startswith("ch:") else None


def describe(c: Change) -> str:
    """Human, console-neutral description (English UI copy)."""
    where = "Main L/R" if c.target == "main" else f"Ch {c.channel}"
    v = c.value
    if c.param == "trim":
        return f"{where}: gain/trim {v['db']:+.1f} dB"
    if c.param == "hpf":
        return f"{where}: high-pass {'on' if v.get('on', True) else 'off'} at {v['freq']:.0f} Hz"
    if c.param == "peq":
        return (f"{where}: EQ band {v['band']} {v['type'].replace('_', ' ')} {v['freq']:.0f} Hz "
                f"{v['gain_db']:+.1f} dB Q {v['q']:.2f}")
    if c.param == "gate":
        return (f"{where}: gate on, threshold {v['threshold_db']:.0f} dB, range {v['range_db']:.0f} dB, "
                f"attack {v['attack_ms']:.1f} ms, hold {v['hold_ms']:.0f} ms, release {v['release_ms']:.0f} ms")
    if c.param == "comp":
        key = f", sidechain from {v['key']}" if v.get("key") else ""
        return (f"{where}: compressor on, threshold {v['threshold_db']:.0f} dB, ratio {v['ratio']}:1, "
                f"attack {v['attack_ms']:.0f} ms, release {v['release_ms']:.0f} ms{key}")
    if c.param == "geq":
        return f"{where}: GEQ " + ", ".join(f"{b['freq']} Hz {b['gain_db']:+.1f}" for b in v["bands"] if b["gain_db"])
    if c.param == "name":
        return f"{where}: name '{v['name']}'"
    return f"{where}: {c.param} {v}"
