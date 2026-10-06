/**
 * Typed client for the FastAPI backend. Everything read back is validated
 * with Zod (same rule as Worship Keys' storage layer).
 */
import { z } from "zod";

export const tipSchema = z.object({
  id: z.string(),
  severity: z.enum(["info", "warning", "critical"]),
  category: z.string(),
  targets: z.array(z.string()).default([]),
  problem: z.string(),
  action: z.string(),
  why: z.string(),
  params: z.record(z.string(), z.unknown()).default({}),
  confidence: z.number(),
});

export const metricsSchema = z.object({
  integrated_lufs: z.number(),
  sample_peak_db: z.number(),
  true_peak_db: z.number(),
  plr_db: z.number(),
  bands_db: z.record(z.string(), z.number()),
  stereo_correlation: z.number().nullable(),
  clipped_samples: z.number(),
});

export const analysisSchema = z.object({ metrics: metricsSchema, tips: z.array(tipSchema) });

export type Tip = z.infer<typeof tipSchema>;
export type Analysis = z.infer<typeof analysisSchema>;

export async function analyzeFile(file: File, targetLufs = -14): Promise<Analysis> {
  const body = new FormData();
  body.append("file", file);
  const res = await fetch(`/api/analyze?target_lufs=${targetLufs}`, { method: "POST", body });
  if (!res.ok) throw new Error(`Analysis failed (${res.status}). Is the backend running on port 8000?`);
  return analysisSchema.parse(await res.json());
}
