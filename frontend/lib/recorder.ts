/**
 * Measurement microphone capture.
 *
 * Browser voice processing would destroy a measurement, so echo cancellation,
 * noise suppression and auto gain are switched off. The mic is only opened on
 * an explicit user action (Design-Art.md 11).
 */
import { concatChunks, encodeWavFloat32 } from "@/lib/wav";

export type Recording = { wav: Blob; seconds: number; peak: number };

export async function recordMeasurement(seconds: number, deviceId?: string, onLevel?: (peak: number) => void): Promise<Recording> {
  if (!navigator.mediaDevices?.getUserMedia) {
    throw new Error("This browser can't access a microphone. Use Chrome or Safari over https or localhost.");
  }
  let stream: MediaStream;
  try {
    stream = await navigator.mediaDevices.getUserMedia({
      audio: {
        deviceId: deviceId ? { exact: deviceId } : undefined,
        echoCancellation: false,
        noiseSuppression: false,
        autoGainControl: false,
        channelCount: 1,
      },
    });
  } catch {
    throw new Error("Microphone access is blocked. Allow it in your browser settings.");
  }
  const ctx = new AudioContext();
  try {
    await ctx.audioWorklet.addModule("/worklets/capture-processor.js");
    const src = ctx.createMediaStreamSource(stream);
    const node = new AudioWorkletNode(ctx, "capture-processor");
    const chunks: Float32Array[] = [];
    let peak = 0;
    node.port.onmessage = (e: MessageEvent<Float32Array>) => {
      chunks.push(e.data);
      let p = 0;
      for (const s of e.data) p = Math.max(p, Math.abs(s));
      peak = Math.max(peak, p);
      onLevel?.(p);
    };
    src.connect(node);
    await new Promise((r) => setTimeout(r, seconds * 1000));
    src.disconnect();
    node.disconnect();
    return { wav: encodeWavFloat32(concatChunks(chunks), ctx.sampleRate), seconds, peak };
  } finally {
    stream.getTracks().forEach((t) => t.stop());
    await ctx.close();
  }
}

export async function listInputs(): Promise<MediaDeviceInfo[]> {
  if (!navigator.mediaDevices?.enumerateDevices) return [];
  return (await navigator.mediaDevices.enumerateDevices()).filter((d) => d.kind === "audioinput");
}
