// Whisper works best on 16 kHz mono audio, and downmixing here keeps the
// uploaded file tiny (~2 MB / 10 min) so long meetings don't blow up memory
// or storage. We mix OFFLINE (no real-time re-recording), so merging a 30-min
// meeting takes a couple of seconds instead of 30 minutes.
const TARGET_SR = 16000;

async function decodeResampleMono(blob: Blob): Promise<Float32Array | null> {
  if (!blob || blob.size < 100) return null;

  // Decode at the file's native rate/channels.
  const decodeCtx = new AudioContext();
  let decoded: AudioBuffer;
  try {
    const ab = await blob.arrayBuffer();
    decoded = await decodeCtx.decodeAudioData(ab.slice(0));
  } catch {
    await decodeCtx.close().catch(() => undefined);
    return null;
  }
  await decodeCtx.close().catch(() => undefined);

  // Render to 16 kHz mono offline (fast, bounded memory). The big native-rate
  // buffer is released as soon as this function returns.
  const frames = Math.max(1, Math.ceil(decoded.duration * TARGET_SR));
  const offline = new OfflineAudioContext(1, frames, TARGET_SR);
  const src = offline.createBufferSource();
  src.buffer = decoded;
  src.connect(offline.destination);
  src.start(0);
  const rendered = await offline.startRendering();
  return Float32Array.from(rendered.getChannelData(0));
}

function encodeWav(samples: Float32Array, sampleRate: number, gain = 1): Blob {
  const dataLen = samples.length * 2; // 16-bit PCM
  const buffer = new ArrayBuffer(44 + dataLen);
  const view = new DataView(buffer);

  const writeStr = (offset: number, str: string) => {
    for (let i = 0; i < str.length; i++) view.setUint8(offset + i, str.charCodeAt(i));
  };

  writeStr(0, "RIFF");
  view.setUint32(4, 36 + dataLen, true);
  writeStr(8, "WAVE");
  writeStr(12, "fmt ");
  view.setUint32(16, 16, true);
  view.setUint16(20, 1, true); // PCM
  view.setUint16(22, 1, true); // mono
  view.setUint32(24, sampleRate, true);
  view.setUint32(28, sampleRate * 2, true); // byte rate
  view.setUint16(32, 2, true); // block align
  view.setUint16(34, 16, true); // bits per sample
  writeStr(36, "data");
  view.setUint32(40, dataLen, true);

  let offset = 44;
  for (let i = 0; i < samples.length; i++) {
    let s = samples[i] * gain;
    s = Math.max(-1, Math.min(1, s));
    view.setInt16(offset, s < 0 ? s * 0x8000 : s * 0x7fff, true);
    offset += 2;
  }
  return new Blob([buffer], { type: "audio/wav" });
}

export async function mergeAudioBlobs(blobs: Blob[]): Promise<Blob> {
  const valid = blobs.filter((b) => b && b.size > 100);
  if (!valid.length) throw new Error("No audio to merge");

  // Decode + resample each source one at a time so we never hold more than one
  // large native-rate buffer in memory simultaneously.
  const tracks: Float32Array[] = [];
  for (const blob of valid) {
    const mono = await decodeResampleMono(blob);
    if (mono && mono.length) tracks.push(mono);
  }
  if (!tracks.length) throw new Error("Could not decode audio tracks");

  const length = Math.max(...tracks.map((t) => t.length));
  const mixed = new Float32Array(length);
  for (const t of tracks) {
    for (let i = 0; i < t.length; i++) mixed[i] += t[i];
  }

  // Normalize only if summing the tracks pushed us past full scale.
  let peak = 0;
  for (let i = 0; i < length; i++) {
    const a = Math.abs(mixed[i]);
    if (a > peak) peak = a;
  }
  const gain = peak > 1 ? 1 / peak : 1;

  return encodeWav(mixed, TARGET_SR, gain);
}
