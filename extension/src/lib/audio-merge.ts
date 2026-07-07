async function tryDecode(ctx: AudioContext, blob: Blob): Promise<AudioBuffer | null> {
  if (!blob || blob.size < 100) return null;
  try {
    const ab = await blob.arrayBuffer();
    return await ctx.decodeAudioData(ab.slice(0));
  } catch {
    return null;
  }
}

function recordStream(stream: MediaStream, durationMs: number): Promise<Blob> {
  return new Promise((resolve, reject) => {
    const chunks: Blob[] = [];
    const mimeType = MediaRecorder.isTypeSupported("audio/webm;codecs=opus")
      ? "audio/webm;codecs=opus"
      : "audio/webm";
    const rec = new MediaRecorder(stream, { mimeType, audioBitsPerSecond: 128000 });
    rec.ondataavailable = (e) => {
      if (e.data.size > 0) chunks.push(e.data);
    };
    rec.onstop = () => resolve(new Blob(chunks, { type: mimeType }));
    rec.onerror = (e) => reject((e as any)?.error ?? new Error("MediaRecorder failed"));
    rec.start(1000);
    setTimeout(() => {
      if (rec.state !== "inactive") rec.stop();
      stream.getTracks().forEach((t) => t.stop());
    }, Math.max(durationMs, 500));
  });
}

export async function mergeAudioBlobs(blobs: Blob[]): Promise<Blob> {
  const valid = blobs.filter((b) => b && b.size > 100);
  if (!valid.length) throw new Error("No audio to merge");
  if (valid.length === 1) return valid[0];

  const ctx = new AudioContext();
  const buffers = (await Promise.all(valid.map((b) => tryDecode(ctx, b)))).filter(
    (b): b is AudioBuffer => b !== null
  );
  await ctx.close();

  if (!buffers.length) throw new Error("Could not decode audio tracks");
  if (buffers.length === 1) return valid[0];

  const mixCtx = new AudioContext();
  const length = Math.max(...buffers.map((b) => b.length));
  const dest = mixCtx.createMediaStreamDestination();

  for (const buf of buffers) {
    const src = mixCtx.createBufferSource();
    src.buffer = buf;
    src.connect(dest);
    src.start(0);
  }

  const durationMs = (length / mixCtx.sampleRate) * 1000 + 400;
  const merged = await recordStream(dest.stream, durationMs);
  await mixCtx.close();
  return merged;
}
