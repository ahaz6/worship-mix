import { describe, expect, it } from "vitest";

import { fft } from "@/lib/fft";
import { Rta, TransferAnalyzer, bandCenters } from "@/lib/rta";

function rng(seed: number) {
  return () => {
    seed = (seed * 1664525 + 1013904223) >>> 0;
    return seed / 2 ** 32 - 0.5;
  };
}

describe("fft", () => {
  it("matches a direct DFT", () => {
    const n = 16;
    const x = Array.from({ length: n }, (_, i) => Math.sin(i) + 0.3 * Math.cos(3 * i));
    const re = Float64Array.from(x);
    const im = new Float64Array(n);
    fft(re, im);
    for (let k = 0; k < n; k++) {
      let r = 0;
      let i = 0;
      x.forEach((v, t) => {
        r += v * Math.cos((-2 * Math.PI * k * t) / n);
        i += v * Math.sin((-2 * Math.PI * k * t) / n);
      });
      expect(re[k]).toBeCloseTo(r, 9);
      expect(im[k]).toBeCloseTo(i, 9);
    }
  });

  it("inverse restores the signal", () => {
    const re = Float64Array.from([1, 2, 3, 4, 5, 6, 7, 8]);
    const im = new Float64Array(8);
    fft(re, im);
    fft(re, im, true);
    expect(Array.from(re).map((v) => Math.round(v))).toEqual([1, 2, 3, 4, 5, 6, 7, 8]);
  });
});

describe("bandCenters", () => {
  it("gives ~31 third-octave bands anchored at 1 kHz", () => {
    const c = bandCenters(3);
    expect(c.length).toBe(31);
    expect(c.some((f) => Math.abs(f - 1000) < 1e-9)).toBe(true);
  });
});

describe("Rta", () => {
  it("shows white noise rising ~3 dB per octave", () => {
    const r = new Rta(48000, 1, "moving");
    const rand = rng(1);
    r.push(Float32Array.from({ length: 48000 * 2 }, () => rand()));
    const lv = r.levels();
    const c = r.centers;
    const i1 = c.findIndex((f) => Math.abs(f - 1000) < 1);
    expect(lv[i1 + 1]! - lv[i1]!).toBeCloseTo(3, 0);
  });
});

describe("TransferAnalyzer", () => {
  const n = 4096;
  const rand = rng(7);
  const ref = Float32Array.from({ length: n }, () => rand());

  it("recovers gain, ignores the bulk delay and reports full coherence", () => {
    const t = new TransferAnalyzer(ref, 48000, "moving");
    const delay = 300;
    for (let p = 0; p < 4; p++) {
      const y = Float32Array.from({ length: n }, (_, i) => 0.5 * ref[(i - delay + n * 4) % n]!);
      t.push(y);
    }
    const s = t.snapshot(6, 64, 0);
    const mid = s.freqs.findIndex((f) => f > 1000);
    expect(s.magnitudeDb[mid]).toBeCloseTo(-6.02, 1);
    expect(s.coherence[mid]).toBeGreaterThan(0.99);
    expect(s.delayMs).toBeCloseTo((delay / 48000) * 1000, 3);
  });

  it("lower coherence when noise is added", () => {
    const t = new TransferAnalyzer(ref, 48000, "moving");
    for (let p = 0; p < 8; p++) t.push(Float32Array.from({ length: n }, (_, i) => 0.1 * ref[i]! + 0.2 * rand()));
    const s = t.snapshot(6, 64, 0);
    const mid = s.freqs.findIndex((f) => f > 1000);
    expect(s.coherence[mid]).toBeLessThan(0.8);
  });
});
