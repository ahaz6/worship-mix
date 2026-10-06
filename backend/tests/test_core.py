import numpy as np
import pytest
from fastapi.testclient import TestClient

from app.analysis.metrics import analyze, true_peak_db
from app.analysis.tips import generate_tips
from app.consoles.base import WriteNotAllowed
from app.consoles.mock import MockAdapter
from app.consoles.sq import db_to_sq_level, nrpn
from app.consoles.x32 import db_to_x32_fader
from app.live.feedback import FeedbackDetector
from app.main import app
from app.mastering.pipeline import normalize_to
from app.presets.loader import build_scene

SR = 48000


def sine(freq=1000, db=-20, secs=5, sr=SR):
    t = np.arange(int(secs * sr)) / sr
    x = 10 ** (db / 20) * np.sin(2 * np.pi * freq * t)
    return np.stack([x, x], axis=1)


def test_metrics_sine():
    m = analyze(sine(), SR)
    assert m["sample_peak_db"] == pytest.approx(-20, abs=0.1)
    assert m["stereo_correlation"] == pytest.approx(1.0, abs=1e-6)
    assert m["clipped_samples"] == 0
    # 1 kHz sine at -20 dBFS peak, stereo: ~ -20 LUFS (K-weighting ~0 dB at 1 kHz)
    assert -24 < m["integrated_lufs"] < -18


def test_tips_flag_clipping_and_true_peak():
    loud = np.clip(sine(db=3), -1, 1)
    ids = {t.id for t in generate_tips(analyze(loud, SR))}
    assert {"clipping", "true_peak_over"} <= ids


def test_normalize_hits_target_and_ceiling():
    y = normalize_to(sine(db=-30), SR, -14.0)
    assert true_peak_db(y) <= -1.0 + 1e-6


async def test_mock_adapter_read_only_by_default():
    c = MockAdapter(channels=4)
    with pytest.raises(WriteNotAllowed):
        await c.set_mute(1, False)
    c.write_enabled = True
    snap = await c.snapshot()
    await c.set_fader(1, 6.0)  # clamps to 0 dB
    assert c.state[1]["fader_db"] == 0.0
    await c.restore(snap)
    assert c.state[1]["fader_db"] == -90.0
    assert len(c.audit_log) == 1


def test_protocol_encoders():
    assert nrpn(1, 0x40, 0x00, 1, 2) == bytes([0xB0, 0x63, 0x40, 0xB0, 0x62, 0, 0xB0, 6, 1, 0xB0, 0x26, 2])
    assert db_to_sq_level(-90) == (0, 0)
    assert db_to_x32_fader(0) == pytest.approx(0.75)
    assert db_to_x32_fader(10) == pytest.approx(1.0)


def test_feedback_detector_fires_on_growing_tone():
    det = FeedbackDetector(sr=SR)
    rng = np.random.default_rng(0)
    alerts = []
    for i in range(12):
        t = np.arange(8192) / SR + i * 8192 / SR
        frame = 0.01 * rng.standard_normal(8192) + (0.01 * 1.3 ** i) * np.sin(2 * np.pi * 2500 * t)
        alerts = det.process(frame)
    assert alerts and abs(alerts[0]["freq_hz"] - 2500) < 10


def test_feedback_detector_ignores_steady_chord():
    det = FeedbackDetector(sr=SR)
    alerts = []
    for i in range(12):
        t = np.arange(8192) / SR + i * 8192 / SR
        frame = sum(0.1 * np.sin(2 * np.pi * f * t) for f in (261.6, 329.6, 392.0))
        alerts = det.process(frame)
    assert alerts == []


def test_scene_builder():
    scene = build_scene([{"name": "Lead Vocal Agi", "instrument": "lead_vocal_m"}])
    assert scene[0]["hpf"] == 90 and scene[0]["channel"] == 1


def test_api():
    c = TestClient(app)
    assert c.get("/api/health").json()["status"] == "ok"
    assert "spotify" in c.get("/api/mastering/targets").json()
    names = {t["name"] for t in c.get("/api/consoles/types").json()}
    assert {"mock", "allen-heath-sq", "behringer-x32"} <= names
