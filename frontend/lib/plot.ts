/** Log-frequency plot helpers (20 Hz - 20 kHz). */
export const F_MIN = 20;
export const F_MAX = 20000;

export function xOfFreq(f: number, width: number, fmin = F_MIN, fmax = F_MAX): number {
  return (Math.log(f / fmin) / Math.log(fmax / fmin)) * width;
}

export function freqOfX(x: number, width: number, fmin = F_MIN, fmax = F_MAX): number {
  return fmin * Math.pow(fmax / fmin, x / width);
}

/** SVG path; null values break the line (coherence blanking). */
export function tracePath(freqs: number[], values: (number | null)[], x: (f: number) => number, y: (v: number) => number): string {
  let d = "";
  let pen = false;
  freqs.forEach((f, i) => {
    const v = values[i];
    if (v === null || v === undefined || !Number.isFinite(v)) {
      pen = false;
      return;
    }
    d += `${pen ? "L" : "M"}${x(f).toFixed(1)},${y(v).toFixed(1)}`;
    pen = true;
  });
  return d;
}

export function niceRange(series: (number | null)[][], pad = 3, minSpan = 24): [number, number] {
  const vals = series.flat().filter((v): v is number => v !== null && Number.isFinite(v));
  if (!vals.length) return [-30, 10];
  let lo = Math.min(...vals) - pad;
  let hi = Math.max(...vals) + pad;
  if (hi - lo < minSpan) {
    const mid = (hi + lo) / 2;
    lo = mid - minSpan / 2;
    hi = mid + minSpan / 2;
  }
  return [Math.floor(lo / 6) * 6, Math.ceil(hi / 6) * 6];
}

export function formatHz(f: number): string {
  return f >= 1000 ? `${(f / 1000).toFixed(f >= 10000 ? 0 : 1)}k` : `${Math.round(f)}`;
}
