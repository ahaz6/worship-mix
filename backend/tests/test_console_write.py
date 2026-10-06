"""Safe console writing against a fake X32 that speaks OSC over UDP."""
import socket
import threading
import time

import pytest
from fastapi.testclient import TestClient
from pythonosc.osc_message import OscMessage
from pythonosc.osc_message_builder import OscMessageBuilder

from app.consoles.changes import Change, describe
from app.consoles.session import ConsoleSession, WriteDisabled
from app.consoles.x32 import x32_messages
from app.main import app


class FakeX32(threading.Thread):
    def __init__(self):
        super().__init__(daemon=True)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(("127.0.0.1", 0))
        self.port = self.sock.getsockname()[1]
        self.state = {"/info": "V2.07 fake X32", "/main/st/eq/1/g": 0.5, "/ch/05/preamp/hpf": 0.0}
        self.writes: list[tuple[str, object]] = []
        self.running = True

    def run(self):
        self.sock.settimeout(0.1)
        while self.running:
            try:
                data, addr = self.sock.recvfrom(4096)
            except TimeoutError:
                continue
            msg = OscMessage(data)
            if msg.params:
                self.state[msg.address] = msg.params[0]
                self.writes.append((msg.address, msg.params[0]))
            elif msg.address in self.state:
                b = OscMessageBuilder(address=msg.address)
                b.add_arg(self.state[msg.address])
                self.sock.sendto(b.build().dgram, addr)


@pytest.fixture
def x32():
    srv = FakeX32()
    srv.start()
    yield srv
    srv.running = False


def _wait(cond, timeout=2.0):
    """UDP is asynchronous: give the fake console a moment to process packets."""
    end = time.time() + timeout
    while time.time() < end and not cond():
        time.sleep(0.01)
    assert cond()


EQ = Change("main", "peq", {"band": 1, "type": "peak", "freq": 63.0, "gain_db": -6.0, "q": 4.0})


def test_translation_ranges():
    msgs = dict(x32_messages(EQ))
    assert msgs["/main/st/eq/1/g"] == pytest.approx(0.3)          # -6 dB on a -15..+15 scale
    assert 0 < msgs["/main/st/eq/1/f"] < 0.3
    gate = dict(x32_messages(Change("ch:9", "gate", {"threshold_db": -40, "range_db": 20, "attack_ms": 0.5,
                                                      "hold_ms": 80, "release_ms": 200})))
    assert gate["/ch/09/gate/thr"] == pytest.approx(0.5)
    assert "Ch 9: gate on" in describe(Change("ch:9", "gate", {"threshold_db": -40, "range_db": 20, "attack_ms": 0.5,
                                                                 "hold_ms": 80, "release_ms": 200}))


def test_read_only_until_allowed(x32):
    s = ConsoleSession("behringer-x32", "127.0.0.1", x32.port)
    assert s.connect()["connected"]
    with pytest.raises(WriteDisabled):
        s.apply([EQ], sleep=False)
    assert x32.writes == []


def test_apply_ramps_and_undo_restores(x32):
    s = ConsoleSession("behringer-x32", "127.0.0.1", x32.port)
    s.connect()
    s.write_enabled = True
    r = s.apply([EQ], sleep=False)
    assert r["applied"] == 5
    _wait(lambda: x32.state["/main/st/eq/1/g"] == pytest.approx(0.3))
    gains = [v for a, v in x32.writes if a == "/main/st/eq/1/g"]
    assert len(gains) == 6 and gains[0] > gains[-1]                  # ramped down in steps, no jump
    assert x32.state["/main/st/eq/1/g"] == pytest.approx(0.3)
    gain_log = next(e for e in s.audit if e["address"] == "/main/st/eq/1/g")
    assert gain_log["old"] == pytest.approx(0.5)
    s.undo(sleep=False)
    _wait(lambda: x32.state["/main/st/eq/1/g"] == pytest.approx(0.5))


def test_sq_returns_manual_steps():
    s = ConsoleSession("allen-heath-sq", "127.0.0.1", 51325)
    r = s.apply([Change("ch:3", "hpf", {"freq": 100})], sleep=False)
    assert r["mode"] == "manual" and r["applied"] == 0
    assert r["steps"] == ["Ch 3: high-pass on at 100 Hz"]


def test_console_api_with_mock():
    c = TestClient(app)
    sid = c.post("/api/consoles/connect", json={"kind": "mock"}).json()["session"]
    body = {"changes": [{"target": "ch:1", "param": "hpf", "value": {"freq": 90}}]}
    assert c.post(f"/api/consoles/{sid}/apply", json=body).status_code == 409   # read-only first
    c.post(f"/api/consoles/{sid}/writes", params={"enabled": True})
    assert c.post(f"/api/consoles/{sid}/apply", json=body).json()["applied"] == 2
    assert len(c.get(f"/api/consoles/{sid}/audit").json()) == 2
    assert c.post(f"/api/consoles/{sid}/undo").json()["restored"] == 0          # mock had no prior value
