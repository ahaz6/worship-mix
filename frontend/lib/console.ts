/** Console session client: connect, allow writes, plan, apply, undo. */
import { z } from "zod";

export type ConsoleChange = { target: string; param: string; value: Record<string, unknown>; note?: string };

export const sessionSchema = z.object({
  session: z.string(),
  kind: z.string(),
  connected: z.boolean(),
  info: z.unknown().optional(),
  note: z.string().nullable().optional(),
  writes_processing: z.boolean(),
  write_enabled: z.boolean(),
});
export type ConsoleSessionInfo = z.infer<typeof sessionSchema>;

export const planSchema = z.object({
  mode: z.enum(["write", "manual"]),
  steps: z.array(z.string()),
  messages: z.array(z.object({ address: z.string(), value: z.unknown() })),
  manual_steps: z.array(z.string()).optional(),
  applied: z.number().optional(),
});
export type ConsolePlan = z.infer<typeof planSchema>;

async function call<T>(url: string, schema: z.ZodType<T>, init?: RequestInit): Promise<T> {
  const res = await fetch(url, init);
  if (!res.ok) {
    let msg = `Console request failed (${res.status}).`;
    try {
      const b = (await res.json()) as { detail?: unknown };
      if (typeof b.detail === "string") msg = b.detail;
    } catch {
      /* keep generic */
    }
    throw new Error(msg);
  }
  return schema.parse(await res.json());
}

const jsonInit = (body: unknown): RequestInit => ({ method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });

export const connectConsole = (kind: string, host: string) => call("/api/consoles/connect", sessionSchema, jsonInit({ kind, host }));
export const setWrites = (sid: string, enabled: boolean) =>
  call(`/api/consoles/${sid}/writes?enabled=${enabled}`, z.object({ write_enabled: z.boolean() }), { method: "POST" });
export const planChanges = (sid: string, changes: ConsoleChange[]) => call(`/api/consoles/${sid}/plan`, planSchema, jsonInit({ changes }));
export const applyChanges = (sid: string, changes: ConsoleChange[]) => call(`/api/consoles/${sid}/apply`, planSchema, jsonInit({ changes }));
export const undoChanges = (sid: string) => call(`/api/consoles/${sid}/undo`, z.object({ restored: z.number() }), { method: "POST" });

/** Console-neutral text for a change when no console is connected. */
export function describeChange(c: ConsoleChange): string {
  const where = c.target === "main" ? "Main L/R" : `Ch ${c.target.split(":")[1]}`;
  const v = c.value as Record<string, number | string | boolean | null>;
  const n = (k: string, d = 0) => Number(v[k] ?? 0).toFixed(d);
  switch (c.param) {
    case "trim":
      return `${where}: gain/trim ${Number(v.db) > 0 ? "+" : ""}${n("db", 1)} dB`;
    case "hpf":
      return `${where}: high-pass at ${n("freq")} Hz`;
    case "peq":
      return `${where}: EQ band ${v.band} ${String(v.type).replace("_", " ")} ${n("freq")} Hz ${Number(v.gain_db) > 0 ? "+" : ""}${n("gain_db", 1)} dB Q ${n("q", 2)}`;
    case "gate":
      return `${where}: gate threshold ${n("threshold_db")} dB, range ${n("range_db")} dB, attack ${n("attack_ms", 1)} ms, hold ${n("hold_ms")} ms, release ${n("release_ms")} ms`;
    case "comp":
      return `${where}: compressor threshold ${n("threshold_db")} dB, ratio ${v.ratio}:1, attack ${n("attack_ms")} ms, release ${n("release_ms")} ms${v.key ? `, sidechain from ${v.key}` : ""}`;
    case "geq":
      return `${where}: graphic EQ (see GEQ panel)`;
    case "name":
      return `${where}: name "${v.name}"`;
    default:
      return `${where}: ${c.param}`;
  }
}
