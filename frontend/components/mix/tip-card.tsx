import type { Tip } from "@/lib/api";

const SEVERITY_LABEL: Record<Tip["severity"], string> = { info: "Info", warning: "Check", critical: "Fix" };

/** Problem → action → why. Every suggestion explains itself (WORSHIP_MIX.md ch. 6). */
export function TipCard({ tip }: { tip: Tip }) {
  return (
    <article className={`tip-card sev-${tip.severity}`}>
      <span className="label">
        {SEVERITY_LABEL[tip.severity]} · {tip.category}
      </span>
      <h3>{tip.problem}</h3>
      <p>{tip.action}</p>
      <p className="why">Why: {tip.why}</p>
    </article>
  );
}
