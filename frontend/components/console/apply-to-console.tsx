"use client";

/**
 * "Send to console" with a review step.
 * - X32 / practice console: shows the values, sends them (ramped), offers Undo.
 * - SQ or no console: a big checklist of manual steps (nothing is sent).
 */
import { useState } from "react";
import { createPortal } from "react-dom";

import { Status } from "@/components/common/status";
import { useConsole } from "@/components/console/console-context";
import { type ConsoleChange, type ConsolePlan, applyChanges, describeChange, planChanges, undoChanges } from "@/lib/console";

export function ApplyToConsole({ changes, label = "Send to console" }: { changes: ConsoleChange[]; label?: string }) {
  const { session } = useConsole();
  const [open, setOpen] = useState(false);
  const [plan, setPlan] = useState<ConsolePlan | null>(null);
  const [done, setDone] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [checked, setChecked] = useState<Set<number>>(new Set());

  const openModal = () => {
    setOpen(true);
    setDone(null);
    setError(null);
    setChecked(new Set());
    if (!session) {
      setPlan({ mode: "manual", steps: changes.map(describeChange), messages: [] });
      return;
    }
    setPlan(null);
    planChanges(session.session, changes)
      .then(setPlan)
      .catch((e: unknown) => setError(e instanceof Error ? e.message : "Planning failed."));
  };

  const send = async () => {
    if (!session) return;
    try {
      const r = await applyChanges(session.session, changes);
      setDone(`Sent ${r.applied ?? 0} values. Listen, then keep or undo.`);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Sending failed.");
    }
  };

  const undo = async () => {
    if (!session) return;
    try {
      const r = await undoChanges(session.session);
      setDone(`Restored ${r.restored} values.`);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Undo failed.");
    }
  };

  if (!changes.length) return null;
  const manual = plan?.mode === "manual";

  return (
    <>
      <button type="button" className="btn" onClick={openModal}>
        {label}
      </button>
      {open
        ? createPortal(
        <div className="modal-backdrop" role="presentation" onClick={() => setOpen(false)}>
          <div className="modal is-wide" role="dialog" aria-modal="true" aria-label={label} onClick={(e) => e.stopPropagation()}>
            <button type="button" className="modal-close" aria-label="Close" onClick={() => setOpen(false)}>
              ×
            </button>
            <span className="label">{manual ? "Manual steps" : "Review before sending"}</span>
            <h2>{manual ? "Set these on your console" : `${changes.length} changes`}</h2>
            {manual ? (
              <p className="hint">
                {session ? "This console doesn't accept processing changes over the network." : "No console connected."} Tick each step when done.
              </p>
            ) : null}
            <ol className="step-list">
              {(plan?.steps ?? []).map((s, i) => (
                <li key={i} className={checked.has(i) ? "is-done" : ""}>
                  {manual ? (
                    <label className="check">
                      <input
                        type="checkbox"
                        checked={checked.has(i)}
                        onChange={() =>
                          setChecked((c) => {
                            const n = new Set(c);
                            if (n.has(i)) n.delete(i);
                            else n.add(i);
                            return n;
                          })
                        }
                      />
                      {s}
                    </label>
                  ) : (
                    s
                  )}
                </li>
              ))}
            </ol>
            {plan?.manual_steps?.length ? <Status tone="info" state="Some steps stay manual" detail={plan.manual_steps.join(" · ")} /> : null}
            {error ? <Status tone="danger" state="Problem" detail={error} /> : null}
            {done ? <Status tone="ok" state="Done" detail={done} /> : null}
            <div className="modal-actions">
              {manual ? (
                <button type="button" className="btn" onClick={() => setOpen(false)}>
                  {checked.size === (plan?.steps.length ?? 0) ? "All done" : "Close"}
                </button>
              ) : (
                <>
                  <button type="button" className="btn tone-quiet" onClick={() => void undo()}>
                    Undo last send
                  </button>
                  <button type="button" className="btn-primary is-inline" disabled={!session?.write_enabled} onClick={() => void send()}>
                    {session?.write_enabled ? "Send now" : "Allow writes first"}
                  </button>
                </>
              )}
            </div>
          </div>
        </div>,
            document.body,
          )
        : null}
    </>
  );
}
