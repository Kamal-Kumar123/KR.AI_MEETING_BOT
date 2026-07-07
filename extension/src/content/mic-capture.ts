let micRecorder: MediaRecorder | null = null;
let micStream: MediaStream | null = null;
let micChunks: Blob[] = [];

function blobToBase64(blob: Blob): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      const result = reader.result as string;
      resolve(result.split(",")[1] || "");
    };
    reader.onerror = () => reject(reader.error);
    reader.readAsDataURL(blob);
  });
}

function stopMicTracks() {
  micStream?.getTracks().forEach((t) => t.stop());
  micStream = null;
}

async function startPageMicCapture(): Promise<{ ok: boolean; error?: string }> {
  stopMicTracks();
  micChunks = [];
  try {
    micStream = await navigator.mediaDevices.getUserMedia({
      audio: { echoCancellation: true, noiseSuppression: true },
      video: false,
    });
    const mimeType = MediaRecorder.isTypeSupported("audio/webm;codecs=opus")
      ? "audio/webm;codecs=opus"
      : "audio/webm";
    micRecorder = new MediaRecorder(micStream, { mimeType, audioBitsPerSecond: 48000 });
    micRecorder.ondataavailable = (e) => {
      if (e.data.size > 0) micChunks.push(e.data);
    };
    micRecorder.start(3000);
    return { ok: true };
  } catch (err) {
    stopMicTracks();
    return { ok: false, error: err instanceof Error ? err.message : String(err) };
  }
}

async function stopPageMicCapture(): Promise<{
  ok: boolean;
  size?: number;
  base64?: string;
  type?: string;
  error?: string;
}> {
  if (!micRecorder) {
    stopMicTracks();
    return { ok: false, error: "No page microphone capture active" };
  }

  return new Promise((resolve) => {
    micRecorder!.onstop = async () => {
      stopMicTracks();
      micRecorder = null;
      const blob = new Blob(micChunks, { type: "audio/webm" });
      micChunks = [];
      if (blob.size < 100) {
        resolve({ ok: false, error: "Page microphone recording empty" });
        return;
      }
      const base64 = await blobToBase64(blob);
      resolve({
        ok: true,
        size: blob.size,
        base64,
        type: blob.type || "audio/webm",
      });
    };
    if (micRecorder!.state !== "inactive") {
      micRecorder!.requestData();
      micRecorder!.stop();
    } else {
      resolve({ ok: false, error: "Recorder already stopped" });
    }
  });
}

export function registerPageMicHandlers() {
  chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
    if (message.type === "CONTENT_MIC_START") {
      startPageMicCapture().then(sendResponse);
      return true;
    }
    if (message.type === "CONTENT_MIC_STOP") {
      stopPageMicCapture().then(sendResponse);
      return true;
    }
    return false;
  });
}
