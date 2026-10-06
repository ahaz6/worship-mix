"""In-memory console for development and tests (mandatory per spec)."""
from __future__ import annotations

import copy

from app.consoles.base import ConsoleAdapter


class MockAdapter(ConsoleAdapter):
    name = "mock"

    def __init__(self, channels: int = 32, **kw) -> None:
        super().__init__(**kw)
        self.state = {ch: {"fader_db": -90.0, "mute": True, "hpf": None, "peq": {}, "name": f"Ch {ch}"}
                      for ch in range(1, channels + 1)}

    def capabilities(self) -> set[str]:
        return {"fader", "mute", "hpf", "peq", "name", "snapshot"}

    async def set_fader(self, ch, db, bus="LR"):
        db = min(db, 0.0)  # safety: never above 0 dB
        self._guard(f"ch{ch}.fader", self.state[ch]["fader_db"], db)
        self.state[ch]["fader_db"] = db

    async def set_mute(self, ch, muted):
        self._guard(f"ch{ch}.mute", self.state[ch]["mute"], muted)
        self.state[ch]["mute"] = muted

    async def set_hpf(self, ch, freq_hz, on=True):
        self._guard(f"ch{ch}.hpf", self.state[ch]["hpf"], freq_hz if on else None)
        self.state[ch]["hpf"] = freq_hz if on else None

    async def set_peq_band(self, ch, band, freq_hz, gain_db, q):
        new = {"f": freq_hz, "g": gain_db, "q": q}
        self._guard(f"ch{ch}.peq{band}", self.state[ch]["peq"].get(band), new)
        self.state[ch]["peq"][band] = new

    async def set_channel_name(self, ch, name):
        self._guard(f"ch{ch}.name", self.state[ch]["name"], name)
        self.state[ch]["name"] = name

    async def snapshot(self):
        return copy.deepcopy(self.state)

    async def restore(self, snap):
        self.state = copy.deepcopy(snap)
