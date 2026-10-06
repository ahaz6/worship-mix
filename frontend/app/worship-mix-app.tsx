"use client";

/**
 * Worship Mix host screen.
 *
 * Three-area shell from the Worship Suite (Design-Art.md 7.1):
 *   left rail  — brand + module navigation (instead of Worship Keys' setlist)
 *   stage      — the active module's main workspace
 *   right rail — console connection, live guard and safety controls
 *
 * UI copy is English across the suite (Design-Art.md 12).
 */

import { useCallback, useState } from "react";

import { BrandMark } from "@/components/brand/brand-mark";
import { Status } from "@/components/common/status";
import { FeedbackAlert } from "@/components/mix/feedback-alert";
import { LevelMeter } from "@/components/mix/level-meter";
import { TipCard } from "@/components/mix/tip-card";
import { RoomTuningView } from "@/components/tuning/room-tuning-view";
import { type Analysis, analyzeFile } from "@/lib/api";
import { formatDb } from "@/lib/meter";

type ModuleId = "analyzer" | "mastering" | "soundcheck" | "live" | "scenes" | "tuning";

const MODULES: { id: ModuleId; title: string; hint: string; action: string; state: "ready" | "planned" }[] = [
  { id: "analyzer", title: "Mix Analyzer", hint: "Measure and coach", action: "Analyze a mix", state: "ready" },
  { id: "mastering", title: "Mastering", hint: "Match a reference", action: "Master a track", state: "planned" },
  { id: "soundcheck", title: "Soundcheck", hint: "Channel suggestions", action: "Load a soundcheck", state: "planned" },
  { id: "live", title: "Live Guard", hint: "Feedback and levels", action: "Start listening", state: "planned" },
  { id: "scenes", title: "Scenes", hint: "Lineup to start scene", action: "Describe the band", state: "planned" },
  { id: "tuning", title: "Room Tuning", hint: "Measure and correct the PA", action: "Measure a seat", state: "ready" },
];

const TARGETS = [
  { id: "spotify", label: "Spotify · −14 LUFS", lufs: -14 },
  { id: "apple", label: "Apple Music · −16 LUFS", lufs: -16 },
  { id: "stream", label: "Livestream · −23 LUFS", lufs: -23 },
  { id: "loud", label: "Worship release · −10 LUFS", lufs: -10 },
];

export function WorshipMixApp() {
  const [active, setActive] = useState<ModuleId>("analyzer");
  const [feedbackHz, setFeedbackHz] = useState<number | null>(null);
  const current = MODULES.find((m) => m.id === active) ?? MODULES[0]!;

  return (
    <div className="app-shell">
      <aside className="rail rail-left" aria-label="Modules">
        <BrandMark />
        <nav className="module-nav">
          <span className="section-title">Modules</span>
          {MODULES.map((m, i) => (
            <button
              key={m.id}
              type="button"
              className={`nav-item${m.id === active ? " is-active" : ""}`}
              aria-current={m.id === active ? "page" : undefined}
              onClick={() => setActive(m.id)}
            >
              <span className="num">{String(i + 1).padStart(2, "0")}</span>
              <span>
                {m.title}
                <small>{m.state === "ready" ? m.hint : `${m.hint} · planned`}</small>
              </span>
            </button>
          ))}
        </nav>
      </aside>

      <main className="stage">
        <header className="stage-head">
          <div>
            <span className="label">Worship Mix · {current.hint}</span>
            <h1>{current.title}</h1>
          </div>
        </header>
        <div className="stage-body">
          {active === "analyzer" ? (
            <AnalyzerView />
          ) : active === "tuning" ? (
            <RoomTuningView />
          ) : (
            <PlannedView title={current.title} action={current.action} />
          )}
        </div>
      </main>

      <aside className="rail rail-right" aria-label="Console and safety">
        <section className="panel-card">
          <span className="section-title">Console</span>
          <Status tone="idle" state="Not connected" detail="Mock console available" />
          <div className="inline-fields">
            <select aria-label="Console type" defaultValue="mock">
              <option value="mock">Mock console</option>
              <option value="allen-heath-sq">Allen &amp; Heath SQ</option>
              <option value="behringer-x32">Behringer X32 / M32</option>
            </select>
            <input type="text" aria-label="Console IP address" placeholder="192.168.1.70" />
          </div>
          <div className="btn-row">
            <button className="btn" type="button">
              Connect
            </button>
            <button className="btn tone-quiet" type="button" disabled>
              Allow writes
            </button>
          </div>
          <p className="hint">Read-only by default. Every write takes a snapshot first and can be undone.</p>
        </section>

        <section className="panel-card">
          <span className="section-title">Live guard</span>
          <Status tone="idle" state="Stopped" />
          <button className="btn" type="button" onClick={() => setFeedbackHz(2512)}>
            Preview feedback alert
          </button>
          <button className="btn tone-kill" type="button" onClick={() => setFeedbackHz(null)}>
            Stop all automation
          </button>
        </section>
      </aside>

      {feedbackHz !== null ? <FeedbackAlert freqHz={feedbackHz} onDismiss={() => setFeedbackHz(null)} /> : null}
    </div>
  );
}

function AnalyzerView() {
  const [target, setTarget] = useState(TARGETS[0]!);
  const [result, setResult] = useState<Analysis | null>(null);
  const [fileName, setFileName] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [over, setOver] = useState(false);

  const run = useCallback(
    async (file: File) => {
      setBusy(true);
      setError(null);
      setFileName(file.name);
      try {
        setResult(await analyzeFile(file, target.lufs));
      } catch (e) {
        setError(e instanceof Error ? e.message : "Analysis failed.");
      } finally {
        setBusy(false);
      }
    },
    [target.lufs],
  );

  const m = result?.metrics;

  return (
    <>
      <div className="inline-fields">
        <label className="field">
          <span className="label">Loudness target</span>
          <select value={target.id} onChange={(e) => setTarget(TARGETS.find((t) => t.id === e.target.value) ?? TARGETS[0]!)}>
            {TARGETS.map((t) => (
              <option key={t.id} value={t.id}>
                {t.label}
              </option>
            ))}
          </select>
        </label>
      </div>

      <label
        className={`dropzone${over ? " is-over" : ""}`}
        onDragOver={(e) => {
          e.preventDefault();
          setOver(true);
        }}
        onDragLeave={() => setOver(false)}
        onDrop={(e) => {
          e.preventDefault();
          setOver(false);
          const f = e.dataTransfer.files[0];
          if (f) void run(f);
        }}
      >
        <strong>{busy ? "Analyzing…" : "Drop a mix here"}</strong>
        <span className="meta">WAV, FLAC or AIFF · stereo mix or a single stem</span>
        <input
          className="visually-hidden"
          type="file"
          accept="audio/*"
          onChange={(e) => {
            const f = e.target.files?.[0];
            if (f) void run(f);
          }}
        />
        <span className="btn">Choose file</span>
      </label>

      {error ? <Status tone="danger" state="Analysis failed" detail={error} /> : null}

      {m ? (
        <>
          <Status tone="ok" state="Analyzed" detail={fileName} />
          <div className="metric-grid">
            <Metric label="Integrated" value={formatDb(m.integrated_lufs)} unit="LUFS" />
            <Metric label="True peak" value={formatDb(m.true_peak_db)} unit="dBTP" />
            <Metric label="Peak to loudness" value={formatDb(m.plr_db)} unit="dB" />
            <Metric label="Stereo correlation" value={m.stereo_correlation === null ? "—" : m.stereo_correlation.toFixed(2)} unit="" />
          </div>
          <section className="panel-card">
            <span className="section-title">Loudness</span>
            <LevelMeter label="Integrated loudness" db={m.integrated_lufs} targetDb={target.lufs} unit="LUFS" />
            <LevelMeter label="True peak" db={m.true_peak_db} targetDb={-1} unit="dBTP" />
          </section>
          <section>
            <span className="section-title">Coach · {result.tips.length} suggestions</span>
            <div className="tip-list">
              {result.tips.length === 0 ? <p className="hint">No issues found for this target.</p> : null}
              {result.tips.map((t) => (
                <TipCard key={t.id} tip={t} />
              ))}
            </div>
          </section>
        </>
      ) : null}
    </>
  );
}

function Metric({ label, value, unit }: { label: string; value: string; unit: string }) {
  return (
    <div className="metric">
      <span className="label">{label}</span>
      <span className="value">
        {value}
        {unit ? <small>{unit}</small> : null}
      </span>
    </div>
  );
}

function PlannedView({ title, action }: { title: string; action: string }) {
  return (
    <section className="panel-card">
      <Status tone="info" state="Planned" detail={`${title} arrives in a later milestone`} />
      <button className="btn-primary" type="button" disabled>
        {action}
      </button>
      <p className="hint">See WORSHIP_MIX.md for the full specification of this module.</p>
    </section>
  );
}
