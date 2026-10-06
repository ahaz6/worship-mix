"""Room Tuning tests with a simulated room (no real audio in the repo)."""
import io

import numpy as np
import pytest
import soundfile as sf
from fastapi.testclient import TestClient
from scipy.signal import fftconvolve, lfilter

from app.main import app
from app.tuning.acoustics import analyze_room, schroeder_frequency
from app.tuning.alignment import align
from app.tuning.biquad import Filter, coefficients, response_db
from app.tuning.eq import EqSettings, fit_peq, geq31, min_phase_fir
from app.tuning.export import minidsp_biquads, peq_text
from app.tuning.measure import MeasurementError, average, find_chirp, measure
from app.tuning.signals import FS, LAYOUT, chirp, log_sweep
from app.tuning.signals import test_signal as make_test_signal
from app.tuning.targets import fit_offset, parse_curve, target_on_grid

RNG = np.random.default_rng(7)


def room_ir(delay_ms=5.0, rt60=1.0, mode=(60.0, 8.0, 5.0), seed=0, reverb=0.08):
    rng = np.random.default_rng(seed)
    n = int(FS * 1.2)
    ir = np.zeros(n)
    d = int(delay_ms * FS / 1000)
    ir[d] = 1.0
    t = np.arange(1, n - d) / FS
    ir[d + 1:] += reverb * rng.standard_normal(n - d - 1) * np.exp(-6.91 * t / rt60)
    b, a = coefficients(Filter("peak", *mode), FS)
    return lfilter(b, a, ir)


def record(ir, lead_s=0.6, level=0.1, noise=1e-4, chirp_ir=None):
    """Simulate playback + mic. chirp_ir: play the chirp on another speaker (timing reference)."""
    x = make_test_signal()
    if chirp_ir is None:
        y = fftconvolve(x, ir)[: len(x) + FS]
    else:
        c = np.zeros_like(x)
        c[LAYOUT.chirp_start : LAYOUT.chirp_start + len(chirp())] = chirp()
        s_ = np.zeros_like(x)
        s_[LAYOUT.sweep_start : LAYOUT.sweep_start + LAYOUT.sweep_len] = log_sweep()
        y = (fftconvolve(c, chirp_ir) + fftconvolve(s_, ir))[: len(x) + FS]
    y = np.concatenate([np.zeros(int(lead_s * FS)), y]) * level
    return y + noise * RNG.standard_normal(len(y))


def at(m, f):
    return float(np.interp(np.log(f), np.log(m.freqs), m.magnitude_db))


def test_chirp_found_at_right_time():
    rec = record(room_ir(delay_ms=0.0), lead_s=0.6)
    assert find_chirp(rec) / FS == pytest.approx(0.6 + LAYOUT.lead_s, abs=0.002)


def test_measurement_sees_room_mode():
    m = measure(record(room_ir()), FS)
    assert at(m, 60) - at(m, 1000) > 5          # +8 dB mode, smoothed
    assert np.median(m.snr_db) > 30


def test_silence_and_clipping_are_reported():
    with pytest.raises(MeasurementError, match="No test signal"):
        measure(1e-4 * RNG.standard_normal(FS * 10), FS)
    with pytest.raises(MeasurementError, match="clipped"):
        measure(np.clip(record(room_ir(), level=3.0), -1, 1), FS)


def test_arrival_time_kept_without_delay_removal():
    ref = room_ir(delay_ms=3.0, seed=5)            # chirp on the main speaker
    m = measure(record(room_ir(delay_ms=15.0), chirp_ir=ref), FS, remove_delay=False)
    assert m.arrival_ms == pytest.approx(12.0, abs=0.1)


def test_average_is_db_mean():
    a = measure(record(room_ir(seed=1)), FS)
    b = measure(record(room_ir(seed=2)), FS)
    avg = average([a, b])
    assert np.allclose(avg.magnitude_db, (a.magnitude_db + b.magnitude_db) / 2)


def test_auto_eq_cuts_the_mode_and_reduces_error():
    m = measure(record(room_ir()), FS)
    tgt = target_on_grid("flat", m.freqs)
    tgt += fit_offset(m.magnitude_db, tgt, m.freqs)
    r = fit_peq(m.freqs, m.magnitude_db, tgt, EqSettings(), m.snr_db)
    deepest = min(r["filters"], key=lambda f: f.gain_db)
    assert 50 < deepest.freq < 72 and deepest.gain_db < -5
    assert r["rms_error_after_db"] < r["rms_error_before_db"] / 2
    assert r["within_tolerance_pct"] > 95


def test_only_cuts_and_limits_are_respected():
    m = measure(record(room_ir(mode=(80.0, -10.0, 6.0))), FS)   # a deep dip
    tgt = target_on_grid("flat", m.freqs)
    tgt += fit_offset(m.magnitude_db, tgt, m.freqs)
    r = fit_peq(m.freqs, m.magnitude_db, tgt, EqSettings(allow_only_cuts=True, max_filters=4, max_gain_db=6), m.snr_db)
    assert len(r["filters"]) <= 4
    assert all(f.gain_db <= 0 and f.gain_db >= -6.01 for f in r["filters"])


def test_geq_and_fir():
    grid = np.geomspace(20, 20000, 480)
    corr = response_db([Filter("peak", 100, -6, 1.0)], grid)
    bands = {b["freq"]: b["gain_db"] for b in geq31(grid, corr)}
    assert bands[100] <= -5 and bands[1000] == 0
    fir = min_phase_fir(grid, corr)
    assert int(np.argmax(np.abs(fir))) < 50                    # minimum phase: no pre-delay
    h = np.abs(np.fft.rfft(fir, 1 << 16))
    f = np.fft.rfftfreq(1 << 16, 1 / FS)
    assert 20 * np.log10(h[np.argmin(abs(f - 100))]) == pytest.approx(-6, abs=1.0)


def test_exports():
    filters = [Filter("peak", 60, -8, 4), Filter("high_shelf", 6000, 2, 0.7)]
    mini = minidsp_biquads(filters, 48000).splitlines()
    assert mini[0] == "biquad1," and mini[6] == "biquad2," and not mini[-1].endswith(",")
    _, a = coefficients(filters[0], 48000)
    assert float(mini[4].split("=")[1].rstrip(",")) == pytest.approx(-a[1])   # sign-flipped a1
    assert "Filter 1: ON PK Fc 60 Hz Gain -8.0 dB Q 4.00" in peq_text(filters)


def test_curve_file_parsing():
    f, g = parse_curve("* comment\n20 3\n1000,0\n20000\t-4\n")
    assert list(f) == [20, 1000, 20000] and list(g) == [3, 0, -4]
    with pytest.raises(ValueError):
        parse_curve("100 0\n50 1\n")


def test_room_acoustics():
    r = analyze_room(room_ir(rt60=1.5, mode=(60, 0.0, 1.0)), FS, volume_m3=3000)
    assert r["rt60_mid_s"] == pytest.approx(1.5, rel=0.15)
    assert schroeder_frequency(1.5, 3000) == pytest.approx(44.7, abs=0.1)
    assert r["speech_rating"] in {"good", "fair", "poor"}


def test_sub_alignment_finds_delay():
    # FOH-like position: direct sound dominates the first milliseconds (DRR ~ +5 dB)
    ref = room_ir(delay_ms=5.0, seed=5, reverb=0.01)            # chirp always on the left main
    main = measure(record(room_ir(delay_ms=5.0, seed=5, reverb=0.01), chirp_ir=ref), FS, remove_delay=False)
    sub = measure(record(room_ir(delay_ms=9.0, seed=6, reverb=0.01), chirp_ir=ref), FS, remove_delay=False)
    r = align(main, sub, 100.0)
    assert r["delay_main_ms"] == pytest.approx(4.0, abs=0.5)
    assert r["delay_sub_ms"] == 0


def test_tuning_api_flow():
    c = TestClient(app)
    assert c.get("/api/tuning/test-signal.wav").headers["content-type"] == "audio/wav"
    assert "worship_warm" in c.get("/api/tuning/targets").json()["curves"]
    buf = io.BytesIO()
    sf.write(buf, record(room_ir()).astype(np.float32), FS, format="WAV", subtype="FLOAT")
    m = c.post("/api/tuning/measure", files={"file": ("rec.wav", buf.getvalue(), "audio/wav")},
               data={"label": "Center", "room_volume_m3": "1500"}).json()
    assert m["id"] and m["room"]["rt60_mid_s"] > 0 and m["room"]["schroeder_hz"] > 0
    avg = c.post("/api/tuning/average", json={"ids": [m["id"], m["id"]]}).json()
    assert avg["room"]["schroeder_hz"] == pytest.approx(m["room"]["schroeder_hz"], rel=0.05)
    eq = c.post("/api/tuning/equalize", json={"measurement_id": m["id"], "target": "flat",
                                              "console": "behringer-x32"}).json()
    assert eq["filters"] and eq["console_plan"]["osc"][0]["address"] == "/main/st/eq/on"
    for fmt in ("peq_text", "minidsp", "camilladsp", "fir_wav", "console"):
        r = c.post("/api/tuning/export", json={"measurement_id": m["id"], "format": fmt})
        assert r.status_code == 200 and len(r.content) > 50
