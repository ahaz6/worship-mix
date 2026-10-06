"""Instrument Tuning - live multichannel input (USB from the console) and sessions.

Typical setup: console USB (SQ: 32x32, X32: X-USB 32x32) -> laptop running the
Worship Mix backend natively (not in Docker - audio devices). Channels are
captured into ring buffers; every few seconds the last N seconds are analyzed.
Works the same with uploaded multitrack files (no hardware needed).
"""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field

import numpy as np

from app.instruments.channel import analyze_channel
from app.instruments.mix import analyze_mix, sidechain_changes
from app.instruments.profiles import get


@dataclass
class ChannelMap:
    input_index: int            # 0-based input on the audio device / track index
    profile: str
    name: str
    console_channel: int | None = None


def run_analysis(tracks: dict[int, np.ndarray], fs: int, mapping: list[ChannelMap],
                 room_rt60: float | None = None, bpm: float | None = None) -> dict:
    channels, audio, profiles = [], {}, {}
    for m in mapping:
        x = tracks.get(m.input_index)
        if x is None or not np.any(x):
            continue
        p = get(m.profile)
        key = m.input_index + 1
        channels.append(analyze_channel(x, fs, p, m.console_channel, m.name, room_rt60, bpm))
        audio[key] = x
        profiles[key] = p
    if not channels:
        return {"channels": [], "mix": None, "updated": time.time()}
    mix = analyze_mix(channels, audio, fs, profiles)
    mix["sidechain_changes"] = [c.to_dict() for c in sidechain_changes(mix["sidechains"])]
    return {"channels": channels, "mix": mix, "updated": time.time()}


@dataclass
class LiveSession:
    device: int | str | None
    mapping: list[ChannelMap]
    fs: int = 48000
    window_s: float = 8.0
    every_s: float = 3.0
    room_rt60: float | None = None
    bpm: float | None = None
    latest: dict = field(default_factory=dict)
    levels: dict = field(default_factory=dict)
    error: str | None = None
    _buf: np.ndarray | None = None
    _pos: int = 0
    _stream: object | None = None
    _thread: threading.Thread | None = None
    _stop: threading.Event = field(default_factory=threading.Event)
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def feed(self, block: np.ndarray) -> None:
        """block: (frames, channels). Public so tests/simulations can push audio."""
        n_ch = block.shape[1]
        size = int(self.window_s * self.fs)
        with self._lock:
            if self._buf is None or self._buf.shape[1] != n_ch:
                self._buf = np.zeros((size, n_ch), dtype=np.float32)
                self._pos = 0
            for row in np.array_split(block, max(1, len(block) // size + 1)):
                k = len(row)
                end = self._pos + k
                if end <= size:
                    self._buf[self._pos:end] = row
                else:
                    first = size - self._pos
                    self._buf[self._pos:] = row[:first]
                    self._buf[: k - first] = row[first:]
                self._pos = end % size
            peaks = np.max(np.abs(block), axis=0)
        self.levels = {m.input_index: round(float(20 * np.log10(peaks[m.input_index] + 1e-9)), 1)
                       for m in self.mapping if m.input_index < n_ch}

    def snapshot(self) -> dict[int, np.ndarray]:
        with self._lock:
            if self._buf is None:
                return {}
            ordered = np.roll(self._buf, -self._pos, axis=0)
        return {i: ordered[:, i].astype(float) for i in range(ordered.shape[1])}

    def analyze_now(self) -> dict:
        self.latest = run_analysis(self.snapshot(), self.fs, self.mapping, self.room_rt60, self.bpm)
        return self.latest

    # -- hardware ---------------------------------------------------------------
    def start(self) -> None:
        try:
            import sounddevice as sd
        except (ImportError, OSError) as e:  # PortAudio missing (e.g. in Docker)
            raise RuntimeError("No audio input available here. Run the backend on the FOH laptop "
                               "(pip install -e '.[live]') or upload multitrack files instead.") from e
        n_ch = max(m.input_index for m in self.mapping) + 1
        self._stream = sd.InputStream(device=self.device, channels=n_ch, samplerate=self.fs,
                                      callback=lambda data, frames, t, status: self.feed(data.copy()))
        self._stream.start()  # type: ignore[attr-defined]
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def _loop(self) -> None:
        while not self._stop.wait(self.every_s):
            try:
                self.analyze_now()
                self.error = None
            except Exception as e:  # noqa: BLE001 - must keep running during a service
                self.error = str(e)

    def stop(self) -> None:
        self._stop.set()
        if self._stream is not None:
            self._stream.stop()  # type: ignore[attr-defined]
            self._stream.close()  # type: ignore[attr-defined]


def list_devices() -> list[dict]:
    try:
        import sounddevice as sd
        return [{"index": i, "name": d["name"], "inputs": d["max_input_channels"]}
                for i, d in enumerate(sd.query_devices()) if d["max_input_channels"] > 0]
    except Exception:  # noqa: BLE001 - no PortAudio = simply no devices
        return []


LIVE: dict[str, LiveSession] = {}
