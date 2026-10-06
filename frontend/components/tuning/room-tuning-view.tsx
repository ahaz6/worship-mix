"use client";

/**
 * Module 06 — Room Tuning.
 *
 * Flow: Setup → Measure (several seats) → Average → Equalize → Export / console,
 * plus Room acoustics (RT60, C50) and Sub alignment. See WORSHIP_MIX.md ch. 11a.
 */
import { useCallback, useEffect, useMemo, useState } from "react";

import { Status } from "@/components/common/status";
import { ResponsePlot, type Trace } from "@/components/tuning/response-plot";
import { recordMeasurement } from "@/lib/recorder";
import {
  type AlignResult,
  DEFAULT_EQ,
  type EqOptions,
  type EqualizeResult,
  type TuningMeasurement,
  align,
  averageMeasurements,
  deleteMeasurement,
  equalize,
  exportFilters,
  fetchTargets,
  uploadMeasurement,
} from "@/lib/tuning";

type Tab = "measure" | "equalize" | "room" | "align";
type PlotKind = "magnitude" | "phase" | "group_delay";

const RECORD_SECONDS = 11; // test signal is ~8.1 s; margin for starting playback
const SEATS = ["Front left", "Front center", "Front right", "Middle", "FOH", "Back left", "Back right", "Balcony"];

const EXPORTS = [
  { id: "console", label: "Console steps" },
  { id: "peq_text", label: "PEQ text" },
  { id: "minidsp", label: "miniDSP biquads" },
  { id: "camilladsp", label: "CamillaDSP" },
  { id: "fir_wav", label: "FIR (min phase)" },
];

export function RoomTuningView() {
  const [tab, setTab] = useState<Tab>("measure");
  const [items, setItems] = useState<TuningMeasurement[]>([]);
  const [selected, setSelected] = useState<string[]>([]);
  const [active, setActive] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const add = useCallback((m: TuningMeasurement) => {
    setItems((xs) => [...xs, m]);
    setActive(m.id);
  }, []);

  const current = items.find((m) => m.id === active) ?? null;

  return (
    <>
      <div className="tab-row" role="tablist" aria-label="Room tuning steps">
        {(
          [
            ["measure", "1 · Measure"],
            ["equalize", "2 · Equalize"],
            ["room", "Room acoustics"],
            ["align", "Sub alignment"],
          ] as const
        ).map(([id, label]) => (
          <button key={id} type="button" role="tab" aria-selected={tab === id} className={`btn${tab === id ? " is-active" : ""}`} onClick={() => setTab(id)}>
            {label}
          </button>
        ))}
      </div>

      {error ? <Status tone="danger" state="Problem" detail={error} /> : null}

      {tab === "measure" ? (
        <MeasureStep
          items={items}
          selected={selected}
          setSelected={setSelected}
          active={active}
          setActive={setActive}
          onAdd={add}
          onDelete={(id) => {
            void deleteMeasurement(id);
            setItems((xs) => xs.filter((m) => m.id !== id));
            setSelected((s) => s.filter((x) => x !== id));
          }}
          setError={setError}
          current={current}
        />
      ) : null}
      {tab === "equalize" ? <EqualizeStep items={items} active={active} setActive={setActive} setError={setError} /> : null}
      {tab === "room" ? <RoomStep current={current} /> : null}
      {tab === "align" ? <AlignStep items={items} setError={setError} /> : null}
    </>
  );
}

/* ------------------------------------------------------------- measure -- */

function MeasureStep({
  items,
  selected,
  setSelected,
  active,
  setActive,
  onAdd,
  onDelete,
  setError,
  current,
}: {
  items: TuningMeasurement[];
  selected: string[];
  setSelected: (fn: (s: string[]) => string[]) => void;
  active: string | null;
  setActive: (id: string) => void;
  onAdd: (m: TuningMeasurement) => void;
  onDelete: (id: string) => void;
  setError: (e: string | null) => void;
  current: TuningMeasurement | null;
}) {
  const [seat, setSeat] = useState(SEATS[1]!);
  const [removeDelay, setRemoveDelay] = useState(true);
  const [volume, setVolume] = useState<string>("");
  const [busy, setBusy] = useState<"idle" | "listening" | "processing">("idle");
  const [level, setLevel] = useState(0);
  const [plot, setPlot] = useState<PlotKind>("magnitude");

  const process = async (wav: Blob) => {
    setBusy("processing");
    try {
      onAdd(await uploadMeasurement(wav, `${seat} ${items.length + 1}`, removeDelay, Number(volume) || undefined));
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Measurement failed.");
    } finally {
      setBusy("idle");
    }
  };

  const listen = async () => {
    setError(null);
    setBusy("listening");
    try {
      const rec = await recordMeasurement(RECORD_SECONDS, undefined, setLevel);
      await process(rec.wav);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Recording failed.");
      setBusy("idle");
    }
  };

  const shown = items.filter((m) => selected.includes(m.id) || m.id === active);
  const traces: Trace[] = shown.map((m) => ({
    id: m.id,
    label: m.label,
    tone: m.id === active ? "measured" : "reference",
    values: plot === "magnitude" ? m.magnitude_db : plot === "phase" ? m.phase_deg : m.group_delay_ms,
  }));

  return (
    <>
      <section className="panel-card">
        <span className="section-title">Setup</span>
        <ol className="steps">
          <li>
            Play the{" "}
            <a className="link" href="/api/tuning/test-signal.wav" download>
              test signal
            </a>{" "}
            through the PA (console USB playback or a laptop on a stereo channel). Turn all room EQ off first.
          </li>
          <li>Place the mic at ear height of a seated person, pointing at the stage.</li>
          <li>Measure 5–8 seats across the room, then average them. Never boost what only one seat hears.</li>
        </ol>
        <div className="inline-fields">
          <label className="field">
            <span className="label">Seat</span>
            <select value={seat} onChange={(e) => setSeat(e.target.value)}>
              {SEATS.map((s) => (
                <option key={s}>{s}</option>
              ))}
            </select>
          </label>
          <label className="field">
            <span className="label">Room volume (m³, optional)</span>
            <input type="number" min={10} placeholder="e.g. 2500" value={volume} onChange={(e) => setVolume(e.target.value)} />
          </label>
        </div>
        <label className="check">
          <input type="checkbox" checked={removeDelay} onChange={(e) => setRemoveDelay(e.target.checked)} />
          Remove delay <span className="hint">— on for averaging seats, off for sub alignment</span>
        </label>
        <div className="btn-row">
          <button className="btn-primary is-inline" type="button" onClick={() => void listen()} disabled={busy !== "idle"}>
            {busy === "listening" ? "Listening… start playback now" : busy === "processing" ? "Processing…" : "Measure this seat"}
          </button>
          <label className="btn">
            Upload recording
            <input
              className="visually-hidden"
              type="file"
              accept="audio/*"
              onChange={(e) => {
                const f = e.target.files?.[0];
                if (f) void process(f);
              }}
            />
          </label>
        </div>
        {busy === "listening" ? (
          <div className="level-meter" aria-label="Mic input level">
            <div className="track">
              <div className="fill" style={{ width: `${Math.min(100, level * 100)}%` }} />
            </div>
          </div>
        ) : null}
      </section>

      {items.length ? (
        <section className="panel-card">
          <div className="section-title">
            <span>Measurements</span>
            <span className="btn-row">
              <button
                className="btn"
                type="button"
                disabled={selected.length < 2}
                onClick={async () => {
                  try {
                    onAdd(await averageMeasurements(selected));
                    setSelected(() => []);
                  } catch (e) {
                    setError(e instanceof Error ? e.message : "Averaging failed.");
                  }
                }}
              >
                Average {selected.length || ""}
              </button>
            </span>
          </div>
          <ul className="measure-list">
            {items.map((m) => (
              <li key={m.id} className={m.id === active ? "is-active" : ""}>
                <input
                  type="checkbox"
                  aria-label={`Select ${m.label}`}
                  checked={selected.includes(m.id)}
                  onChange={(e) => setSelected((s) => (e.target.checked ? [...s, m.id] : s.filter((x) => x !== m.id)))}
                />
                <button type="button" className="measure-name" onClick={() => setActive(m.id)}>
                  {m.label}
                  <small className="mono">
                    {m.room.rt60_mid_s ? `RT60 ${m.room.rt60_mid_s.toFixed(2)} s · ` : ""}
                    {m.arrival_ms ? `${m.arrival_ms.toFixed(1)} ms` : "delay removed"}
                  </small>
                </button>
                <button type="button" className="btn tone-quiet" onClick={() => onDelete(m.id)} aria-label={`Delete ${m.label}`}>
                  ✕
                </button>
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      {current ? (
        <section className="panel-card">
          <div className="section-title">
            <span>{current.label}</span>
            <PlotSwitch value={plot} onChange={setPlot} />
          </div>
          <ResponsePlot
            freqs={current.freqs}
            traces={traces}
            unit={plot === "magnitude" ? "dB" : plot === "phase" ? "°" : "ms"}
            ariaLabel={`${plot} response of ${current.label}`}
          />
          <p className="hint">Gaps mean the signal was less than 10 dB above the background noise there (blanked).</p>
        </section>
      ) : null}
    </>
  );
}

function PlotSwitch({ value, onChange }: { value: PlotKind; onChange: (p: PlotKind) => void }) {
  return (
    <span className="btn-row">
      {(
        [
          ["magnitude", "Magnitude"],
          ["phase", "Phase"],
          ["group_delay", "Group delay"],
        ] as const
      ).map(([id, label]) => (
        <button key={id} type="button" className={`btn${value === id ? " is-active" : ""}`} onClick={() => onChange(id)}>
          {label}
        </button>
      ))}
    </span>
  );
}

/* ------------------------------------------------------------ equalize -- */

function EqualizeStep({
  items,
  active,
  setActive,
  setError,
}: {
  items: TuningMeasurement[];
  active: string | null;
  setActive: (id: string) => void;
  setError: (e: string | null) => void;
}) {
  const [opts, setOpts] = useState<EqOptions>(DEFAULT_EQ);
  const [targets, setTargets] = useState<Record<string, { label: string; use: string }>>({});
  const [result, setResult] = useState<EqualizeResult | null>(null);
  const set = <K extends keyof EqOptions>(k: K, v: EqOptions[K]) => setOpts((o) => ({ ...o, [k]: v }));

  useEffect(() => {
    fetchTargets()
      .then((t) => setTargets(t.curves))
      .catch(() => setError("Could not load target curves. Is the backend running?"));
  }, [setError]);

  useEffect(() => {
    if (!active) return;
    let cancelled = false;
    equalize(active, opts)
      .then((r) => !cancelled && setResult(r))
      .catch((e: unknown) => !cancelled && setError(e instanceof Error ? e.message : "Equalize failed."));
    return () => {
      cancelled = true;
    };
  }, [active, opts, setError]);

  if (!items.length) return <Status tone="info" state="No measurement yet" detail="Measure and average a few seats first." />;

  const traces: Trace[] = result
    ? [
        { id: "m", label: "Measured", tone: "measured", values: result.measured_db },
        { id: "p", label: "Predicted", tone: "predicted", values: result.predicted_db },
      ]
    : [];
  const corrTraces: Trace[] = result ? [{ id: "c", label: "Correction", tone: "correction", values: result.correction_db }] : [];

  return (
    <>
      <section className="panel-card">
        <span className="section-title">Equalize setup</span>
        <div className="inline-fields three">
          <label className="field">
            <span className="label">Measurement</span>
            <select value={active ?? ""} onChange={(e) => setActive(e.target.value)}>
              {items.map((m) => (
                <option key={m.id} value={m.id}>
                  {m.label}
                </option>
              ))}
            </select>
          </label>
          <label className="field">
            <span className="label">Target curve</span>
            <select value={opts.target} onChange={(e) => set("target", e.target.value)}>
              {Object.entries(targets).map(([id, t]) => (
                <option key={id} value={id}>
                  {t.label}
                </option>
              ))}
            </select>
          </label>
          <label className="field">
            <span className="label">Console</span>
            <select value={opts.console} onChange={(e) => set("console", e.target.value)}>
              <option value="generic">Any console</option>
              <option value="allen-heath-sq">Allen &amp; Heath SQ</option>
              <option value="behringer-x32">Behringer X32 / M32</option>
            </select>
          </label>
        </div>
        {targets[opts.target] ? <p className="hint">{targets[opts.target]!.use}</p> : null}
        <div className="inline-fields three">
          <NumberField label="Max filters" value={opts.max_filters} min={1} max={20} onChange={(v) => set("max_filters", v)} />
          <NumberField label="Max cut (dB)" value={opts.max_gain_db} min={1} max={15} onChange={(v) => set("max_gain_db", v)} />
          <NumberField label="Max boost (dB)" value={opts.max_boost_db} min={0} max={15} onChange={(v) => set("max_boost_db", v)} />
          <NumberField label="Max Q" value={opts.max_q} min={0.5} max={20} step={0.5} onChange={(v) => set("max_q", v)} />
          <NumberField label="From (Hz)" value={opts.fmin} min={20} max={500} onChange={(v) => set("fmin", v)} />
          <NumberField label="To (Hz)" value={opts.fmax} min={1000} max={20000} step={500} onChange={(v) => set("fmax", v)} />
        </div>
        <div className="btn-row">
          <label className="check">
            <input type="checkbox" checked={opts.allow_only_cuts} onChange={(e) => set("allow_only_cuts", e.target.checked)} />
            Cuts only
          </label>
          <label className="check">
            <input type="checkbox" checked={opts.allow_shelves} onChange={(e) => set("allow_shelves", e.target.checked)} />
            Shelf filters
          </label>
        </div>
      </section>

      {result ? (
        <>
          <div className="metric-grid">
            <Metric label="Error before" value={result.rms_error_before_db.toFixed(1)} unit="dB rms" />
            <Metric label="Error after" value={result.rms_error_after_db.toFixed(1)} unit="dB rms" />
            <Metric label="Within ±3 dB" value={result.within_tolerance_pct.toFixed(0)} unit="%" />
            <Metric label="Lower main by" value={Math.abs(result.preamp_db).toFixed(1)} unit="dB" />
          </div>
          <section className="panel-card">
            <span className="section-title">Response</span>
            <ResponsePlot freqs={result.freqs} traces={traces} target={result.target_db} tolerance={result.tolerance_db} ariaLabel="Measured, target and predicted response" />
            <ResponsePlot freqs={result.freqs} traces={corrTraces} ariaLabel="Correction curve" />
          </section>
          <section className="panel-card">
            <span className="section-title">PEQ filters · main L/R</span>
            <table className="data-table">
              <thead>
                <tr>
                  <th>#</th>
                  <th>Type</th>
                  <th>Freq</th>
                  <th>Gain</th>
                  <th>Q</th>
                </tr>
              </thead>
              <tbody>
                {result.filters.map((f, i) => (
                  <tr key={i}>
                    <td>{i + 1}</td>
                    <td>{f.type.replace("_", " ")}</td>
                    <td className="mono">{Math.round(f.freq)} Hz</td>
                    <td className="mono">
                      {f.gain_db > 0 ? "+" : ""}
                      {f.gain_db.toFixed(1)} dB
                    </td>
                    <td className="mono">{f.q.toFixed(2)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>
          <section className="panel-card">
            <span className="section-title">31-band GEQ · for any console</span>
            <GeqBars bands={result.geq31} />
          </section>
          <section className="panel-card">
            <span className="section-title">Export</span>
            <div className="btn-row">
              {EXPORTS.map((x) => (
                <button key={x.id} type="button" className="btn" onClick={() => active && void exportFilters(active, opts, x.id).catch(() => setError("Export failed."))}>
                  {x.label}
                </button>
              ))}
            </div>
            <ul className="steps">
              {result.console_plan.peq_steps.slice(0, 1).map((s) => (
                <li key={s}>{s}</li>
              ))}
            </ul>
            <p className="hint">FIR export is minimum phase: no added latency, safe for live PA processors.</p>
          </section>
        </>
      ) : null}
    </>
  );
}

function GeqBars({ bands }: { bands: { freq: number; gain_db: number }[] }) {
  return (
    <div className="geq" role="img" aria-label="31-band graphic EQ settings">
      {bands.map((b) => (
        <div key={b.freq} className="geq-band" title={`${b.freq} Hz ${b.gain_db.toFixed(1)} dB`}>
          <div className="geq-track">
            <div
              className={`geq-fill ${b.gain_db >= 0 ? "up" : "down"}`}
              style={{ height: `${(Math.min(12, Math.abs(b.gain_db)) / 12) * 50}%` }}
            />
          </div>
          <span className="geq-label">{b.freq >= 1000 ? `${b.freq / 1000}k` : b.freq}</span>
        </div>
      ))}
    </div>
  );
}

/* --------------------------------------------------------------- room -- */

function RoomStep({ current }: { current: TuningMeasurement | null }) {
  if (!current?.room.bands) return <Status tone="info" state="No measurement yet" detail="Room acoustics are computed from every measurement." />;
  const r = current.room;
  const rating = r.speech_rating ?? "fair";
  return (
    <>
      <div className="metric-grid">
        <Metric label="Reverb time (mid)" value={r.rt60_mid_s ? r.rt60_mid_s.toFixed(2) : "—"} unit="s" />
        <Metric label="Speech clarity C50" value={r.c50_speech_db !== undefined ? r.c50_speech_db.toFixed(1) : "—"} unit="dB" />
        <Metric label="Schroeder frequency" value={r.schroeder_hz ? Math.round(r.schroeder_hz).toString() : "—"} unit="Hz" />
      </div>
      <Status
        tone={rating === "good" ? "ok" : rating === "fair" ? "warn" : "danger"}
        state={`Speech clarity ${rating}`}
        detail={
          rating === "good"
            ? "Sermons will be clear."
            : rating === "fair"
              ? "Keep vocal reverb short and the stage quiet."
              : "The room smears speech. Use little or no reverb on speech, aim the PA at the audience, not the walls."
        }
      />
      <section className="panel-card">
        <span className="section-title">Per octave · {current.label}</span>
        <table className="data-table">
          <thead>
            <tr>
              <th>Band</th>
              <th>RT60</th>
              <th>C50</th>
            </tr>
          </thead>
          <tbody>
            {Object.entries(r.bands ?? {}).map(([f, b]) => (
              <tr key={f}>
                <td className="mono">{Number(f) >= 1000 ? `${Number(f) / 1000}k` : f} Hz</td>
                <td className="mono">{b.rt60_s ? `${b.rt60_s.toFixed(2)} s` : "—"}</td>
                <td className="mono">{b.c50_db.toFixed(1)} dB</td>
              </tr>
            ))}
          </tbody>
        </table>
        <p className="hint">Enter the room volume before measuring to get the Schroeder frequency; use it as the EQ&apos;s room-mode limit.</p>
      </section>
    </>
  );
}

/* -------------------------------------------------------------- align -- */

function AlignStep({ items, setError }: { items: TuningMeasurement[]; setError: (e: string | null) => void }) {
  const timed = useMemo(() => items, [items]);
  const [mainId, setMainId] = useState("");
  const [subId, setSubId] = useState("");
  const [xo, setXo] = useState("");
  const [result, setResult] = useState<AlignResult | null>(null);

  return (
    <>
      <section className="panel-card">
        <span className="section-title">Sub alignment</span>
        <ol className="steps">
          <li>Turn &quot;Remove delay&quot; off. Route the chirp to one main speaker for every measurement (timing reference).</li>
          <li>Measure the mains alone, then the sub alone, from FOH.</li>
          <li>Pick both below. Apply the delay, re-measure, repeat.</li>
        </ol>
        <div className="inline-fields three">
          <label className="field">
            <span className="label">Mains</span>
            <select value={mainId} onChange={(e) => setMainId(e.target.value)}>
              <option value="">Choose…</option>
              {timed.map((m) => (
                <option key={m.id} value={m.id}>
                  {m.label}
                </option>
              ))}
            </select>
          </label>
          <label className="field">
            <span className="label">Sub</span>
            <select value={subId} onChange={(e) => setSubId(e.target.value)}>
              <option value="">Choose…</option>
              {timed.map((m) => (
                <option key={m.id} value={m.id}>
                  {m.label}
                </option>
              ))}
            </select>
          </label>
          <label className="field">
            <span className="label">Crossover (Hz, optional)</span>
            <input type="number" placeholder="auto" value={xo} onChange={(e) => setXo(e.target.value)} />
          </label>
        </div>
        <button
          className="btn-primary is-inline"
          type="button"
          disabled={!mainId || !subId || mainId === subId}
          onClick={() =>
            void align(mainId, subId, Number(xo) || undefined)
              .then(setResult)
              .catch((e: unknown) => setError(e instanceof Error ? e.message : "Alignment failed."))
          }
        >
          Calculate alignment
        </button>
      </section>
      {result ? (
        <>
          <div className="metric-grid">
            <Metric label="Crossover" value={Math.round(result.alignment.crossover_hz).toString()} unit="Hz" />
            <Metric label="Delay mains" value={result.alignment.delay_main_ms.toFixed(2)} unit="ms" />
            <Metric label="Delay sub" value={result.alignment.delay_sub_ms.toFixed(2)} unit="ms" />
            <Metric label="Sub level" value={`${result.levels.sub_gain_db > 0 ? "+" : ""}${result.levels.sub_gain_db.toFixed(1)}`} unit="dB" />
          </div>
          {result.alignment.consider_polarity_flip ? <Status tone="warn" state="Try flipping sub polarity" detail="The sources are nearly opposite in phase." /> : null}
          <p className="hint">{result.alignment.note}</p>
        </>
      ) : null}
    </>
  );
}

/* ------------------------------------------------------------- shared -- */

function NumberField({ label, value, onChange, min, max, step = 1 }: { label: string; value: number; onChange: (v: number) => void; min: number; max: number; step?: number }) {
  return (
    <label className="field">
      <span className="label">{label}</span>
      <input type="number" value={value} min={min} max={max} step={step} onChange={(e) => onChange(Math.min(max, Math.max(min, Number(e.target.value) || min)))} />
    </label>
  );
}

function Metric({ label, value, unit }: { label: string; value: string; unit: string }) {
  return (
    <div className="metric">
      <span className="label">{label}</span>
      <span className="value">
        {value}
        <small>{unit}</small>
      </span>
    </div>
  );
}
