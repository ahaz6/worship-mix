"use client";

/**
 * Real-time pink noise analysis: RTA bars or live transfer function.
 * Rendering is throttled to ~10 fps; DSP runs on every audio chunk.
 */
import { useEffect, useRef, useState } from "react";

import { Status } from "@/components/common/status";
import { ResponsePlot, type Trace } from "@/components/tuning/response-plot";
import { type LiveInput, type PinkPlayer, loadPinkPeriod, playPinkNoise, startLiveInput } from "@/lib/live-input";
import { formatHz } from "@/lib/plot";
import { type Averaging, Rta, TransferAnalyzer, type TransferSnapshot } from "@/lib/rta";
import { type TuningMeasurement, importResponse } from "@/lib/tuning";

type Mode = "transfer" | "rta";

export function RealtimeView({ onSaved }: { onSaved: (m: TuningMeasurement) => void }) {
  const [mode, setMode] = useState<Mode>("transfer");
  const [avg, setAvg] = useState<Averaging>("slow");
  const [fraction, setFraction] = useState(3);
  const [running, setRunning] = useState(false);
  const [playing, setPlaying] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [rtaLevels, setRtaLevels] = useState<{ centers: number[]; levels: number[] } | null>(null);
  const [tf, setTf] = useState<TransferSnapshot | null>(null);
  const [frozen, setFrozen] = useState<TransferSnapshot | null>(null);
  const [saved, setSaved] = useState<string | null>(null);

  const input = useRef<LiveInput | null>(null);
  const player = useRef<PinkPlayer | null>(null);
  const rta = useRef<Rta | null>(null);
  const transfer = useRef<TransferAnalyzer | null>(null);
  const dirty = useRef(false);

  // propagate averaging changes into the running engines
  useEffect(() => {
    if (rta.current) rta.current.averaging = avg;
    if (transfer.current) transfer.current.averaging = avg;
    if (avg === "moving") {
      rta.current?.reset();
      transfer.current?.reset();
    }
  }, [avg]);

  // UI refresh loop (~10 fps)
  useEffect(() => {
    if (!running) return;
    const id = window.setInterval(() => {
      if (!dirty.current) return;
      dirty.current = false;
      if (mode === "rta" && rta.current) setRtaLevels({ centers: rta.current.centers, levels: rta.current.levels() });
      if (mode === "transfer" && transfer.current) setTf(transfer.current.snapshot(fraction === 3 ? 6 : fraction * 2));
    }, 100);
    return () => window.clearInterval(id);
  }, [running, mode, fraction]);

  useEffect(
    () => () => {
      void input.current?.stop();
      void player.current?.stop();
    },
    [],
  );

  const start = async () => {
    setError(null);
    try {
      if (mode === "transfer") {
        const ref = await loadPinkPeriod();
        transfer.current = new TransferAnalyzer(ref, 48000, avg);
      }
      input.current = await startLiveInput((s) => {
        if (mode === "rta") {
          if (!rta.current || rta.current.sampleRate !== (input.current?.sampleRate ?? 48000) || rta.current.fraction !== fraction) {
            rta.current = new Rta(input.current?.sampleRate ?? 48000, fraction, avg);
          }
          if (rta.current.push(s)) dirty.current = true;
        } else if (transfer.current?.push(s)) {
          dirty.current = true;
        }
      });
      if (input.current.sampleRate !== 48000 && mode === "transfer") {
        throw new Error("This device can't run the microphone at 48 kHz. Use RTA mode instead.");
      }
      setRunning(true);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not start.");
      await input.current?.stop();
      input.current = null;
    }
  };

  const stop = async () => {
    await input.current?.stop();
    input.current = null;
    setRunning(false);
  };

  const togglePink = async () => {
    try {
      if (player.current) {
        await player.current.stop();
        player.current = null;
        setPlaying(false);
      } else {
        player.current = await playPinkNoise();
        setPlaying(true);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Playback failed.");
    }
  };

  const save = async () => {
    if (!tf) return;
    try {
      const m = await importResponse(`Real time ${new Date().toLocaleTimeString()}`, tf.freqs, tf.magnitudeDb, tf.phaseDeg, tf.coherence);
      onSaved(m);
      setSaved(m.label);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Saving failed.");
    }
  };

  const meanCoh = tf ? tf.coherence.filter((_, i) => tf.freqs[i]! > 100 && tf.freqs[i]! < 10000).reduce((a, b, _, arr) => a + b / arr.length, 0) : 0;

  const traces: Trace[] = [];
  if (frozen) traces.push({ id: "frozen", label: "Frozen", tone: "reference", values: frozen.magnitudeDb });
  if (tf) traces.push({ id: "live", label: "Live", tone: "measured", values: tf.magnitudeDb });

  return (
    <>
      <section className="panel-card">
        <span className="section-title">Real-time analyzer</span>
        <ol className="steps">
          <li>
            Feed pink noise into the PA: tap <b>Play pink noise</b> on a laptop connected to the console, or loop the{" "}
            <a className="link" href="/api/tuning/pink-noise.wav" download>
              pink noise file
            </a>{" "}
            from any player. Start quietly, then raise to normal service level.
          </li>
          <li>Tap <b>Start listening</b> on the device with the mic. It can be a different device than the one playing.</li>
          <li>
            Use <b>Moving mic</b> and walk slowly through the seating area for 20–30 s, then <b>Save as measurement</b> and open Equalize.
          </li>
        </ol>
        <div className="btn-row">
          <button type="button" className={`btn${mode === "transfer" ? " is-active" : ""}`} disabled={running} onClick={() => setMode("transfer")}>
            Transfer function
          </button>
          <button type="button" className={`btn${mode === "rta" ? " is-active" : ""}`} disabled={running} onClick={() => setMode("rta")}>
            RTA bands
          </button>
          <span className="spacer" />
          {(["fast", "slow", "moving"] as const).map((a) => (
            <button key={a} type="button" className={`btn${avg === a ? " is-active" : ""}`} onClick={() => setAvg(a)}>
              {a === "fast" ? "Fast" : a === "slow" ? "Slow" : "Moving mic"}
            </button>
          ))}
          <select aria-label="Resolution" value={fraction} disabled={running} onChange={(e) => setFraction(Number(e.target.value))} className="compact">
            <option value={1}>1/1 oct</option>
            <option value={3}>1/3 oct</option>
            <option value={6}>1/6 oct</option>
            <option value={12}>1/12 oct</option>
          </select>
        </div>
        <div className="btn-row">
          <button type="button" className="btn-primary is-inline" onClick={() => void (running ? stop() : start())}>
            {running ? "Stop listening" : "Start listening"}
          </button>
          <button type="button" className={`btn${playing ? " is-active" : ""}`} onClick={() => void togglePink()}>
            {playing ? "Stop pink noise" : "Play pink noise"}
          </button>
          {mode === "transfer" ? (
            <>
              <button type="button" className="btn" disabled={!tf} onClick={() => setFrozen(tf)}>
                Freeze
              </button>
              <button type="button" className="btn" disabled={!tf || tf.periods < 4} onClick={() => void save()}>
                Save as measurement
              </button>
            </>
          ) : null}
        </div>
        {error ? <Status tone="danger" state="Problem" detail={error} /> : null}
        {saved ? <Status tone="ok" state="Saved" detail={`${saved} — open Equalize to correct it`} /> : null}
      </section>

      {mode === "transfer" && tf ? (
        <section className="panel-card">
          <div className="status-line">
            <Status
              tone={meanCoh > 0.85 ? "ok" : meanCoh > 0.6 ? "warn" : "danger"}
              state={meanCoh > 0.85 ? "Clean signal" : meanCoh > 0.6 ? "Some noise" : "Too noisy"}
              detail={`coherence ${(meanCoh * 100).toFixed(0)} %`}
            />
            <Status tone="info" state={`${tf.periods} periods`} detail={`delay ${tf.delayMs.toFixed(1)} ms (modulo 1.37 s)`} />
          </div>
          <ResponsePlot freqs={tf.freqs} traces={traces} ariaLabel="Live transfer function" />
          <CoherenceStrip freqs={tf.freqs} coherence={tf.coherence} />
          <p className="hint">Gaps = coherence below 50 % (noise, people talking, reverb). Raise the level or wait for more periods.</p>
        </section>
      ) : null}

      {mode === "rta" && rtaLevels ? (
        <section className="panel-card">
          <span className="section-title">RTA · {fraction === 1 ? "1/1" : `1/${fraction}`} octave · dBFS</span>
          <RtaBars centers={rtaLevels.centers} levels={rtaLevels.levels} />
          <p className="hint">With pink noise, a level line across all bands means a flat system. RTA shows the signal only — no phase or timing.</p>
        </section>
      ) : null}
    </>
  );
}

function RtaBars({ centers, levels }: { centers: number[]; levels: number[] }) {
  const max = Math.max(...levels);
  const floor = max - 48;
  return (
    <div className="rta" role="img" aria-label="RTA band levels">
      {centers.map((c, i) => {
        const h = Math.max(0, Math.min(1, (levels[i]! - floor) / (max - floor)));
        return (
          <div key={c} className="rta-band" title={`${Math.round(c)} Hz ${levels[i]!.toFixed(1)} dBFS`}>
            <div className="rta-track">
              <div className="rta-fill" style={{ height: `${h * 100}%` }} />
            </div>
            <span className="geq-label">{centers.length > 40 && i % 3 ? "" : formatHz(c)}</span>
          </div>
        );
      })}
    </div>
  );
}

function CoherenceStrip({ freqs, coherence }: { freqs: number[]; coherence: number[] }) {
  return (
    <div className="coh-strip" aria-label="Coherence across frequency">
      {freqs.map((f, i) => (
        <span key={f} style={{ opacity: 0.15 + 0.85 * coherence[i]!, background: coherence[i]! > 0.85 ? "var(--wm-success)" : coherence[i]! > 0.5 ? "var(--wm-warning)" : "var(--wm-danger)" }} />
      ))}
    </div>
  );
}
