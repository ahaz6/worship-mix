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
