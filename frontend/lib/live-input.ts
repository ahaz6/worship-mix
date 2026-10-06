/**
 * Continuous measurement-mic input + optional pink-noise playback (Web Audio).
 * Voice processing is disabled; the mic opens only on a user action.
 */
export const MEASURE_RATE = 48000;

export type LiveInput = { sampleRate: number; stop: () => Promise<void> };

export async function startLiveInput(onSamples: (s: Float32Array) => void, deviceId?: string): Promise<LiveInput> {
  if (!navigator.mediaDevices?.getUserMedia) throw new Error("This browser can't access a microphone. Use Chrome or Safari over https or localhost.");
  let stream: MediaStream;
  try {
    stream = await navigator.mediaDevices.getUserMedia({
      audio: { deviceId: deviceId ? { exact: deviceId } : undefined, echoCancellation: false, noiseSuppression: false, autoGainControl: false, channelCount: 1 },
    });
  } catch {
    throw new Error("Microphone access is blocked. Allow it in your browser settings.");
  }
  const ctx = new AudioContext({ sampleRate: MEASURE_RATE });
  await ctx.audioWorklet.addModule("/worklets/capture-processor.js");
  const src = ctx.createMediaStreamSource(stream);
  const node = new AudioWorkletNode(ctx, "capture-processor");
  node.port.onmessage = (e: MessageEvent<Float32Array>) => onSamples(e.data);
  src.connect(node);
  return {
    sampleRate: ctx.sampleRate,
    stop: async () => {
      src.disconnect();
      node.disconnect();
      stream.getTracks().forEach((t) => t.stop());
      await ctx.close();
    },
  };
}

let periodCache: Float32Array | null = null;

/** One period of the periodic pink noise (exact reference for the transfer function). */
export async function loadPinkPeriod(): Promise<Float32Array> {
  if (periodCache) return periodCache;
  const res = await fetch("/api/tuning/pink-period.f32");
  if (!res.ok) throw new Error("Could not load the pink noise reference. Is the backend running?");
  periodCache = new Float32Array(await res.arrayBuffer());
  return periodCache;
}

export type PinkPlayer = { stop: () => Promise<void> };

/** Loops the periodic pink noise on this device's output (e.g. laptop → console). */
export async function playPinkNoise(): Promise<PinkPlayer> {
  const period = await loadPinkPeriod();
  const ctx = new AudioContext({ sampleRate: MEASURE_RATE });
  const buf = ctx.createBuffer(1, period.length, MEASURE_RATE);
  buf.copyToChannel(new Float32Array(period), 0);
  const src = ctx.createBufferSource();
  src.buffer = buf;
  src.loop = true;
  const gain = ctx.createGain();
  gain.gain.setValueAtTime(0, ctx.currentTime);
  gain.gain.linearRampToValueAtTime(1, ctx.currentTime + 1); // no sudden blast
  src.connect(gain).connect(ctx.destination);
  src.start();
  return {
    stop: async () => {
      gain.gain.linearRampToValueAtTime(0, ctx.currentTime + 0.3);
      await new Promise((r) => setTimeout(r, 320));
      src.stop();
      await ctx.close();
    },
  };
}
