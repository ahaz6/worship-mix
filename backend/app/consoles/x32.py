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


# --- Generic OSC client with query support --------------------------------------
# X32 answers a message that has *no arguments* with the current value.
import socket

from pythonosc.osc_message import OscMessage
from pythonosc.osc_message_builder import OscMessageBuilder


class OscClient:
    def __init__(self, host: str, port: int, timeout: float = 0.3) -> None:
        self.addr = (host, port)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.settimeout(timeout)

    @staticmethod
    def _build(address: str, value=None) -> bytes:
        b = OscMessageBuilder(address=address)
        if value is not None:
            b.add_arg(value)
        return b.build().dgram

    def send(self, address: str, value) -> None:
        self.sock.sendto(self._build(address, value), self.addr)

    def query(self, address: str):
        self.sock.sendto(self._build(address), self.addr)
        try:
            while True:
                data, _ = self.sock.recvfrom(4096)
                msg = OscMessage(data)
                if msg.address == address:
                    return msg.params[0] if msg.params else None
        except TimeoutError:
            return None

    def close(self) -> None:
        self.sock.close()


# --- Semantic change -> X32 OSC --------------------------------------------------
# TODO(verify): enum orders and value laws against Patrick-Gilles Maillot's
# "Unofficial X32/M32 OSC Remote Protocol" before writing to a real console.
X32_RATIOS = [1.1, 1.3, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0, 7.0, 10.0, 20.0, 100.0]


def _lin(v: float, lo: float, hi: float) -> float:
    return float((max(lo, min(hi, v)) - lo) / (hi - lo))


def _log(v: float, lo: float, hi: float) -> float:
    return float(math.log(max(lo, min(hi, v)) / lo) / math.log(hi / lo))


def x32_messages(change) -> list[tuple[str, float | int | str]]:
    """Translate one Change into X32 OSC (address, value) pairs."""
    v = change.value
    if change.target == "main":
        base = "/main/st"
    else:
        base = f"/ch/{change.channel:02d}"
    p = change.param
    if p == "trim" and change.channel:
        return [(f"{base}/preamp/trim", _lin(v["db"], -18, 18))]
    if p == "hpf" and change.channel:
        return [(f"{base}/preamp/hpf", _log(v["freq"], 20, 400)), (f"{base}/preamp/hpon", 1 if v.get("on", True) else 0)]
    if p == "peq":
        return [(f"{base}/eq/on", 1),
                (f"{base}/eq/{v['band']}/type", X32_EQ_TYPE.get(v["type"], 2)),
                (f"{base}/eq/{v['band']}/f", x32_freq(v["freq"])),
                (f"{base}/eq/{v['band']}/g", x32_gain(v["gain_db"])),
                (f"{base}/eq/{v['band']}/q", x32_q(v["q"]))]
    if p == "gate" and change.channel:
        return [(f"{base}/gate/on", 1), (f"{base}/gate/mode", 3),
                (f"{base}/gate/thr", _lin(v["threshold_db"], -80, 0)),
                (f"{base}/gate/range", _lin(v["range_db"], 3, 60)),
                (f"{base}/gate/attack", _lin(v["attack_ms"], 0, 120)),
                (f"{base}/gate/hold", _log(max(v["hold_ms"], 0.02), 0.02, 2000)),
                (f"{base}/gate/release", _log(v["release_ms"], 5, 4000))]
    if p == "comp":
        ratio_idx = min(range(len(X32_RATIOS)), key=lambda i: abs(X32_RATIOS[i] - v["ratio"]))
        msgs = [(f"{base}/dyn/on", 1), (f"{base}/dyn/mode", 0),
                (f"{base}/dyn/thr", _lin(v["threshold_db"], -60, 0)),
                (f"{base}/dyn/ratio", ratio_idx),
                (f"{base}/dyn/attack", _lin(v["attack_ms"], 0, 120)),
                (f"{base}/dyn/release", _log(v["release_ms"], 5, 4000)),
                (f"{base}/dyn/mgain", _lin(v.get("makeup_db", 0), 0, 24))]
        if v.get("key_channel"):
            msgs.append((f"{base}/dyn/keysrc", int(v["key_channel"])))  # 1..32 = input channel (verify)
        return msgs
    if p == "name" and change.channel:
        return [(f"{base}/config/name", str(v["name"])[:12])]
    return []  # e.g. GEQ lives in an FX slot on X32 -> manual
