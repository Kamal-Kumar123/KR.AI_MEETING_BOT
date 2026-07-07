import { apiFetch, getConfig, getToken } from "../lib/config";
import { findMeetingTab } from "../lib/meeting-tab";
import { detectPlatform, isSupportedMeetingUrl } from "../lib/platforms";
import { getTabStreamId } from "../lib/tab-capture";

const captureSourcesEl = document.getElementById("captureSources")!;
const srcTabEl = document.getElementById("srcTab")!;
const srcMicEl = document.getElementById("srcMic")!;

function updateCaptureSources(mode?: { hasTab: boolean; hasMic: boolean }) {
  if (!mode) {
    captureSourcesEl.classList.add("hidden");
    return;
  }
  captureSourcesEl.classList.remove("hidden");
  srcTabEl.className = `source-pill ${mode.hasTab ? "active" : "inactive"}`;
  srcMicEl.className = `source-pill ${mode.hasMic ? "active" : "inactive"}`;
}

function recordingHint(captureMode?: { hasTab: boolean; hasMic: boolean }): string {
  if (captureMode?.hasMic && captureMode?.hasTab) {
    return "Recording your voice + others. Speak clearly for at least 20 seconds.";
  }
  if (captureMode?.hasTab) {
    return "Recording meeting audio only. Join with mic on in the call and speak for 20+ seconds.";
  }
  return "Recording started. Speak for at least 20 seconds before Stop.";
}

const authView = document.getElementById("authView")!;
const mainView = document.getElementById("mainView")!;
const authMsg = document.getElementById("authMsg")!;
const mainMsg = document.getElementById("mainMsg")!;
const statusEl = document.getElementById("status")!;
const platformEl = document.getElementById("platform")!;
const timerEl = document.getElementById("timer")!;
const userEmailEl = document.getElementById("userEmail")!;
const startBtn = document.getElementById("startBtn") as HTMLButtonElement;

let timerInterval: number | null = null;

function formatTime(ms: number): string {
  const sec = Math.max(0, Math.floor(ms / 1000));
  const mm = String(Math.floor(sec / 60)).padStart(2, "0");
  const ss = String(sec % 60).padStart(2, "0");
  return `${mm}:${ss}`;
}

function friendlyFetchError(err: unknown, apiUrl: string): string {
  const msg = err instanceof Error ? err.message : String(err);
  if (msg === "Failed to fetch" || msg.includes("NetworkError")) {
    return `Cannot reach API at ${apiUrl}. Start it: cd apps/api && python -m app.main`;
  }
  return msg;
}

async function checkApiReachable(): Promise<boolean> {
  try {
    const config = await getConfig();
    const res = await fetch(`${config.API_URL}/health`, { method: "GET" });
    return res.ok;
  } catch {
    return false;
  }
}

function setAuthMsg(text: string, isError = true) {
  authMsg.textContent = text;
  authMsg.className = isError ? "error" : "success";
}

function setMainMsg(text: string, isError = true) {
  mainMsg.textContent = text;
  mainMsg.className = isError ? "error" : "success";
}

function showAuthView() {
  authView.classList.remove("hidden");
  mainView.classList.add("hidden");
  stopTimer();
}

function showMainView(email?: string) {
  authView.classList.add("hidden");
  mainView.classList.remove("hidden");
  if (email) userEmailEl.textContent = email;
  initMain();
}

function stopTimer() {
  if (timerInterval) {
    clearInterval(timerInterval);
    timerInterval = null;
  }
}

function startTimerTick() {
  stopTimer();
  timerInterval = window.setInterval(async () => {
    const res = await chrome.runtime.sendMessage({ type: "GET_STATUS" });
    updateTimerDisplay(res);
  }, 500);
}

function updateTimerDisplay(session: { status?: string; elapsedMs?: number }) {
  const ms = session.elapsedMs ?? 0;
  timerEl.textContent = formatTime(ms);
  timerEl.classList.remove("recording", "paused");
  if (session.status === "recording") timerEl.classList.add("recording");
  if (session.status === "paused") timerEl.classList.add("paused");
}

function setRecordingControls(recording: boolean) {
  startBtn.disabled = recording;
}

async function verifyToken(): Promise<{ ok: boolean; email?: string }> {
  const token = await getToken();
  if (!token) return { ok: false };

  const stored = await chrome.storage.local.get("userEmail");
  const email = stored.userEmail as string | undefined;

  try {
    const config = await getConfig();
    const res = await fetch(`${config.API_URL}/api/v1/settings`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    // Only log out when the token is actually rejected (invalid/expired).
    if (res.status === 401 || res.status === 403) {
      await chrome.storage.local.remove(["token", "userEmail"]);
      return { ok: false };
    }
    // Success or any other status (5xx, etc.) → keep the session.
    return { ok: true, email };
  } catch {
    // Network error / API offline / restarting → keep the user logged in.
    return { ok: true, email };
  }
}

async function onAuthSuccess(token: string, email?: string) {
  await chrome.storage.local.set({ token, userEmail: email || "" });
  showMainView(email);
}

// --- Auth tabs ---
document.getElementById("tabLogin")!.addEventListener("click", () => {
  document.getElementById("tabLogin")!.classList.add("active");
  document.getElementById("tabSignup")!.classList.remove("active");
  document.getElementById("loginForm")!.classList.remove("hidden");
  document.getElementById("signupForm")!.classList.add("hidden");
  document.getElementById("forgotForm")!.classList.add("hidden");
  setAuthMsg("");
});

document.getElementById("tabSignup")!.addEventListener("click", () => {
  document.getElementById("tabSignup")!.classList.add("active");
  document.getElementById("tabLogin")!.classList.remove("active");
  document.getElementById("signupForm")!.classList.remove("hidden");
  document.getElementById("loginForm")!.classList.add("hidden");
  document.getElementById("forgotForm")!.classList.add("hidden");
  setAuthMsg("");
});

document.getElementById("forgotBtn")!.addEventListener("click", () => {
  const loginEmail = (document.getElementById("loginEmail") as HTMLInputElement).value;
  document.getElementById("loginForm")!.classList.add("hidden");
  document.getElementById("forgotForm")!.classList.remove("hidden");
  if (loginEmail) {
    (document.getElementById("forgotEmail") as HTMLInputElement).value = loginEmail;
  }
  setAuthMsg("");
});

document.getElementById("forgotBackBtn")!.addEventListener("click", () => {
  document.getElementById("forgotForm")!.classList.add("hidden");
  document.getElementById("loginForm")!.classList.remove("hidden");
  setAuthMsg("");
});

document.getElementById("loginBtn")!.addEventListener("click", async () => {
  const email = (document.getElementById("loginEmail") as HTMLInputElement).value.trim();
  const password = (document.getElementById("loginPassword") as HTMLInputElement).value;
  if (!email || !password) {
    setAuthMsg("Enter email and password");
    return;
  }
  try {
    const config = await getConfig();
    const res = await fetch(`${config.API_URL}/api/v1/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Login failed");
    await onAuthSuccess(data.access_token, email);
  } catch (e) {
    const config = await getConfig();
    setAuthMsg(friendlyFetchError(e, config.API_URL));
  }
});

document.getElementById("signupBtn")!.addEventListener("click", async () => {
  const full_name = (document.getElementById("signupName") as HTMLInputElement).value.trim();
  const email = (document.getElementById("signupEmail") as HTMLInputElement).value.trim();
  const password = (document.getElementById("signupPassword") as HTMLInputElement).value;
  if (!email || !password) {
    setAuthMsg("Enter email and password");
    return;
  }
  if (password.length < 8) {
    setAuthMsg("Password must be at least 8 characters");
    return;
  }
  try {
    const config = await getConfig();
    const res = await fetch(`${config.API_URL}/api/v1/auth/register`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password, full_name: full_name || undefined }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Registration failed");
    await onAuthSuccess(data.access_token, email);
  } catch (e) {
    const config = await getConfig();
    setAuthMsg(friendlyFetchError(e, config.API_URL));
  }
});

document.getElementById("forgotSubmitBtn")!.addEventListener("click", async () => {
  const email = (document.getElementById("forgotEmail") as HTMLInputElement).value.trim();
  if (!email) {
    setAuthMsg("Enter your email");
    return;
  }
  try {
    const config = await getConfig();
    const res = await fetch(`${config.API_URL}/api/v1/auth/forgot-password`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Request failed");
    setAuthMsg(data.message || "If an account exists, reset instructions will be sent.", false);
  } catch (e) {
    setAuthMsg(e instanceof Error ? e.message : String(e));
  }
});

function clearGoogleAuthCache(): Promise<void> {
  return new Promise((resolve) => {
    chrome.identity.clearAllCachedAuthTokens(() => resolve());
  });
}

document.getElementById("googleBtn")!.addEventListener("click", async () => {
  const manifest = chrome.runtime.getManifest() as chrome.runtime.Manifest & {
    oauth2?: { client_id: string };
  };
  const clientId = manifest.oauth2?.client_id;
  if (!clientId || clientId.startsWith("YOUR_")) {
    setAuthMsg("Set oauth2.client_id in manifest.json");
    return;
  }

  await clearGoogleAuthCache();

  chrome.identity.getAuthToken({ interactive: true }, async (accessToken) => {
    if (chrome.runtime.lastError || !accessToken) {
      setAuthMsg(chrome.runtime.lastError?.message || "Google login cancelled");
      return;
    }
    try {
      const config = await getConfig();
      const res = await fetch(`${config.API_URL}/api/v1/auth/google`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ access_token: accessToken }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Google auth failed");

      let email = "";
      try {
        const profile = await fetch("https://www.googleapis.com/oauth2/v3/userinfo", {
          headers: { Authorization: `Bearer ${accessToken}` },
        });
        if (profile.ok) {
          const p = await profile.json();
          email = p.email || "";
        }
      } catch {
        /* optional */
      }

      await onAuthSuccess(data.access_token, email);
    } catch (e) {
      const config = await getConfig();
      setAuthMsg(friendlyFetchError(e, config.API_URL));
    }
  });
});

document.getElementById("logoutBtn")!.addEventListener("click", async () => {
  await chrome.storage.local.remove(["token", "userEmail"]);
  await clearGoogleAuthCache();
  try {
    const config = await getConfig();
    await fetch(`${config.API_URL}/api/v1/auth/logout`, { method: "POST" });
  } catch {
    /* optional */
  }
  showAuthView();
  setAuthMsg("");
});

document.getElementById("settingsLink")!.addEventListener("click", () => {
  chrome.runtime.openOptionsPage();
});

document.getElementById("startBtn")!.addEventListener("click", async () => {
  const token = await getToken();
  if (!token) {
    showAuthView();
    setAuthMsg("Please log in first");
    return;
  }

  const current = await chrome.runtime.sendMessage({ type: "GET_STATUS" });
  if (current.status === "recording" || current.status === "paused") {
    setMainMsg("Already recording. Use Stop & Upload when done.", false);
    return;
  }

  const tab = await findMeetingTab();
  if (!tab?.id) {
    setMainMsg("Open Google Meet, Teams, or Zoom in this browser window first.");
    return;
  }

  startBtn.disabled = true;
  setMainMsg("Starting recording…", false);

  try {
    const streamId = await getTabStreamId(tab.id);
    const res = await chrome.runtime.sendMessage({
      type: "START_RECORDING",
      tabId: tab.id,
      streamId,
    });
    if (!res?.ok) throw new Error(res?.error || "Failed to start");

    statusEl.textContent = "Status: recording";
    updateCaptureSources(res.captureMode);
    setRecordingControls(true);
    setMainMsg(recordingHint(res.captureMode), false);
    startTimerTick();
  } catch (e) {
    setMainMsg(e instanceof Error ? e.message : String(e));
    setRecordingControls(false);
  } finally {
    startBtn.disabled = false;
  }
});

document.getElementById("pauseBtn")!.addEventListener("click", async () => {
  await chrome.runtime.sendMessage({ type: "PAUSE_RECORDING" });
  statusEl.textContent = "Status: paused";
  const res = await chrome.runtime.sendMessage({ type: "GET_STATUS" });
  updateTimerDisplay(res);
});

document.getElementById("resumeBtn")!.addEventListener("click", async () => {
  await chrome.runtime.sendMessage({ type: "RESUME_RECORDING" });
  statusEl.textContent = "Status: recording";
  startTimerTick();
});

document.getElementById("stopBtn")!.addEventListener("click", async () => {
  // Reset the timer to 0 immediately so the next recording starts fresh,
  // even while the upload is still in progress.
  stopTimer();
  timerEl.textContent = "00:00";
  timerEl.classList.remove("recording", "paused");
  statusEl.textContent = "Status: idle";
  updateCaptureSources();
  setRecordingControls(false);
  setMainMsg("Uploading...", false);
  try {
    const res = await chrome.runtime.sendMessage({ type: "STOP_RECORDING" });
    if (!res?.ok) throw new Error(res?.error || "Upload failed");
    if (res.openUrl) {
      chrome.tabs.create({ url: res.openUrl });
      setMainMsg("Meeting report opened in a new tab.", false);
    } else {
      setMainMsg("Upload complete. Check the notification to open your report.", false);
    }
  } catch (e) {
    setMainMsg(e instanceof Error ? e.message : String(e));
  }
});

async function refreshStatus() {
  const res = await chrome.runtime.sendMessage({ type: "GET_STATUS" });
  statusEl.textContent = `Status: ${res.status || "idle"}`;
  updateTimerDisplay(res);
  const isActive = res.status === "recording" || res.status === "paused";
  setRecordingControls(isActive);
  if (isActive) {
    updateCaptureSources(res.captureMode);
    startTimerTick();
  } else {
    updateCaptureSources();
  }
}

async function initMain() {
  const tab = await findMeetingTab();
  if (tab?.url && isSupportedMeetingUrl(tab.url)) {
    platformEl.textContent = `Platform: ${detectPlatform(tab.url)}`;
  } else {
    platformEl.textContent = "Platform: open Meet / Teams / Zoom in this window";
  }
  await refreshStatus();
}

async function init() {
  const apiUp = await checkApiReachable();
  if (!apiUp) {
    const config = await getConfig();
    setAuthMsg(`API offline at ${config.API_URL} — start: cd apps/api && python -m app.main`);
  }
  const { ok, email } = await verifyToken();
  if (ok) {
    showMainView(email);
  } else {
    showAuthView();
  }
}

init();
