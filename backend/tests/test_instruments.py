"""Instrument Tuning tests on the synthetic demo band (planted problems)."""
import io
import json

import numpy as np
import pytest
import soundfile as sf
from fastapi.testclient import TestClient

from app.instruments.channel import analyze_channel
from app.instruments.demo import FS, demo_band
from app.instruments.live import ChannelMap, LiveSession, run_analysis
from app.instruments.profiles import PROFILES, get
from app.main import app


@pytest.fixture(scope="module")
def band():
    return demo_band()


@pytest.fixture(scope="module")
def result(band):
    tracks, maps = {}, []
    for i, (name, (p, x)) in enumerate(band.items()):
        tracks[i] = x
        maps.append(ChannelMap(i, p, name, console_channel=i + 1))
    return run_analysis(tracks, FS, maps, room_rt60=1.8, bpm=120)


def ch(result, name):
    return next(c for c in result["channels"] if c["name"] == name)


def test_profiles_cover_the_worship_band():
    for key in ("keys", "aux_keys", "acoustic_guitar", "electric_guitar", "bass", "kick", "snare", "tom1", "tom2",
                "tom3", "overheads", "violin", "lead_vocal_m", "lead_vocal_f", "bgv", "speech", "percussion",
                "sample_pad", "cajon", "tracks", "pad"):
        assert key in PROFILES


def test_snare_ring_found_and_cut(result):
    eq = ch(result, "Snare")["settings"]["eq"]
    assert any(310 < b["freq"] < 350 and b["gain_db"] <= -3 and b["q"] >= 4 for b in eq)


def test_drum_gate_between_bleed_and_hits(result):
    m = ch(result, "Snare")["metrics"]
    g = ch(result, "Snare")["settings"]["gate"]
    assert m["bleed_dbfs"] < g["threshold_db"] < m["hit_level_dbfs"]


def test_kick_keeps_its_click(result):
    assert all(not (2000 < b["freq"] < 5000 and b["gain_db"] < 0) for b in ch(result, "Kick")["settings"]["eq"])


def test_mud_cut_on_keys_and_pad(result):
    for name in ("Keys", "Pad"):
        assert any(200 <= b["freq"] <= 500 and b["gain_db"] < 0 for b in ch(result, name)["settings"]["eq"])


def test_vocal_deesser_and_compressor(result):
    s = ch(result, "Lead vocal")["settings"]
    assert s["deesser"] and 6000 <= s["deesser"]["freq"] <= 8500
    assert s["comp"]["ratio"] == 3.0 and s["comp"]["threshold_db"] < ch(result, "Lead vocal")["metrics"]["loud_dbfs"]


def test_gain_staging_and_hpf(result):
    ag = ch(result, "Acoustic")["settings"]
    assert ag["gain"]["trim_db"] > 5                      # planted: too quiet
    assert 70 <= ch(result, "Lead vocal")["settings"]["hpf"]["freq"] <= 130


def test_reverb_shorter_in_reverberant_room(result):
    assert ch(result, "Lead vocal")["settings"]["fx"]["reverb"] == "short"   # medium -> short at RT60 1.8 s
    assert ch(result, "Lead vocal")["settings"]["fx"]["delay_ms"] == 500     # quarter note at 120 BPM


def test_mix_balance_sidechain_master(result):
    mix = result["mix"]
    assert mix["reference"] == "Lead vocal"
    fad = {b["name"]: b["fader_db"] for b in mix["balance"]}
    assert fad["Lead vocal"] == 0 and fad["Pad"] < fad["Keys"]               # pad sits lower than keys
    assert any(s["key"] == "Kick" and s["target"] == "Bass" for s in mix["sidechains"])
    assert mix["master"]["limiter"]["ceiling_dbtp"] == -1.0
    assert any(c["param"] == "comp" and c["value"]["key_channel"] == 1 for c in mix["sidechain_changes"])


def test_console_changes_per_channel(result):
    changes = ch(result, "Snare")["changes"]
    params = {c["param"] for c in changes}
    assert {"name", "hpf", "peq", "gate", "comp"} <= params
    assert all(c["target"] == "ch:2" for c in changes)


def test_speech_ducks_pad():
    rng = np.random.default_rng(0)
    t = np.arange(FS * 4) / FS
    speech = np.sin(2 * np.pi * 140 * t) * (np.sin(2 * np.pi * 3 * t) > 0) * 0.2 + rng.standard_normal(len(t)) * 0.01
    pad = sum(np.sin(2 * np.pi * f * t) * 0.05 for f in (220, 330, 440))
    r = run_analysis({0: speech, 1: pad}, FS, [ChannelMap(0, "speech", "Pastor", 10), ChannelMap(1, "pad", "Pad", 11)])
    sc = r["mix"]["sidechains"]
    assert sc and sc[0]["key"] == "Pastor" and sc[0]["settings"]["gr_db"] >= 6


def test_live_ring_buffer(band):
    names = list(band)
    sess = LiveSession(None, [ChannelMap(i, band[n][0], n, i + 1) for i, n in enumerate(names)], window_s=4.0)
    block = np.stack([band[n][1] for n in names], axis=1).astype(np.float32)
    for k in range(0, len(block), 4800):          # 100 ms blocks like a sound card
        sess.feed(block[k:k + 4800])
    snap = sess.snapshot()
    assert len(snap[0]) == 4 * FS
    assert np.allclose(snap[0], block[-4 * FS:, 0], atol=1e-6)   # last 4 s, in order
    assert len(sess.analyze_now()["channels"]) == len(names)
    assert set(sess.levels) == set(range(len(names))) and all(v < 0 for v in sess.levels.values())


def test_api_demo_and_upload(band):
    c = TestClient(app)
    assert len(c.get("/api/instruments/profiles").json()) == len(PROFILES)
    demo = c.post("/api/instruments/demo").json()
    assert demo["demo"] and len(demo["channels"]) == 8 and demo["mix"]["balance"]
    kick, vox = band["Kick"][1], band["Lead vocal"][1]
    buf = io.BytesIO()
    sf.write(buf, np.stack([kick, vox], axis=1).astype(np.float32), FS, format="WAV", subtype="FLOAT")
    mapping = [{"input_index": 0, "profile": "kick", "name": "Kick"},
               {"input_index": 1, "profile": "lead_vocal_m", "name": "Vox"}]
    r = c.post("/api/instruments/analyze", files=[("files", ("multi.wav", buf.getvalue(), "audio/wav"))],
               data={"mapping": json.dumps(mapping)}).json()
    assert [x["name"] for x in r["channels"]] == ["Kick", "Vox"]
    assert c.post("/api/instruments/live/start", json={"mapping": mapping}).status_code in (200, 503)
    c.post("/api/instruments/live/stop")


def test_every_profile_runs_without_errors():
    rng = np.random.default_rng(1)
    x = rng.standard_normal(FS * 2) * 0.05
    for p in PROFILES.values():
        r = analyze_channel(x, FS, get(p.key), console_channel=1)
        assert r["settings"]["hpf"]["freq"] >= p.hpf_range[0]
