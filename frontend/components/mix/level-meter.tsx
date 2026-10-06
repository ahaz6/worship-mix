import { dbToMeter, formatDb } from "@/lib/meter";

export function LevelMeter({ label, db, targetDb, unit = "dB" }: { label: string; db: number | null; targetDb?: number; unit?: string }) {
  const pos = db === null ? 0 : dbToMeter(db);
  return (
    <div className="level-meter" role="meter" aria-label={label} aria-valuemin={-60} aria-valuemax={0} aria-valuenow={db ?? -60}>
      <div className="field-head">
        <b>{label}</b>
        <span className="value">
          {formatDb(db)} {unit}
        </span>
      </div>
      <div className="track">
        <div className="fill" style={{ width: `${pos * 100}%`, ["--meter-scale" as string]: `${pos > 0 ? 100 / pos : 100}%` }} />
        {targetDb !== undefined ? <span className="target" style={{ left: `${dbToMeter(targetDb) * 100}%` }} title={`Target ${formatDb(targetDb)}`} /> : null}
      </div>
    </div>
  );
}
