/** Typed client for /api/tuning (Zod-validated, like the rest of the suite). */
import { z } from "zod";

const num = z.number();
const maybe = z.number().nullable();

export const roomSchema = z.object({
  bands: z.record(z.string(), z.object({ rt60_s: maybe, c50_db: num })).optional(),
  rt60_mid_s: maybe.optional(),
  c50_speech_db: num.optional(),
  speech_rating: z.enum(["good", "fair", "poor"]).optional(),
  schroeder_hz: num.optional(),
  volume_m3: maybe.optional(),
});

export const measurementSchema = z.object({
  id: z.string(),
  label: z.string(),
  freqs: z.array(num),
  magnitude_db: z.array(maybe),
  phase_deg: z.array(maybe),
  group_delay_ms: z.array(maybe),
  snr_db: z.array(num),
  arrival_ms: num,
  room: roomSchema,
});

export const filterSchema = z.object({ type: z.enum(["peak", "low_shelf", "high_shelf"]), freq: num, gain_db: num, q: num });

export const equalizeSchema = z.object({
  freqs: z.array(num),
  measured_db: z.array(maybe),
  target_db: z.array(num),
  target_offset_db: num,
  tolerance_db: num,
  correction_db: z.array(num),
  predicted_db: z.array(maybe),
  filters: z.array(filterSchema),
  geq31: z.array(z.object({ freq: num, gain_db: num })),
  max_boost_db: num,
  preamp_db: num,
  rms_error_before_db: num,
  rms_error_after_db: num,
  within_tolerance_pct: num,
  console_plan: z.object({ console: z.string(), peq_steps: z.array(z.string()), geq_steps: z.array(z.string()), osc: z.array(z.unknown()) }),
  console_changes: z.array(z.object({ target: z.string(), param: z.string(), value: z.record(z.string(), z.unknown()), note: z.string().optional() })),
});

export const targetsSchema = z.object({
  tolerance_db: num,
  curves: z.record(z.string(), z.object({ label: z.string(), use: z.string(), builtin: z.boolean() })),
});

export const alignSchema = z.object({
  crossover: z.record(z.string(), z.unknown()),
  alignment: z.object({
    crossover_hz: num,
    phase_difference_deg: num,
    arrival_difference_ms: num,
    delay_main_ms: num,
    delay_sub_ms: num,
    consider_polarity_flip: z.boolean(),
    note: z.string(),
  }),
  levels: z.object({ sub_gain_db: num }),
});

export type TuningMeasurement = z.infer<typeof measurementSchema>;
export type EqualizeResult = z.infer<typeof equalizeSchema>;
export type AlignResult = z.infer<typeof alignSchema>;

export type EqOptions = {
  target: string;
  max_filters: number;
  max_boost_db: number;
  max_gain_db: number;
  max_q: number;
  allow_only_cuts: boolean;
  allow_shelves: boolean;
  fmin: number;
  fmax: number;
  schroeder_hz: number;
  console: string;
};

export const DEFAULT_EQ: EqOptions = {
  target: "worship_warm",
  max_filters: 8,
  max_boost_db: 4,
  max_gain_db: 9,
  max_q: 8,
  allow_only_cuts: false,
  allow_shelves: true,
  fmin: 30,
  fmax: 12000,
  schroeder_hz: 300,
  console: "generic",
};

async function json<T>(res: Response, schema: z.ZodType<T>): Promise<T> {
  if (!res.ok) {
    let msg = `Request failed (${res.status}).`;
    try {
      const body = (await res.json()) as { detail?: unknown };
      if (typeof body.detail === "string") msg = body.detail;
    } catch {
      /* keep generic message */
    }
    throw new Error(msg);
  }
  return schema.parse(await res.json());
}

export async function fetchTargets() {
  return json(await fetch("/api/tuning/targets"), targetsSchema);
}

export async function uploadMeasurement(wav: Blob, label: string, removeDelay: boolean, roomVolume?: number) {
  const body = new FormData();
  body.append("file", wav, "measurement.wav");
  body.append("label", label);
  body.append("remove_delay", String(removeDelay));
  if (roomVolume) body.append("room_volume_m3", String(roomVolume));
  return json(await fetch("/api/tuning/measure", { method: "POST", body }), measurementSchema);
}

export async function averageMeasurements(ids: string[]) {
  return json(
    await fetch("/api/tuning/average", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ ids }) }),
    measurementSchema,
  );
}

export async function deleteMeasurement(id: string) {
  await fetch(`/api/tuning/measurements/${id}`, { method: "DELETE" });
}

export async function equalize(measurementId: string, opts: EqOptions) {
  return json(
    await fetch("/api/tuning/equalize", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ measurement_id: measurementId, ...opts }),
    }),
    equalizeSchema,
  );
}

export async function align(mainId: string, subId: string, crossoverHz?: number) {
  return json(
    await fetch("/api/tuning/align", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ main_id: mainId, sub_id: subId, crossover_hz: crossoverHz || null }),
    }),
    alignSchema,
  );
}

/** Downloads an export file through a temporary link. */
export async function exportFilters(measurementId: string, opts: EqOptions, format: string) {
  const res = await fetch("/api/tuning/export", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ measurement_id: measurementId, format, ...opts }),
  });
  if (!res.ok) throw new Error("Export failed.");
  const name = /filename="([^"]+)"/.exec(res.headers.get("Content-Disposition") ?? "")?.[1] ?? "export";
  const url = URL.createObjectURL(await res.blob());
  const a = document.createElement("a");
  a.href = url;
  a.download = name;
  a.click();
  URL.revokeObjectURL(url);
}

export async function importResponse(label: string, freqs: number[], magnitudeDb: (number | null)[], phaseDeg: (number | null)[], coherence: number[]) {
  return json(
    await fetch("/api/tuning/import-response", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ label, freqs, magnitude_db: magnitudeDb, phase_deg: phaseDeg, coherence }),
    }),
    measurementSchema,
  );
}
