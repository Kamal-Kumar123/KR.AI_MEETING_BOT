import { DEFAULT_CONFIG, apiFetch, getToken } from "../lib/config";
import {
  getExtensionClientId,
  getExtensionRedirectUri,
  signOutGoogle,
} from "../lib/google-auth";

const fields = {
  apiUrl: document.getElementById("apiUrl") as HTMLInputElement,
  frontendUrl: document.getElementById("frontendUrl") as HTMLInputElement,
  googleAskAccount: document.getElementById("googleAskAccount") as HTMLInputElement,
  extensionId: document.getElementById("extensionId") as HTMLInputElement,
  extensionClientId: document.getElementById("extensionClientId") as HTMLInputElement,
  redirectUri: document.getElementById("redirectUri") as HTMLInputElement,
  autoUpload: document.getElementById("autoUpload") as HTMLInputElement,
  autoSummary: document.getElementById("autoSummary") as HTMLInputElement,
  openDashboard: document.getElementById("openDashboard") as HTMLInputElement,
  notifications: document.getElementById("notifications") as HTMLInputElement,
  recordingQuality: document.getElementById("recordingQuality") as HTMLSelectElement,
  language: document.getElementById("language") as HTMLInputElement,
  darkMode: document.getElementById("darkMode") as HTMLInputElement,
};

const googleAuthStatus = document.getElementById("googleAuthStatus")!;
const statusEl = document.getElementById("status")!;

function showStatus(text: string, isError = false) {
  statusEl.textContent = text;
  statusEl.className = isError ? "status error" : "status";
  statusEl.hidden = false;
  setTimeout(() => (statusEl.hidden = true), 2500);
}

async function refreshGoogleAuthStatus() {
  const { userEmail, token } = (await chrome.storage.local.get(["userEmail", "token"])) as {
    userEmail?: string;
    token?: string;
  };

  if (token && userEmail) {
    googleAuthStatus.textContent = `Signed in as ${userEmail}`;
    googleAuthStatus.className = "auth-status signed-in";
    return;
  }
  if (token) {
    googleAuthStatus.textContent = "Signed in";
    googleAuthStatus.className = "auth-status signed-in";
    return;
  }
  googleAuthStatus.textContent = "Not signed in";
  googleAuthStatus.className = "auth-status signed-out";
}

async function load() {
  fields.extensionId.value = chrome.runtime.id;
  fields.extensionClientId.value = getExtensionClientId();
  fields.redirectUri.value = getExtensionRedirectUri();
  await refreshGoogleAuthStatus();

  const data = (await chrome.storage.sync.get([
    "API_URL",
    "FRONTEND_URL",
    "google_ask_account",
    "auto_upload",
    "auto_summary",
    "open_dashboard",
    "notifications",
    "recording_quality",
    "language",
    "dark_mode",
  ])) as Record<string, any>;

  fields.apiUrl.value = data.API_URL || DEFAULT_CONFIG.API_URL;
  fields.frontendUrl.value = data.FRONTEND_URL || DEFAULT_CONFIG.FRONTEND_URL;
  fields.googleAskAccount.checked = data.google_ask_account === true;
  fields.autoUpload.checked = data.auto_upload !== false;
  fields.autoSummary.checked = data.auto_summary !== false;
  fields.openDashboard.checked = data.open_dashboard !== false;
  fields.notifications.checked = data.notifications !== false;
  fields.recordingQuality.value = data.recording_quality || "medium";
  fields.language.value = data.language || "en-US";
  fields.darkMode.checked = data.dark_mode !== false;

  const token = await getToken();
  if (token) {
    try {
      const remote = await apiFetch("/api/v1/settings");
      fields.autoUpload.checked = remote.auto_upload;
      fields.autoSummary.checked = remote.auto_summary;
      fields.openDashboard.checked = remote.open_dashboard;
      fields.recordingQuality.value = remote.recording_quality;
      fields.language.value = remote.language;
      fields.notifications.checked = remote.notifications;
      fields.darkMode.checked = remote.dark_mode;
    } catch {
      /* use local settings */
    }
  }
}

document.getElementById("copyRedirectUri")!.addEventListener("click", async () => {
  const uri = fields.redirectUri.value;
  if (!uri) return;
  try {
    await navigator.clipboard.writeText(uri);
    showStatus("Redirect URI copied.");
  } catch {
    fields.redirectUri.select();
    document.execCommand("copy");
    showStatus("Redirect URI copied.");
  }
});

document.getElementById("googleSignOutBtn")!.addEventListener("click", async () => {
  await signOutGoogle();
  try {
    const config = await chrome.storage.sync.get(["API_URL"]);
    const apiUrl = config.API_URL || DEFAULT_CONFIG.API_URL;
    await fetch(`${apiUrl}/api/v1/auth/logout`, { method: "POST" });
  } catch {
    /* optional */
  }
  await refreshGoogleAuthStatus();
  showStatus("Signed out. Next sign-in will show account chooser if enabled.");
});

document.getElementById("save")!.addEventListener("click", async () => {
  const payload = {
    API_URL: fields.apiUrl.value.trim(),
    FRONTEND_URL: fields.frontendUrl.value.trim(),
    google_ask_account: fields.googleAskAccount.checked,
    auto_upload: fields.autoUpload.checked,
    auto_summary: fields.autoSummary.checked,
    open_dashboard: fields.openDashboard.checked,
    notifications: fields.notifications.checked,
    recording_quality: fields.recordingQuality.value,
    language: fields.language.value.trim(),
    dark_mode: fields.darkMode.checked,
  };

  await chrome.storage.sync.set(payload);

  const token = await getToken();
  if (token) {
    await apiFetch("/api/v1/settings", {
      method: "PATCH",
      body: JSON.stringify({
        auto_upload: payload.auto_upload,
        auto_summary: payload.auto_summary,
        open_dashboard: payload.open_dashboard,
        notifications: payload.notifications,
        recording_quality: payload.recording_quality,
        language: payload.language,
        dark_mode: payload.dark_mode,
      }),
    });
  }

  showStatus("Saved successfully.");
});

load();
