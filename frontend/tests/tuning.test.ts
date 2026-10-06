import { describe, expect, it } from "vitest";

import { freqOfX, niceRange, tracePath, xOfFreq } from "@/lib/plot";
import { concatChunks } from "@/lib/wav";

describe("log frequency axis", () => {
  it("maps decades evenly and round-trips", () => {
    expect(xOfFreq(20, 300)).toBe(0);
    expect(xOfFreq(20000, 300)).toBeCloseTo(300);
    expect(xOfFreq(200, 300)).toBeCloseTo(100);
    expect(freqOfX(xOfFreq(1234, 500), 500)).toBeCloseTo(1234);
  });
});

describe("tracePath", () => {
  it("breaks the line on blanked (null) values", () => {
    const d = tracePath([20, 40, 80, 160], [0, null, 1, 2], (f) => f, (v) => v);
    expect(d).toBe("M20.0,0.0M80.0,1.0L160.0,2.0");
  });
});

describe("niceRange", () => {
  it("keeps a minimum span and snaps to 6 dB", () => {
    const [lo, hi] = niceRange([[0, 1, 2]]);
    expect(hi - lo).toBeGreaterThanOrEqual(24);
    expect(Math.abs(lo % 6)).toBe(0); // -0 vs 0
  });
});

describe("concatChunks", () => {
  it("joins capture chunks in order", () => {
    expect(Array.from(concatChunks([new Float32Array([1, 2]), new Float32Array([3])]))).toEqual([1, 2, 3]);
  });
});
