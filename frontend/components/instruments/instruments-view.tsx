"use client";

/**
 * Module 03 — Instruments: tune every channel and the whole mix.
 *
 * 1. Source: demo band · upload soundcheck · live from console USB
 * 2. Channels: name → instrument (auto-guessed) → console channel
 * 3. Results: per channel (gain, HPF, EQ, gate, comp, de-esser, FX, pan, tips)
 *             and the mix (start faders, masking, sidechains, master bus)
 */
import { useCallback, useEffect, useState } from "react";

import { Status } from "@/components/common/status";
import { ApplyToConsole } from "@/components/console/apply-to-console";
import {
  type ChannelResult,
  type InstrumentProfile,
  type InstrumentResult,
  type MapRow,
  analyzeUpload,
  fetchDevices,
  fetchProfiles,
  guessProfile,
  latestLive,
  runDemo,
  startLive,
  stopLive,
} from "@/lib/instruments";
import { wavChannels } from "@/lib/wavinfo";

type Source = "demo" | "upload" | "live";

export function InstrumentsView() {
  const [profiles, setProfiles] = useState<InstrumentProfile[]>([]);
  const [source, setSource] = useState<Source | null>(null);
  const [rows, setRows] = useState<MapRow[]>([]);
  const [files, setFiles] = useState<File[]>([]);
  const [devices, setDevices] = useState<{ index: number; name: string; inputs: number }[]>([]);
  const [device, setDevice] = useState<number | null>(null);
  const [rt60, setRt60] = useState("");
  const [bpm, setBpm] = useState("");
  const [result, setResult] = useState<InstrumentResult | null>(null);
  const [busy, setBusy] = useState(false);
  const [live, setLive] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [view, setView] = useState<"channels" | "mix">("channels");
  const [selected, setSelected] = useState(0);

  useEffect(() => {
    fetchProfiles()
      .then(setProfiles)
      .catch(() => setError("Could not reach the Worship Mix backend. Is it running?"));
  }, []);

  // live polling
  useEffect(() => {
    if (!live) return;
    const id = window.setInterval(() => {
      latestLive()
        .then((r) => {
          if (r.channels?.length) setResult(r as InstrumentResult);
          if (r.error) setError(r.error);
        })
        .catch(() => undefined);
    }, 2000);
    return () => window.clearInterval(id);
  }, [live]);

  const num = (v: string) => (Number(v) > 0 ? Number(v) : undefined);

  const run = useCallback(
    async (fn: () => Promise<InstrumentResult>) => {
      setBusy(true);
      setError(null);
      try {
        const r = await fn();
        setResult(r);
        setSelected(0);
      } catch (e) {
        setError(e instanceof Error ? e.message : "Analysis failed.");
      } finally {
        setBusy(false);
      }
    },
    [],
  );

  const pickFiles = async (list: FileList | null) => {
    if (!list?.length) return;
    const fs = Array.from(list);
    setFiles(fs);
    if (fs.length === 1) {
      const info = await wavChannels(fs[0]!);
      const n = info?.channels ?? 1;
      setRows(Array.from({ length: n }, (_, i) => ({ input_index: i, name: `Ch ${i + 1}`, profile: "keys", console_channel: i + 1 })));
    } else {
      setRows(
        fs.map((f, i) => {
          const name = f.name.replace(/\.[^.]+$/, "");
          return { input_index: i, name, profile: guessProfile(name), console_channel: i + 1 };
        }),
      );
    }
  };

  const chooseLive = async () => {
    setSource("live");
    try {
      const d = await fetchDevices();
      setDevices(d);
      if (d[0]) {
        setDevice(d[0].index);
        setRows(Array.from({ length: Math.min(d[0].inputs, 32) }, (_, i) => ({ input_index: i, name: `Ch ${i + 1}`, profile: "keys", console_channel: i + 1 })));
      }
    } catch {
      setDevices([]);
    }
  };

  const toggleLive = async () => {
    if (live) {
      await stopLive();
      setLive(false);
      return;
    }
    setError(null);
    try {
      await startLive(device, rows.filter((r) => r.profile !== "off"), num(rt60), num(bpm));
      setLive(true);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not start live input.");
    }
  };

  return (
    <>
      {/* ------------------------------------------------------ 1. source -- */}
      <section className="panel-card">
        <span className="section-title">1 · Choose your audio</span>
        <div className="choice-grid">
          <button type="button" className={`choice${source === "demo" ? " is-active" : ""}`} onClick={() => { setSource("demo"); void run(runDemo); }}>
            <b>Try the demo band</b>
            <span>8 channels with typical problems. No hardware needed.</span>
          </button>
          <label className={`choice${source === "upload" ? " is-active" : ""}`}>
            <b>Upload a soundcheck</b>
            <span>One multitrack WAV from the console USB, or one file per channel.</span>
            <input className="visually-hidden" type="file" accept=".wav,audio/wav" multiple onChange={(e) => { setSource("upload"); void pickFiles(e.target.files); }} />
          </label>
          <button type="button" className={`choice${source === "live" ? " is-active" : ""}`} onClick={() => void chooseLive()}>
            <b>Live from the console</b>
            <span>Console USB into this laptop. Updates every 3 seconds while the band plays.</span>
          </button>
        </div>
        <div className="inline-fields">
          <label className="field">
            <span className="label">Room reverb RT60 (s, optional)</span>
            <input type="number" step={0.1} placeholder="from Room Tuning, e.g. 1.6" value={rt60} onChange={(e) => setRt60(e.target.value)} />
          </label>
          <label className="field">
            <span className="label">Song tempo BPM (optional)</span>
            <input type="number" placeholder="for delay times, e.g. 72" value={bpm} onChange={(e) => setBpm(e.target.value)} />
          </label>
        </div>
      </section>

      {/* ---------------------------------------------------- 2. channels -- */}
      {(source === "upload" || source === "live") && (rows.length || source === "live") ? (
        <section className="panel-card">
          <span className="section-title">2 · Tell us what is on each channel</span>
          {source === "live" ? (
            devices.length ? (
              <label className="field">
                <span className="label">Audio input (console USB)</span>
                <select value={device ?? ""} onChange={(e) => setDevice(Number(e.target.value))}>
                  {devices.map((d) => (
                    <option key={d.index} value={d.index}>
                      {d.name} · {d.inputs} inputs
                    </option>
                  ))}
                </select>
              </label>
            ) : (
              <Status tone="warn" state="No audio input found" detail="Run the backend on the laptop connected to the console USB, or upload a recording." />
            )
          ) : null}
          <div className="map-table" role="table" aria-label="Channel mapping">
            <div className="map-row head" role="row">
              <span>In</span>
              <span>Name</span>
              <span>Instrument</span>
              <span>Console ch</span>
            </div>
            {rows.map((r, i) => (
              <div key={i} className="map-row" role="row">
                <span className="mono">{r.input_index + 1}</span>
                <input
                  type="text"
                  aria-label={`Name of input ${r.input_index + 1}`}
                  value={r.name}
                  onChange={(e) => {
                    const name = e.target.value;
                    setRows((rs) => rs.map((x, j) => (j === i ? { ...x, name, profile: guessProfile(name) } : x)));
                  }}
                />
                <select aria-label={`Instrument on input ${r.input_index + 1}`} value={r.profile} onChange={(e) => setRows((rs) => rs.map((x, j) => (j === i ? { ...x, profile: e.target.value } : x)))}>
                  <option value="off">— not used —</option>
                  {profiles.map((p) => (
                    <option key={p.key} value={p.key}>
                      {p.label}
                    </option>
                  ))}
                </select>
                <input
                  type="number"
                  aria-label={`Console channel for input ${r.input_index + 1}`}
                  value={r.console_channel ?? ""}
                  onChange={(e) => setRows((rs) => rs.map((x, j) => (j === i ? { ...x, console_channel: Number(e.target.value) || null } : x)))}
                />
              </div>
            ))}
          </div>
          <p className="hint">Typing a name like &quot;Kick&quot;, &quot;Snare&quot;, &quot;Bass DI&quot; or &quot;Lead Vox&quot; picks the instrument for you.</p>
          {source === "upload" ? (
            <button
              type="button"
              className="btn-primary is-inline"
              disabled={busy}
              onClick={() => void run(() => analyzeUpload(files, rows.filter((r) => r.profile !== "off"), num(rt60), num(bpm)))}
            >
              {busy ? "Analyzing…" : "Analyze"}
            </button>
          ) : (
            <button type="button" className="btn-primary is-inline" disabled={!devices.length} onClick={() => void toggleLive()}>
              {live ? "Stop live analysis" : "Start live analysis"}
            </button>
          )}
        </section>
      ) : null}

      {busy && source === "demo" ? <Status tone="info" state="Analyzing the demo band…" /> : null}
      {error ? <Status tone="danger" state="Problem" detail={error} /> : null}
      {live ? <Status tone="active" state="Live" detail={result ? "updating every 3 s" : "waiting for audio…"} /> : null}

      {/* ----------------------------------------------------- 3. results -- */}
      {result?.channels.length ? (
        <>
          <div className="tab-row" role="tablist">
            <button type="button" role="tab" aria-selected={view === "channels"} className={`btn${view === "channels" ? " is-active" : ""}`} onClick={() => setView("channels")}>
              3 · Channels
            </button>
            <button type="button" role="tab" aria-selected={view === "mix"} className={`btn${view === "mix" ? " is-active" : ""}`} onClick={() => setView("mix")}>
              4 · Whole mix
            </button>
            <span className="spacer" />
            <ApplyToConsole changes={result.channels.flatMap((c) => c.changes)} label="Send all channels to console" />
          </div>
          {view === "channels" ? (
            <div className="channel-layout">
              <ul className="channel-list" aria-label="Channels">
                {result.channels.map((c, i) => {
                  const crit = c.notes.filter((n) => n.severity !== "info").length;
                  return (
                    <li key={c.name}>
                      <button type="button" className={`channel-chip${i === selected ? " is-active" : ""}`} onClick={() => setSelected(i)}>
                        <span>
                          {c.name}
                          <small>{c.label}</small>
                        </span>
                        <span className={`badge ${crit ? "warn" : "ok"}`}>{crit ? `${crit} to fix` : "OK"}</span>
                      </button>
                    </li>
                  );
                })}
              </ul>
              {result.channels[selected] ? <ChannelDetail c={result.channels[selected]!} profiles={profiles} /> : null}
            </div>
          ) : result.mix ? (
            <MixDetail result={result} />
          ) : null}
        </>
      ) : null}
    </>
  );
}

/* --------------------------------------------------------- channel card -- */

function ChannelDetail({ c, profiles }: { c: ChannelResult; profiles: InstrumentProfile[] }) {
  const s = c.settings;
  const tips = profiles.find((p) => p.key === c.profile)?.tips ?? [];
  const sign = (v: number) => `${v > 0 ? "+" : ""}${v.toFixed(1)}`;
  return (
    <section className="panel-card channel-detail">
      <div className="section-title">
        <span>
          {c.name} · {c.label}
          {c.console_channel ? ` · console ch ${c.console_channel}` : ""}
        </span>
        <ApplyToConsole changes={c.changes} label="Send to console" />
      </div>

      <div className="setting-grid">
        <Setting title="Gain" tone={s.gain.ok ? "ok" : "warn"} value={s.gain.ok ? "OK" : `${sign(s.gain.trim_db)} dB`} detail={`peaks ${c.metrics.peak_dbfs.toFixed(0)} dBFS · target −12`} />
        <Setting title="High-pass" value={`${Math.round(s.hpf.freq)} Hz`} detail={s.lpf ? `low-pass ${Math.round(s.lpf.freq / 1000)} kHz` : "low-pass off"} />
        <Setting
          title="Gate"
          value={s.gate ? `${Math.round(s.gate.threshold_db)} dB` : "Off"}
          detail={s.gate ? `range ${s.gate.range_db} · att ${s.gate.attack_ms} · hold ${s.gate.hold_ms} · rel ${s.gate.release_ms} ms` : "not needed"}
        />
        <Setting
          title="Compressor"
          value={s.comp ? `${s.comp.ratio}:1` : "Off"}
          detail={s.comp ? `thr ${Math.round(s.comp.threshold_db)} dB · att ${s.comp.attack_ms} · rel ${s.comp.release_ms} ms · +${s.comp.makeup_db} dB` : "not needed"}
        />
        <Setting title="De-esser" value={s.deesser ? `${(s.deesser.freq / 1000).toFixed(1)} kHz` : "Off"} detail={s.deesser ? `−${s.deesser.reduction_db} dB` : "not needed"} />
        <Setting
          title="Effects"
          value={s.fx.reverb === "none" ? "Dry" : `${s.fx.reverb} reverb`}
          detail={`${s.fx.reverb_time_s ? `${s.fx.reverb_time_s} s` : ""}${s.fx.delay_ms ? ` · delay ${s.fx.delay_ms} ms` : s.fx.delay_note ? ` · ${s.fx.delay_note}` : ""} · pan ${s.pan}`}
        />
      </div>

      <span className="section-title">EQ</span>
      {s.eq.length ? (
        <table className="data-table">
          <thead>
            <tr>
              <th>Band</th>
              <th>Type</th>
              <th>Freq</th>
              <th>Gain</th>
              <th>Q</th>
              <th>Why</th>
            </tr>
          </thead>
          <tbody>
            {s.eq.map((b, i) => (
              <tr key={i}>
                <td>{i + 1}</td>
                <td>{b.type.replace("_", " ")}</td>
                <td className="mono">{Math.round(b.freq)} Hz</td>
                <td className="mono">{sign(b.gain_db)} dB</td>
                <td className="mono">{b.q.toFixed(1)}</td>
                <td>{b.why}</td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : (
        <p className="hint">Sounds balanced — no EQ needed beyond the high-pass.</p>
      )}

      {c.notes.length ? (
        <div className="tip-list">
          {c.notes.map((n, i) => (
            <article key={i} className={`tip-card sev-${n.severity}`}>
              <h3>{n.problem}</h3>
              <p>{n.action}</p>
              <p className="why">Why: {n.why}</p>
            </article>
          ))}
        </div>
      ) : null}
      {tips.length ? (
        <ul className="steps">
          {tips.map((t) => (
            <li key={t}>{t}</li>
          ))}
        </ul>
      ) : null}
    </section>
  );
}

function Setting({ title, value, detail, tone }: { title: string; value: string; detail: string; tone?: "ok" | "warn" }) {
  return (
    <div className={`metric setting${tone === "warn" ? " is-warn" : ""}`}>
      <span className="label">{title}</span>
      <span className="value">{value}</span>
      <span className="hint">{detail}</span>
    </div>
  );
}

/* ------------------------------------------------------------- mix card -- */

function MixDetail({ result }: { result: InstrumentResult }) {
  const mix = result.mix!;
  return (
    <>
      <section className="panel-card">
        <span className="section-title">Start fader positions · {mix.reference} at 0 dB</span>
        <div className="fader-row">
          {mix.balance.map((b) => (
            <div key={b.channel} className="fader" title={`${b.name}: ${b.fader_db} dB`}>
              <div className="fader-track">
                <div className="fader-cap" style={{ bottom: `${Math.max(0, Math.min(100, ((b.fader_db + 40) / 50) * 100))}%` }} />
              </div>
              <span className="mono">{b.fader_db > 0 ? "+" : ""}{b.fader_db.toFixed(0)}</span>
              <span className="fader-name">{b.name}</span>
            </div>
          ))}
        </div>
        <p className="hint">Start here, then mix by ear. Pre-fader recordings can&apos;t know your current fader positions.</p>
      </section>

      <section className="panel-card">
        <span className="section-title">Frequency conflicts</span>
        {mix.conflicts.length ? (
          <ul className="conflict-list">
            {mix.conflicts.slice(0, 8).map((c, i) => (
              <li key={i}>
                <span className="mono">{c.band_hz >= 1000 ? `${c.band_hz / 1000}k` : c.band_hz} Hz</span>
                <span>
                  <b>{c.keep_name}</b> vs {c.give_name}
                  <small>{c.action}</small>
                </span>
              </li>
            ))}
          </ul>
        ) : (
          <p className="hint">No strong conflicts — every instrument has its space.</p>
        )}
      </section>

      <section className="panel-card">
        <div className="section-title">
          <span>Sidechain &amp; ducking</span>
          <ApplyToConsole changes={mix.sidechain_changes} label="Send sidechains" />
        </div>
        {mix.sidechains.length ? (
          <div className="tip-list">
            {mix.sidechains.map((s, i) => (
              <article key={i} className="tip-card sev-info">
                <span className="label">
                  {s.key} → {s.target}
                </span>
                <h3>
                  {s.settings.type === "dynamic_eq"
                    ? `Dynamic EQ on ${s.target}: −${String(s.settings.max_cut_db)} dB at ${String(s.settings.freq)} Hz while ${s.key} is active`
                    : `Compress ${s.target} from ${s.key}: ${String(s.settings.ratio)}:1, ${String(s.settings.attack_ms)} ms attack, ${String(s.settings.release_ms)} ms release, ~${String(s.settings.gr_db)} dB`}
                </h3>
                <p className="why">{s.why}</p>
              </article>
            ))}
          </div>
        ) : (
          <p className="hint">No ducking needed for this lineup.</p>
        )}
      </section>

      <section className="panel-card">
        <span className="section-title">Master bus</span>
        <div className="setting-grid">
          <Setting title="Mix loudness" value={`${mix.master.lufs.toFixed(0)} LUFS`} detail={`peak ${mix.master.peak_dbfs.toFixed(0)} dBFS · PLR ${mix.master.plr_db.toFixed(0)} dB`} />
          <Setting
            title="Bus compressor"
            value={`${mix.master.bus_comp.ratio}:1`}
            detail={`thr ${mix.master.bus_comp.threshold_db} dB · att ${mix.master.bus_comp.attack_ms} · rel ${mix.master.bus_comp.release_ms} ms · ${mix.master.bus_comp.gr_db} dB GR`}
          />
          <Setting title="Limiter" value={`${mix.master.limiter.ceiling_dbtp} dBTP`} detail={mix.master.limiter.why} />
          <Setting title="Livestream bus" value={`${mix.master.stream.target_lufs} LUFS`} detail={mix.master.stream.why} />
        </div>
        {mix.master.eq.length ? (
          <p className="meta">
            Master EQ (broad, max ±2 dB): {mix.master.eq.map((e) => `${e.freq >= 1000 ? `${e.freq / 1000}k` : e.freq} Hz ${e.gain_db > 0 ? "+" : ""}${e.gain_db} dB`).join(" · ")}
          </p>
        ) : null}
        <p className="hint">{mix.master.bus_comp.why}</p>
      </section>
    </>
  );
}
