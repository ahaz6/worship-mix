import { describe, expect, it } from "vitest";

import { dbToMeter, formatDb } from "@/lib/meter";

describe("dbToMeter", () => {
  it("maps the floor, ceiling and midpoint", () => {
    expect(dbToMeter(-60)).toBe(0);
    expect(dbToMeter(0)).toBe(1);
    expect(dbToMeter(-30)).toBeCloseTo(0.5);
  });

  it("clamps out-of-range and non-finite values", () => {
    expect(dbToMeter(12)).toBe(1);
    expect(dbToMeter(-200)).toBe(0);
    expect(dbToMeter(Number.NEGATIVE_INFINITY)).toBe(0);
  });
});

describe("formatDb", () => {
  it("uses a real minus sign and one decimal", () => {
    expect(formatDb(-14.04)).toBe("−14.0");
    expect(formatDb(null)).toBe("—");
  });
});
