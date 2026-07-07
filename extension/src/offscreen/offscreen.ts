import { mergeAudioBlobs } from "../lib/audio-merge";

function base64ToBlob(base64: string, type: string): Blob {
  const binary = atob(base64);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
  return new Blob([bytes], { type });
}

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

let mediaRecorder: MediaRecorder | null = null;
let chunks: Blob[] = [];
let captureStream: MediaStream | null = null;
let audioContext: AudioContext | null = null;
let sourceStreams: MediaStream[] = [];

chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  if (message.target !== "offscreen") return;

  (async () => {
    try {
      switch (message.type) {
        case "OFFSCREEN_START": {
          const mode = await startCapture(message.streamId, !!message.tabOnly);
          sendResponse({ ok: true, ...mode });
          break;
        }
        case "OFFSCREEN_PAUSE":
          mediaRecorder?.pause();
          sendResponse({ ok: true });
          break;
        case "OFFSCREEN_RESUME":
          mediaRecorder?.resume();
          sendResponse({ ok: true });
          break;
        case "OFFSCREEN_STOP": {
          const blobs = await stopCapture();
          const tabBlob = new Blob(blobs, { type: "audio/webm" });
          let finalBlob = tabBlob;

          if (message.pageMicBase64) {
            const pageMic = base64ToBlob(
              message.pageMicBase64,
              message.pageMicType || "audio/webm"
            );
            if (pageMic.size > 100 && tabBlob.size > 100) {
              finalBlob = await mergeAudioBlobs([tabBlob, pageMic]);
            } else if (pageMic.size > 100) {
              finalBlob = pageMic;
            }
          }

          const base64 = await blobToBase64(finalBlob);
          sendResponse({
            ok: true,
            size: finalBlob.size,
            base64,
            type: finalBlob.type || "audio/webm",
          });
          break;
        }
        default:
          sendResponse({ ok: false, error: "Unknown offscreen command" });
      }
    } catch (err) {
      sendResponse({ ok: false, error: err instanceof Error ? err.message : String(err) });
    }
  })();
  return true;
});

async function getTabAudioStream(streamId: string): Promise<MediaStream> {
  const stream = await navigator.mediaDevices.getUserMedia({
    audio: {
      mandatory: {
        chromeMediaSource: "tab",
        chromeMediaSourceId: streamId,
      },
    },
    video: {
      mandatory: {
        chromeMediaSource: "tab",
        chromeMediaSourceId: streamId,
        maxWidth: 1,
        maxHeight: 1,
        maxFrameRate: 1,
      },
    },
  } as MediaStreamConstraints);

  for (const track of stream.getVideoTracks()) {
    track.stop();
    stream.removeTrack(track);
  }
  return stream;
}

async function getMicStream(): Promise<MediaStream> {
  return navigator.mediaDevices.getUserMedia({
    audio: {
      echoCancellation: true,
      noiseSuppression: true,
      autoGainControl: true,
    },
    video: false,
  });
}

function mixStreams(streams: MediaStream[], playbackStream: MediaStream | null): MediaStream {
  audioContext = new AudioContext();
  const destination = audioContext.createMediaStreamDestination();

  for (const stream of streams) {
    const tracks = stream.getAudioTracks();
    if (!tracks.length) continue;
    const source = audioContext.createMediaStreamSource(new MediaStream(tracks));
    // Everything goes into the recording.
    source.connect(destination);
    // Tab audio (others in the call) is ALSO played to the speakers, because
    // chrome.tabCapture mutes the tab's own playback while it is captured.
    // The mic is intentionally NOT played back to avoid echo/feedback.
    if (playbackStream && stream === playbackStream) {
      source.connect(audioContext.destination);
    }
  }

  return destination.stream;
}

function cleanupStreams() {
  captureStream?.getTracks().forEach((t) => t.stop());
  captureStream = null;
  for (const stream of sourceStreams) {
    stream.getTracks().forEach((t) => t.stop());
  }
  sourceStreams = [];
  if (audioContext) {
    audioContext.close().catch(() => undefined);
    audioContext = null;
  }
}

async function tryAttachExtensionMic(): Promise<boolean> {
  try {
    const micStream = await getMicStream();
    sourceStreams.push(micStream);
    return true;
  } catch {
    return false;
  }
}

async function startCapture(
  streamId: string,
  tabOnly = false
): Promise<{ hasTab: boolean; hasMic: boolean }> {
  if (!streamId) throw new Error("Missing stream ID for tab capture");

  cleanupStreams();
  sourceStreams = [];

  let hasTab = false;
  let tabStream: MediaStream | null = null;
  try {
    tabStream = await getTabAudioStream(streamId);
    sourceStreams.push(tabStream);
    hasTab = tabStream.getAudioTracks().length > 0;
  } catch (err) {
    const msg = err instanceof Error ? err.message : String(err);
    throw new Error(`Could not capture meeting tab audio: ${msg}`);
  }

  let hasMic = false;
  if (!tabOnly) {
    hasMic = await tryAttachExtensionMic();
  }

  const hasAudio = sourceStreams.some((s) => s.getAudioTracks().length > 0);
  if (!hasAudio) {
    throw new Error("No audio tracks. Join the meeting with audio on, then try again.");
  }

  captureStream = mixStreams(sourceStreams, tabStream);

  chunks = [];
  const mimeType = MediaRecorder.isTypeSupported("audio/webm;codecs=opus")
    ? "audio/webm;codecs=opus"
    : MediaRecorder.isTypeSupported("audio/webm")
      ? "audio/webm"
      : "";

  if (!mimeType) throw new Error("Browser does not support audio/webm recording");

  mediaRecorder = new MediaRecorder(captureStream, {
    mimeType,
    audioBitsPerSecond: 128000,
  });
  mediaRecorder.ondataavailable = (e) => {
    if (e.data.size > 0) chunks.push(e.data);
  };
  mediaRecorder.start(3000);
  return { hasTab, hasMic };
}

async function stopCapture(): Promise<Blob[]> {
  return new Promise((resolve) => {
    if (!mediaRecorder) {
      cleanupStreams();
      return resolve([]);
    }
    mediaRecorder.onstop = () => {
      cleanupStreams();
      mediaRecorder = null;
      resolve(chunks);
      chunks = [];
    };
    if (mediaRecorder.state !== "inactive") {
      mediaRecorder.requestData();
      mediaRecorder.stop();
    } else {
      cleanupStreams();
      resolve(chunks);
    }
  });
}
