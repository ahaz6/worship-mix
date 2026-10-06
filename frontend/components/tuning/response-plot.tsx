"use client";

/**
 * Frequency response plot (log axis). Colours come only from suite tokens:
 *   measurement  --wm-success      target + ±3 dB band  --wm-violet-bright
 *   reference    --wm-text-muted   predicted            --wm-blue
 *   correction   --wm-warning
 * Blanked (low SNR) regions are gaps in the line.
 */
import { useMemo, useState } from "react";

import { formatHz, freqOfX, niceRange, tracePath, xOfFreq } from "@/lib/plot";

export type Trace = { id: string; label: string; values: (number | null)[]; tone: "measured" | "reference" | "predicted" | "correction" };

const W = 720;
const H = 300;
const PAD = { l: 40, r: 12, t: 12, b: 24 };
const GRID_F = [20, 50, 100, 200, 500, 1000, 2000, 5000, 10000, 20000];

export function ResponsePlot({
  freqs,
  traces,
  target,
  tolerance = 3,
  unit = "dB",
  ariaLabel,
}: {
  freqs: number[];
  traces: Trace[];
  target?: number[];
  tolerance?: number;
  unit?: string;
  ariaLabel: string;
}) {
  const [cursor, setCursor] = useState<number | null>(null);
  const iw = W - PAD.l - PAD.r;
  const ih = H - PAD.t - PAD.b;
  const [lo, hi] = useMemo(() => niceRange([...traces.map((t) => t.values), target ?? []]), [traces, target]);
  const x = (f: number) => PAD.l + xOfFreq(f, iw);
  const y = (v: number) => PAD.t + ((hi - v) / (hi - lo)) * ih;
  const ticks = [];
  for (let v = lo; v <= hi; v += (hi - lo) / 6) ticks.push(Math.round(v));

  const band = target
    ? `${tracePath(freqs, target.map((v) => v + tolerance), x, y)}${tracePath([...freqs].reverse(), [...target].reverse().map((v) => v - tolerance), x, y).replace(/^M/, "L")}Z`
    : "";

  const ci = cursor === null ? null : freqs.reduce((best, f, i) => (Math.abs(Math.log(f / cursor)) < Math.abs(Math.log(freqs[best]! / cursor)) ? i : best), 0);

  return (
    <figure className="response-plot">
      <svg
        viewBox={`0 0 ${W} ${H}`}
        role="img"
        aria-label={ariaLabel}
        onClick={(e) => {
          const r = (e.currentTarget as SVGSVGElement).getBoundingClientRect();
          const px = ((e.clientX - r.left) / r.width) * W - PAD.l;
          setCursor(cursor === null && px >= 0 && px <= iw ? freqOfX(px, iw) : null);
        }}
      >
        {GRID_F.map((f) => (
          <g key={f}>
            <line className="grid" x1={x(f)} x2={x(f)} y1={PAD.t} y2={PAD.t + ih} />
            <text className="axis" x={x(f)} y={H - 6} textAnchor="middle">
              {formatHz(f)}
            </text>
          </g>
        ))}
        {ticks.map((v) => (
          <g key={v}>
            <line className="grid" x1={PAD.l} x2={PAD.l + iw} y1={y(v)} y2={y(v)} />
            <text className="axis" x={PAD.l - 6} y={y(v) + 3} textAnchor="end">
              {v}
            </text>
          </g>
        ))}
        {target ? <path className="tol-band" d={band} /> : null}
        {target ? <path className="trace tone-target" d={tracePath(freqs, target, x, y)} /> : null}
        {traces.map((t) => (
          <path key={t.id} className={`trace tone-${t.tone}`} d={tracePath(freqs, t.values, x, y)} />
        ))}
        {ci !== null ? <line className="cursor" x1={x(freqs[ci]!)} x2={x(freqs[ci]!)} y1={PAD.t} y2={PAD.t + ih} /> : null}
      </svg>
      <figcaption className="plot-legend">
        {target ? <span className="tone-target">Target ±{tolerance} dB</span> : null}
        {traces.map((t) => (
          <span key={t.id} className={`tone-${t.tone}`}>
            {t.label}
          </span>
        ))}
        {ci !== null ? (
          <span className="mono cursor-readout">
            {Math.round(freqs[ci]!)} Hz ·{" "}
            {traces
              .map((t) => t.values[ci])
              .filter((v): v is number => v !== null && v !== undefined)
              .map((v) => `${v.toFixed(1)} ${unit}`)
              .join(" / ") || "blanked"}
          </span>
        ) : (
          <span className="hint">Tap the plot for a cursor.</span>
        )}
      </figcaption>
    </figure>
  );
}
