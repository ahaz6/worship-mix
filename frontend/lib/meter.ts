/** Map a dB value onto a 0..1 meter position over [floorDb, ceilDb]. */
export function dbToMeter(db: number, floorDb = -60, ceilDb = 0): number {
  if (!Number.isFinite(db)) return 0;
  const clamped = Math.min(ceilDb, Math.max(floorDb, db));
  return (clamped - floorDb) / (ceilDb - floorDb);
}

/** Format a dB/LUFS number for mono readouts: one decimal, explicit minus. */
export function formatDb(value: number | null | undefined): string {
  if (value === null || value === undefined || !Number.isFinite(value)) return "—";
  return value.toFixed(1).replace("-", "−");
}
