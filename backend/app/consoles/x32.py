"""Behringer X32 / Midas M32 - OSC over UDP port 10023.

Reference: unofficial X32 OSC protocol documentation (Patrick-Gilles Maillot).
TODO(verify): normalised float mappings for EQ freq/gain/q.
"""
from __future__ import annotations

import math

from pythonosc.udp_client import SimpleUDPClient

from app.consoles.base import ConsoleAdapter

X32_PORT = 10023


def db_to_x32_fader(db: float) -> float:
    """X32 fader law (4 linear segments) -> 0.0..1.0."""
    if db <= -90:
        return 0.0
    if db < -60:
        return (db + 90) / 480
    if db < -30:
        return (db + 70) / 160
    if db < -10:
        return (db + 50) / 80
    return min(1.0, (db + 30) / 40)


def hz_to_x32_hpf(freq: float) -> float:
    """HPF 20..400 Hz, logarithmic -> 0..1."""
    freq = max(20.0, min(400.0, freq))
    return math.log(freq / 20) / math.log(400 / 20)


class X32Adapter(ConsoleAdapter):
    name = "behringer-x32"

    def __init__(self, host: str, port: int = X32_PORT) -> None:
        super().__init__(host, port)
        self.client = SimpleUDPClient(host, port)

    def capabilities(self) -> set[str]:
        return {"fader", "mute", "hpf", "peq", "name"}

    async def set_fader(self, ch: int, db: float, bus: str = "LR") -> None:
        db = min(db, 0.0)
        self._guard(f"ch{ch}.fader", None, db)
        self.client.send_message(f"/ch/{ch:02d}/mix/fader", db_to_x32_fader(db))

    async def set_mute(self, ch: int, muted: bool) -> None:
        self._guard(f"ch{ch}.mute", None, muted)
        self.client.send_message(f"/ch/{ch:02d}/mix/on", 0 if muted else 1)

    async def set_hpf(self, ch: int, freq_hz: float, on: bool = True) -> None:
        self._guard(f"ch{ch}.hpf", None, freq_hz if on else None)
        self.client.send_message(f"/ch/{ch:02d}/preamp/hpf", hz_to_x32_hpf(freq_hz))
        self.client.send_message(f"/ch/{ch:02d}/preamp/hpon", 1 if on else 0)

    async def set_channel_name(self, ch: int, name: str) -> None:
        self._guard(f"ch{ch}.name", None, name)
        self.client.send_message(f"/ch/{ch:02d}/config/name", name[:12])


# --- Main bus PEQ (Room Tuning) ---------------------------------------------
# X32 main stereo EQ: /main/st/eq/{1..6}/{type,f,g,q}. Values are normalised floats.
# TODO(verify): type enum order and Q mapping against the X32 OSC documentation.
X32_EQ_TYPE = {"low_shelf": 1, "peak": 2, "high_shelf": 4}  # LCut=0, LShv=1, PEQ=2, VEQ=3, HShv=4, HCut=5


def x32_freq(f: float) -> float:
    """20 Hz..20 kHz logarithmic -> 0..1."""
    return float(math.log(max(20.0, min(20000.0, f)) / 20) / math.log(1000))


def x32_gain(db: float) -> float:
    """-15..+15 dB -> 0..1."""
    return float((max(-15.0, min(15.0, db)) + 15) / 30)


def x32_q(q: float) -> float:
    """Q 10..0.3 logarithmic -> 0..1 (high Q at 0)."""
    q = max(0.3, min(10.0, q))
    return float(1 - math.log(q / 0.3) / math.log(10 / 0.3))


def x32_main_peq_messages(filters) -> list[dict]:
    msgs = [{"address": "/main/st/eq/on", "value": 1}]
    for i, f in enumerate(filters, start=1):
        base = f"/main/st/eq/{i}"
        msgs += [{"address": f"{base}/type", "value": X32_EQ_TYPE[f.type]},
                 {"address": f"{base}/f", "value": round(x32_freq(f.freq), 4)},
                 {"address": f"{base}/g", "value": round(x32_gain(f.gain_db), 4)},
                 {"address": f"{base}/q", "value": round(x32_q(f.q), 4)}]
    return msgs
