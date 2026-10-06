"""Allen & Heath SQ series - MIDI (NRPN) over TCP.

Source: "SQ MIDI Protocol Issue 5", Allen & Heath
https://www.allen-heath.com/content/uploads/2023/11/SQ-MIDI-Protocol-Issue5.pdf
TODO(verify): all parameter addresses and the fader value table against the PDF
before using on a real console.
Note: the protocol mainly covers mutes, levels/sends, pan, scene recall and soft keys -
channel processing (EQ/HPF/comp/gain) is NOT exposed -> Soundcheck shows manual steps.
"""
from __future__ import annotations

import asyncio

from app.consoles.base import ConsoleAdapter

SQ_TCP_PORT = 51325


def nrpn(midi_ch: int, msb: int, lsb: int, vc: int, vf: int) -> bytes:
    """Build one NRPN message sequence (midi_ch 1-16)."""
    s = 0xB0 | ((midi_ch - 1) & 0x0F)
    return bytes([s, 0x63, msb & 0x7F, s, 0x62, lsb & 0x7F, s, 0x06, vc & 0x7F, s, 0x26, vf & 0x7F])


def db_to_sq_level(db: float) -> tuple[int, int]:
    """Map dB to a 14-bit value (coarse, fine).

    TODO(verify): the real SQ curve is non-linear and listed as a table in the PDF.
    This linear approximation over -90..+10 dB is a placeholder for development only.
    """
    db = max(-90.0, min(10.0, db))
    v = round((db + 90.0) / 100.0 * 16383)
    return v >> 7, v & 0x7F


class SQAdapter(ConsoleAdapter):
    name = "allen-heath-sq"

    def __init__(self, host: str, port: int = SQ_TCP_PORT, midi_channel: int = 1) -> None:
        super().__init__(host, port)
        self.midi_channel = midi_channel
        self._writer: asyncio.StreamWriter | None = None

    def capabilities(self) -> set[str]:
        return {"fader", "mute", "scene_recall"}

    async def connect(self) -> None:
        _, self._writer = await asyncio.open_connection(self.host, self.port)

    async def disconnect(self) -> None:
        if self._writer:
            self._writer.close()
            await self._writer.wait_closed()

    async def _send(self, data: bytes) -> None:
        assert self._writer, "not connected"
        self._writer.write(data)
        await self._writer.drain()

    async def set_mute(self, ch: int, muted: bool) -> None:
        self._guard(f"ip{ch}.mute", None, muted)
        # Input mute: MSB 0x00, LSB = ch-1  (TODO(verify))
        await self._send(nrpn(self.midi_channel, 0x00, ch - 1, 0x00, 0x01 if muted else 0x00))

    async def set_fader(self, ch: int, db: float, bus: str = "LR") -> None:
        db = min(db, 0.0)
        self._guard(f"ip{ch}.{bus}.level", None, db)
        # Input -> LR level: MSB 0x40, LSB = ch-1  (TODO(verify))
        vc, vf = db_to_sq_level(db)
        await self._send(nrpn(self.midi_channel, 0x40, ch - 1, vc, vf))

    async def recall_scene(self, scene: int) -> None:
        """Scene recall via Bank Select + Program Change (TODO(verify))."""
        self._guard("scene", None, scene)
        s = (self.midi_channel - 1) & 0x0F
        bank, prog = divmod(scene - 1, 128)
        await self._send(bytes([0xB0 | s, 0x00, bank, 0xC0 | s, prog]))
