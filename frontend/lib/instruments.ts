/** Instrument Tuning client. Results are validated loosely (they're large and evolve). */
import { z } from "zod";

import type { ConsoleChange } from "@/lib/console";

export type MapRow = { input_index: number; profile: string; name: string; console_channel?: number | null };

export const profileSchema = z.object({ key: z.string(), label: z.string(), group: z.string(), tips: z.array(z.string()) });
export type InstrumentProfile = z.infer<typeof profileSchema>;

const note = z.object({ severity: z.string(), problem: z.string(), action: z.string(), why: z.string() });
const eqBand = z.object({ type: z.string(), freq: z.number(), gain_db: z.number(), q: z.number(), why: z.string().optional() });
const change = z.object({ target: z.string(), param: z.string(), value: z.record(z.string(), z.unknown()), note: z.string().optional() });

export const channelSchema = z.object({
  name: z.string(),
  profile: z.string(),
  label: z.string(),
  group: z.string(),
  console_channel: z.number().nullable().optional(),
  metrics: z.object({ peak_dbfs: z.number(), loud_dbfs: z.number(), noise_dbfs: z.number(), crest_db: z.number() }).passthrough(),
  settings: z.object({
    gain: z.object({ trim_db: z.number(), ok: z.boolean() }),
    hpf: z.object({ freq: z.number() }),
    lpf: z.object({ freq: z.number() }).optional(),
    eq: z.array(eqBand),
    gate: z.object({ threshold_db: z.number(), range_db: z.number(), attack_ms: z.number(), hold_ms: z.number(), release_ms: z.number() }).nullable(),
    comp: z.object({ threshold_db: z.number(), ratio: z.number(), attack_ms: z.number(), release_ms: z.number(), makeup_db: z.number() }).nullable(),
    deesser: z.object({ freq: z.number(), reduction_db: z.number() }).nullable(),
    fx: z.object({ reverb: z.string(), reverb_time_s: z.number(), delay_ms: z.number().nullable().optional(), delay_note: z.string().optional() }),
    pan: z.string(),
  }),
  notes: z.array(note),
  changes: z.array(change),
});

export const mixSchema = z.object({
  reference: z.string(),
  balance: z.array(z.object({ channel: z.number(), name: z.string(), relative_lu: z.number(), target_lu: z.number(), fader_db: z.number() })),
  conflicts: z.array(z.object({ band_hz: z.number(), score: z.number(), keep_name: z.string(), give_name: z.string(), action: z.string() })),
  sidechains: z.array(z.object({ key: z.string(), target: z.string(), settings: z.record(z.string(), z.unknown()), why: z.string() })),
  sidechain_changes: z.array(change),
  master: z.object({
    lufs: z.number(),
    peak_dbfs: z.number(),
    plr_db: z.number(),
    eq: z.array(z.object({ freq: z.number(), gain_db: z.number() })),
    bus_comp: z.object({ ratio: z.number(), attack_ms: z.number(), release_ms: z.number(), gr_db: z.number(), threshold_db: z.number(), why: z.string() }),
    limiter: z.object({ ceiling_dbtp: z.number(), why: z.string() }),
    stream: z.object({ target_lufs: z.number(), why: z.string() }),
  }),
});

export const resultSchema = z.object({
  channels: z.array(channelSchema),
  mix: mixSchema.nullable(),
  mapping: z.array(z.record(z.string(), z.unknown())).optional(),
  running: z.boolean().optional(),
  levels: z.record(z.string(), z.number()).optional(),
  error: z.string().nullable().optional(),
});

export type ChannelResult = z.infer<typeof channelSchema>;
export type MixResult = z.infer<typeof mixSchema>;
export type InstrumentResult = z.infer<typeof resultSchema>;
export type Change = ConsoleChange;

async function parse<T>(res: Response, schema: z.ZodType<T>): Promise<T> {
  if (!res.ok) {
    let msg = `Request failed (${res.status}).`;
    try {
      const b = (await res.json()) as { detail?: unknown };
      if (typeof b.detail === "string") msg = b.detail;
    } catch {
      /* generic */
    }
    throw new Error(msg);
  }
  return schema.parse(await res.json());
}

export const fetchProfiles = async () => parse(await fetch("/api/instruments/profiles"), z.array(profileSchema));
export const fetchDevices = async () =>
  parse(await fetch("/api/instruments/devices"), z.array(z.object({ index: z.number(), name: z.string(), inputs: z.number() })));
export const runDemo = async () => parse(await fetch("/api/instruments/demo", { method: "POST" }), resultSchema);

export async function analyzeUpload(files: File[], mapping: MapRow[], roomRt60?: number, bpm?: number) {
  const body = new FormData();
  files.forEach((f) => body.append("files", f));
  body.append("mapping", JSON.stringify(mapping));
  if (roomRt60) body.append("room_rt60", String(roomRt60));
  if (bpm) body.append("bpm", String(bpm));
  return parse(await fetch("/api/instruments/analyze", { method: "POST", body }), resultSchema);
}

export async function startLive(device: number | null, mapping: MapRow[], roomRt60?: number, bpm?: number) {
  return parse(
    await fetch("/api/instruments/live/start", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ device, mapping, room_rt60: roomRt60 ?? null, bpm: bpm ?? null }),
    }),
    z.object({ running: z.boolean() }),
  );
}

export const latestLive = async () => parse(await fetch("/api/instruments/live/latest"), resultSchema.partial().extend({ running: z.boolean() }));
export const stopLive = async () => fetch("/api/instruments/live/stop", { method: "POST" });

/** Best-guess instrument from a track/channel name, so mapping is mostly automatic. */
export function guessProfile(name: string): string {
  const n = name.toLowerCase();
  const rules: [RegExp, string][] = [
    [/kick|bd|bass ?drum/, "kick"],
    [/snare|sn\b/, "snare"],
    [/floor|tom ?3|ft/, "tom3"],
    [/tom ?2|rack ?2/, "tom2"],
    [/tom/, "tom1"],
    [/hat|hh/, "hihat"],
    [/oh|overhead/, "overheads"],
    [/cajon/, "cajon"],
    [/spd|sample/, "sample_pad"],
    [/perc|conga|shaker|bongo/, "percussion"],
    [/bass|bs\b/, "bass"],
    [/ac(ou)?st|ag\b|a-?git/, "acoustic_guitar"],
    [/el(ec)?|eg\b|e-?git|gtr|guitar/, "electric_guitar"],
    [/aux|synth/, "aux_keys"],
    [/pad/, "pad"],
    [/piano/, "piano"],
    [/organ|orgel/, "organ"],
    [/key|kb/, "keys"],
    [/viol|geige/, "violin"],
    [/cello/, "cello"],
    [/sax|trump|horn|brass/, "brass"],
    [/pastor|speech|head|preach|spr/, "speech"],
    [/choir|chor/, "choir"],
    [/bgv|bv|back/, "bgv"],
    [/lead|vox|voc|sing/, "lead_vocal_m"],
    [/track|play|loop|mt/, "tracks"],
  ];
  return rules.find(([r]) => r.test(n))?.[1] ?? "keys";
}
