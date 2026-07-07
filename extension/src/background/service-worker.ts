import { apiFetch, getConfig } from "../lib/config";
import { clearSession, getSession, saveSession } from "../lib/session";
import { detectPlatform } from "../lib/platforms";
import { buildMeetingPageUrl } from "../lib/upload";
import { base64ToBlob, blobToBase64, loadPageMicAudio, savePageMicAudio } from "../lib/session-audio";

function computeElapsedMs(session: Awaited<ReturnType<typeof getSession>>): number {
  if (!session.startedAt || session.status === "idle") return session.elapsedMs;
  if (session.status === "paused") return session.elapsedMs;
  return session.elapsedMs + (Date.now() - session.startedAt);
}

async function ensureOffscreen() {
  const contexts = await chrome.runtime.getContexts({ contextTypes: ["OFFSCREEN_DOCUMENT"] });
  if (contexts.length) return;
  await chrome.offscreen.createDocument({
    url: "offscreen.html",
    reasons: ["USER_MEDIA", "AUDIO_PLAYBACK"],
    justification: "Record meeting tab audio and play it back so the user still hears the call",
  });
}

async function injectMicScript(tabId: number, platform: string): Promise<void> {
  const file =
    platform === "google_meet"
      ? "content/meet.js"
      : platform === "microsoft_teams"
        ? "content/teams.js"
        : platform === "zoom_web"
          ? "content/zoom.js"
          : null;
  if (!file) return;
  await chrome.scripting.executeScript({ target: { tabId }, files: [file] });
}

async function startPageMic(tabId: number, platform: string): Promise<boolean> {
  const tryStart = async (): Promise<boolean> => {
    const res = await chrome.tabs.sendMessage(tabId, { type: "CONTENT_MIC_START" });
    return !!res?.ok;
  };
  try {
    return await tryStart();
  } catch {
    try {
      await injectMicScript(tabId, platform);
      return await tryStart();
    } catch {
      return false;
    }
  }
}

async function stopPageMic(tabId: number): Promise<void> {
  try {
    const res = await chrome.tabs.sendMessage(tabId, { type: "CONTENT_MIC_STOP" });
    if (res?.ok && res.base64) {
      const binary = atob(res.base64);
      const bytes = new Uint8Array(binary.length);
      for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
      const blob = new Blob([bytes], { type: res.type || "audio/webm" });
      await savePageMicAudio(blob);
    }
  } catch {
    /* meeting tab closed */
  }
}

chrome.runtime.onInstalled.addListener(async () => {
  const contexts = await chrome.runtime.getContexts({ contextTypes: ["OFFSCREEN_DOCUMENT"] });
  if (contexts.length) {
    await chrome.offscreen.closeDocument();
  }
});

function notify(title: string, message: string) {
  try {
    chrome.notifications.create(
      {
        type: "basic",
        iconUrl: chrome.runtime.getURL("icons/icon128.png"),
        title,
        message,
      },
      () => {
        // Swallow "Unable to download all specified images" and similar.
        void chrome.runtime.lastError;
      }
    );
  } catch {
    /* notifications unavailable */
  }
}

chrome.notifications.onClicked.addListener(async () => {
  const { lastMeetingUrl } = (await chrome.storage.local.get("lastMeetingUrl")) as {
    lastMeetingUrl?: string;
  };
  if (lastMeetingUrl) {
    chrome.tabs.create({ url: lastMeetingUrl });
  }
});

async function openMeetingReport(openUrl: string) {
  const settings = await chrome.storage.sync.get(["open_dashboard"]);
  if (settings.open_dashboard === false) return;

  await chrome.storage.local.set({ lastMeetingUrl: openUrl });
  notify("Meeting uploaded", "Click to open your meeting report.");
}

chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  handleMessage(message).then(sendResponse).catch((e) => sendResponse({ ok: false, error: String(e) }));
  return true;
});

async function handleMessage(message: {
  type: string;
  tabId?: number;
  streamId?: string;
}) {
  switch (message.type) {
    case "START_RECORDING":
      return startRecording(message.tabId!, message.streamId);
    case "PAUSE_RECORDING":
      return pauseRecording();
    case "RESUME_RECORDING":
      return resumeRecording();
    case "STOP_RECORDING":
      return stopRecording();
    case "GET_STATUS": {
      const session = await getSession();
      return {
        ...session,
        elapsedMs: computeElapsedMs(session),
      };
    }
    default:
      return { ok: false };
  }
}

async function startRecording(tabId: number, streamId?: string) {
  const tab = await chrome.tabs.get(tabId);
  if (!tab.url) throw new Error("No active tab URL");

  if (!streamId) {
    throw new Error("Missing stream ID — click Start Recording from the extension popup.");
  }

  await ensureOffscreen();

  const session = await getSession();
  session.tabId = tabId;
  session.meetingUrl = tab.url;
  session.platform = detectPlatform(tab.url);
  session.status = "recording";
  session.startedAt = Date.now();
  session.elapsedMs = 0;
  session.pausedAt = null;
  session.chunks = [];
  session.pageMicActive = false;
  await saveSession(session);

  // Use the meeting site's existing mic permission (e.g. meet.google.com already allowed).
  session.pageMicActive = await startPageMic(tabId, session.platform);
  await saveSession(session);

  const offscreenRes = await chrome.runtime.sendMessage({
    type: "OFFSCREEN_START",
    target: "offscreen",
    streamId,
    tabOnly: session.pageMicActive,
  });
  if (!offscreenRes?.ok) {
    if (session.pageMicActive && session.tabId) {
      await stopPageMic(session.tabId);
    }
    session.status = "idle";
    session.pageMicActive = false;
    await saveSession(session);
    throw new Error(offscreenRes?.error || "Failed to start audio capture");
  }

  session.captureMode = {
    hasTab: !!offscreenRes.hasTab,
    hasMic: session.pageMicActive || !!offscreenRes.hasMic,
  };
  await saveSession(session);

  const modeLabel =
    session.captureMode.hasMic && session.captureMode.hasTab
      ? "your voice + meeting audio"
      : session.captureMode.hasTab
        ? "meeting tab audio only"
        : "microphone only";

  notify("Recording started", `Capturing ${modeLabel}.`);

  return {
    ok: true,
    status: "recording",
    captureMode: session.captureMode,
  };
}

async function pauseRecording() {
  await chrome.runtime.sendMessage({ type: "OFFSCREEN_PAUSE", target: "offscreen" });
  const session = await getSession();
  if (session.startedAt) {
    session.elapsedMs += Date.now() - session.startedAt;
    session.startedAt = null;
  }
  session.status = "paused";
  session.pausedAt = Date.now();
  await saveSession(session);
  return { ok: true, status: "paused" };
}

async function resumeRecording() {
  await chrome.runtime.sendMessage({ type: "OFFSCREEN_RESUME", target: "offscreen" });
  const session = await getSession();
  session.status = "recording";
  session.startedAt = Date.now();
  session.pausedAt = null;
  await saveSession(session);
  return { ok: true, status: "recording" };
}

async function stopRecording() {
  const session = await getSession();

  if (session.pageMicActive && session.tabId) {
    await stopPageMic(session.tabId);
  }

  let pageMicBase64: string | undefined;
  let pageMicType: string | undefined;
  if (session.pageMicActive) {
    const pageMic = await loadPageMicAudio();
    if (pageMic && pageMic.size > 100) {
      pageMicBase64 = await blobToBase64(pageMic);
      pageMicType = pageMic.type;
    }
  }

  const stopRes = await chrome.runtime.sendMessage({
    type: "OFFSCREEN_STOP",
    target: "offscreen",
    pageMicBase64,
    pageMicType,
  });

  if (stopRes?.ok === false) {
    throw new Error(stopRes.error || "Stop capture failed");
  }
  if (!stopRes?.base64) {
    throw new Error("No audio captured. Speak for at least 15 seconds, then try again.");
  }

  // Capture the recording length, then reset the session to idle so the timer
  // never resumes from the old time — the next recording always starts at 0.
  const durationSeconds = Math.max(1, Math.floor(computeElapsedMs(session) / 1000));
  const platform = session.platform;
  const meetingUrl = session.meetingUrl;
  session.status = "idle";
  session.startedAt = null;
  session.pausedAt = null;
  session.elapsedMs = 0;
  session.pageMicActive = false;
  session.captureMode = undefined;
  await saveSession(session);

  const mergedType = stopRes.type || "audio/webm";
  const merged = base64ToBlob(stopRes.base64, mergedType);
  if (merged.size < 1000) {
    throw new Error("Recording too short or empty. Speak for at least 15 seconds, then try again.");
  }
  const fileExt = mergedType.includes("wav") ? "wav" : "webm";

  const meeting = await apiFetch("/api/v1/meetings", {
    method: "POST",
    body: JSON.stringify({
      platform: platform,
      meeting_url: meetingUrl,
      title: "Meeting Recording",
    }),
  });

  const form = new FormData();
  form.append("file", merged, `recording.${fileExt}`);
  form.append("meeting_id", meeting.id);
  form.append("platform", platform);
  form.append("meeting_url", meetingUrl);
  form.append("duration_seconds", String(durationSeconds));

  const config = await getConfig();
  const token = ((await chrome.storage.local.get("token")) as { token?: string }).token;
  const upload = await fetch(`${config.API_URL}/api/v1/recordings/upload`, {
    method: "POST",
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    body: form,
  });
  if (!upload.ok) {
    const err = await upload.json().catch(() => ({ detail: upload.statusText }));
    throw new Error(err.detail || `Upload failed (${upload.status})`);
  }

  const result = await upload.json();

  const openUrl = buildMeetingPageUrl(
    config.FRONTEND_URL,
    result.meeting_id,
    result.share_token,
    config.API_URL
  );

  await openMeetingReport(openUrl);
  await clearSession();
  return { ok: true, meetingId: result.meeting_id, openUrl };
}
