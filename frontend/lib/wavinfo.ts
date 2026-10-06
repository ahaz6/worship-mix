/** Read channel count / sample rate from a WAV header (first chunk only). */
export async function wavChannels(file: File): Promise<{ channels: number; sampleRate: number } | null> {
  const buf = new DataView(await file.slice(0, 65536).arrayBuffer());
  const tag = (o: number) => String.fromCharCode(buf.getUint8(o), buf.getUint8(o + 1), buf.getUint8(o + 2), buf.getUint8(o + 3));
  if (buf.byteLength < 12 || tag(0) !== "RIFF" || tag(8) !== "WAVE") return null;
  let o = 12;
  while (o + 8 <= buf.byteLength) {
    const id = tag(o);
    const size = buf.getUint32(o + 4, true);
    if (id === "fmt ") return { channels: buf.getUint16(o + 10, true), sampleRate: buf.getUint32(o + 12, true) };
    o += 8 + size + (size % 2);
  }
  return null;
}
