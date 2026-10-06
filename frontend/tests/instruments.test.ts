import { describe, expect, it } from "vitest";

import { guessProfile } from "@/lib/instruments";

describe("guessProfile", () => {
  it("maps typical channel names", () => {
    expect(guessProfile("Kick In")).toBe("kick");
    expect(guessProfile("Snare Top")).toBe("snare");
    expect(guessProfile("Floor Tom")).toBe("tom3");
    expect(guessProfile("Bass DI")).toBe("bass");
    expect(guessProfile("Acoustic Gtr")).toBe("acoustic_guitar");
    expect(guessProfile("Aux Keys")).toBe("aux_keys");
    expect(guessProfile("Lead Vox")).toBe("lead_vocal_m");
    expect(guessProfile("BGV 2")).toBe("bgv");
    expect(guessProfile("Pastor Headset")).toBe("speech");
    expect(guessProfile("SPD-SX")).toBe("sample_pad");
    expect(guessProfile("Violin")).toBe("violin");
  });
});
