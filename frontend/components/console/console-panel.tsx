"use client";

import { useState } from "react";

import { Status } from "@/components/common/status";
import { useConsole } from "@/components/console/console-context";

const KINDS = [
  { id: "mock", label: "Practice console (no hardware)", ip: false },
  { id: "behringer-x32", label: "Behringer X32 / Midas M32", ip: true },
  { id: "allen-heath-sq", label: "Allen & Heath SQ", ip: true },
];

/** Right-rail console card: connect, allow writes. Read-only by default. */
export function ConsolePanel() {
  const { session, busy, error, connect, disconnect, allowWrites } = useConsole();
  const [kind, setKind] = useState("mock");
  const [host, setHost] = useState("");
  const needsIp = KINDS.find((k) => k.id === kind)?.ip ?? false;

  return (
    <section className="panel-card">
      <span className="section-title">Console</span>
      {session ? (
        <>
          <Status
            tone={session.connected ? (session.write_enabled ? "warn" : "ok") : "danger"}
            state={session.connected ? (session.write_enabled ? "Connected · writing allowed" : "Connected · read only") : "No answer"}
            detail={KINDS.find((k) => k.id === session.kind)?.label}
          />
          {session.note ? <p className="hint">{session.note}</p> : null}
          {session.writes_processing ? (
            <label className="check">
              <input type="checkbox" checked={session.write_enabled} onChange={(e) => void allowWrites(e.target.checked)} />
              Allow writes
            </label>
          ) : null}
          <button className="btn tone-quiet" type="button" onClick={disconnect}>
            Disconnect
          </button>
        </>
      ) : (
        <>
          <Status tone="idle" state="Not connected" detail="Settings are shown as steps" />
          <select aria-label="Console type" value={kind} onChange={(e) => setKind(e.target.value)}>
            {KINDS.map((k) => (
              <option key={k.id} value={k.id}>
                {k.label}
              </option>
            ))}
          </select>
          {needsIp ? <input type="text" aria-label="Console IP address" placeholder="Console IP, e.g. 192.168.1.70" value={host} onChange={(e) => setHost(e.target.value)} /> : null}
          <button className="btn" type="button" disabled={busy || (needsIp && !host)} onClick={() => void connect(kind, needsIp ? host : "127.0.0.1")}>
            {busy ? "Connecting…" : "Connect"}
          </button>
          {error ? <Status tone="danger" state="Problem" detail={error} /> : null}
        </>
      )}
      <p className="hint">Read-only until you allow writes. Every change is saved first and can be undone.</p>
    </section>
  );
}
