/**
 * Real-time analysis (browser, Web Audio).
 *
 * 1) Rta — single channel, fractional-octave band levels with Fast/Slow/Moving-mic
 *    averaging. Works with any signal; with pink noise a flat display = flat system.
 * 2) TransferAnalyzer — dual-channel style transfer function against *periodic*
 *    pink noise whose exact period we know (no reference cable). Per period:
 *    circular cross-correlation finds the delay, H = Y/X, then vector averaging.
 *    Coherence γ² = |mean H|² / mean|H|² (1 = clean, lower = noise/reverb).
 */
import { fft, hann } from "@/lib/fft";

export type Averaging = "fast" | "slow" | "moving";
export const AVG_SECONDS: Record<Averaging, number> = { fast: 0.125, slow: 1, moving: Infinity };

export function bandCenters(fraction: number, fmin = 20, fmax = 20000): number[] {
  const out: number[] = [];
  // base-2 centres anchored at 1 kHz; 5 % tolerance so nominal 20 Hz / 20 kHz bands are included
  for (let k = Math.ceil(fraction * Math.log2((fmin * 0.95) / 1000)); ; k++) {
    const f = 1000 * Math.pow(2, k / fraction);
    if (f > fmax * 1.05) break;
    out.push(f);
  }
  return out;
}

/* ------------------------------------------------------------------ RTA -- */

export class Rta {
  readonly size: number;
  readonly centers: number[];
  private readonly win: Float64Array;
  private readonly buf: Float64Array;
  private fill = 0;
  private readonly power: Float64Array;
  private frames = 0;
  private readonly edges: [number, number][];

  constructor(
    readonly sampleRate: number,
    readonly fraction = 3,
    public averaging: Averaging = "slow",
    size = 8192,
  ) {
    this.size = size;
    this.win = hann(size);
    this.buf = new Float64Array(size);
    this.centers = bandCenters(fraction);
    this.power = new Float64Array(this.centers.length);
    const half = Math.pow(2, 1 / (2 * fraction));
    const binHz = sampleRate / size;
    this.edges = this.centers.map((c) => [Math.max(1, Math.floor(c / half / binHz)), Math.max(1, Math.ceil((c * half) / binHz))]);
  }

  reset(): void {
    this.power.fill(0);
    this.frames = 0;
  }

  /** Feed samples; returns true when the display changed. */
  push(samples: Float32Array): boolean {
    let updated = false;
    for (const s of samples) {
      this.buf[this.fill++] = s;
      if (this.fill === this.size) {
        this.frame();
        // 50 % overlap
        this.buf.copyWithin(0, this.size / 2);
        this.fill = this.size / 2;
        updated = true;
      }
    }
    return updated;
  }

  private frame(): void {
    const re = new Float64Array(this.size);
    const im = new Float64Array(this.size);
    for (let i = 0; i < this.size; i++) re[i] = this.buf[i]! * this.win[i]!;
    fft(re, im);
    const norm = 2 / (this.size * 0.375 * this.size); // Hann power normalisation
    const hop = this.size / 2 / this.sampleRate;
    const tau = AVG_SECONDS[this.averaging];
    this.frames++;
    const a = Number.isFinite(tau) ? 1 - Math.exp(-hop / tau) : 1 / this.frames;
    this.edges.forEach(([lo, hi], b) => {
      let p = 0;
      for (let k = lo; k <= Math.min(hi, this.size / 2 - 1); k++) p += (re[k]! * re[k]! + im[k]! * im[k]!) * norm;
      this.power[b] = this.frames === 1 ? p : this.power[b]! + a * (p - this.power[b]!);
    });
  }

  /** Band levels in dBFS. */
  levels(): number[] {
    return Array.from(this.power, (p) => 10 * Math.log10(p + 1e-20));
  }
}

/* ----------------------------------------------------- transfer function -- */

export type TransferSnapshot = {
  freqs: number[];
  magnitudeDb: (number | null)[];
  phaseDeg: (number | null)[];
  coherence: number[];
  delayMs: number;
  periods: number;
};

export class TransferAnalyzer {
  readonly n: number;
  private readonly xr: Float64Array;
  private readonly xi: Float64Array;
  private readonly xPow: Float64Array;
  private readonly buf: Float64Array;
  private fill = 0;
  private hr: Float64Array;
  private hi: Float64Array;
  private hp: Float64Array;
  private count = 0;
  private lag = 0;

  constructor(
    readonly reference: Float32Array,
    readonly sampleRate: number,
    public averaging: Averaging = "slow",
  ) {
    this.n = reference.length;
    this.xr = Float64Array.from(reference);
    this.xi = new Float64Array(this.n);
    fft(this.xr, this.xi);
    this.xPow = new Float64Array(this.n / 2 + 1);
    for (let k = 0; k <= this.n / 2; k++) this.xPow[k] = this.xr[k]! ** 2 + this.xi[k]! ** 2;
    this.buf = new Float64Array(this.n);
    this.hr = new Float64Array(this.n / 2 + 1);
    this.hi = new Float64Array(this.n / 2 + 1);
    this.hp = new Float64Array(this.n / 2 + 1);
  }

  reset(): void {
    this.hr.fill(0);
    this.hi.fill(0);
    this.hp.fill(0);
    this.count = 0;
  }

  get periods(): number {
    return this.count;
  }

  push(samples: Float32Array): boolean {
    let updated = false;
    for (const s of samples) {
      this.buf[this.fill++] = s;
      if (this.fill === this.n) {
        this.period();
        this.fill = 0;
        updated = true;
      }
    }
    return updated;
  }

  private period(): void {
    const n = this.n;
    const yr = Float64Array.from(this.buf);
    const yi = new Float64Array(n);
    fft(yr, yi);
    // circular cross-correlation Y·conj(X) -> lag of the period start
    const cr = new Float64Array(n);
    const ci = new Float64Array(n);
    for (let k = 0; k < n; k++) {
      cr[k] = yr[k]! * this.xr[k]! + yi[k]! * this.xi[k]!;
      ci[k] = yi[k]! * this.xr[k]! - yr[k]! * this.xi[k]!;
    }
    fft(cr, ci, true);
    let best = 0;
    for (let i = 1; i < n; i++) if (Math.abs(cr[i]!) > Math.abs(cr[best]!)) best = i;
    this.lag = best;
    const tau = AVG_SECONDS[this.averaging];
    this.count++;
    const a = Number.isFinite(tau) ? Math.min(1, 1 - Math.exp(-(n / this.sampleRate) / tau)) : 1 / this.count;
    for (let k = 1; k <= n / 2; k++) {
      const xp = this.xPow[k]!;
      if (xp < 1e-12) continue;
      // H = Y X* / |X|², then remove the bulk delay e^{+j2πk·lag/n}
      const hr0 = (yr[k]! * this.xr[k]! + yi[k]! * this.xi[k]!) / xp;
      const hi0 = (yi[k]! * this.xr[k]! - yr[k]! * this.xi[k]!) / xp;
      const ph = (2 * Math.PI * k * best) / n;
      const c = Math.cos(ph);
      const s = Math.sin(ph);
      const hr = hr0 * c - hi0 * s;
      const hi = hr0 * s + hi0 * c;
      const first = this.count === 1;
      this.hr[k] = first ? hr : this.hr[k]! + a * (hr - this.hr[k]!);
      this.hi[k] = first ? hi : this.hi[k]! + a * (hi - this.hi[k]!);
      const p = hr * hr + hi * hi;
      this.hp[k] = first ? p : this.hp[k]! + a * (p - this.hp[k]!);
    }
  }

  /** Smoothed result on a log grid. Values with coherence < minCoherence are blanked. */
  snapshot(fraction = 12, points = 320, minCoherence = 0.5): TransferSnapshot {
    const freqs: number[] = [];
    const mag: (number | null)[] = [];
    const phase: (number | null)[] = [];
    const coh: number[] = [];
    const binHz = this.sampleRate / this.n;
    const half = Math.pow(2, 1 / (2 * fraction));
    for (let i = 0; i < points; i++) {
      const f = 20 * Math.pow(1000, i / (points - 1));
      const lo = Math.max(1, Math.floor(f / half / binHz));
      const hi = Math.min(this.n / 2, Math.ceil((f * half) / binHz));
      let sr = 0;
      let si = 0;
      let sp = 0;
      let cnt = 0;
      for (let k = lo; k <= hi; k++) {
        sr += this.hr[k]!;
        si += this.hi[k]!;
        sp += this.hp[k]!;
        cnt++;
      }
      // coherence is computed per bin pair, approximated per band from the averages
      const vec = (sr * sr + si * si) / (cnt * cnt);
      const pw = sp / cnt;
      const g = this.count < 2 ? 1 : Math.min(1, vec / (pw + 1e-30));
      freqs.push(f);
      coh.push(g);
      const ok = g >= minCoherence && pw > 0;
      mag.push(ok ? 10 * Math.log10(pw + 1e-30) : null);
      phase.push(ok ? (Math.atan2(si, sr) * 180) / Math.PI : null);
    }
    return { freqs, magnitudeDb: mag, phaseDeg: phase, coherence: coh, delayMs: (this.lag / this.sampleRate) * 1000, periods: this.count };
  }
}
