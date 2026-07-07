import { DEFAULT_CONFIG, apiFetch, getToken } from "../lib/config";

const fields = {
  apiUrl: document.getElementById("apiUrl") as HTMLInputElement,
  frontendUrl: document.getElementById("frontendUrl") as HTMLInputElement,
  autoUpload: document.getElementById("autoUpload") as HTMLInputElement,
  autoSummary: document.getElementById("autoSummary") as HTMLInputElement,
  openDashboard: document.getElementById("openDashboard") as HTMLInputElement,
  notifications: document.getElementById("notifications") as HTMLInputElement,
  recordingQuality: document.getElementById("recordingQuality") as HTMLSelectElement,
  language: document.getElementById("language") as HTMLInputElement,
  darkMode: document.getElementById("darkMode") as HTMLInputElement,
};

async function load() {
  const data = (await chrome.storage.sync.get([
    "API_URL",
    "FRONTEND_URL",
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

document.getElementById("save")!.addEventListener("click", async () => {
  const payload = {
    API_URL: fields.apiUrl.value.trim(),
    FRONTEND_URL: fields.frontendUrl.value.trim(),
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

  const status = document.getElementById("status")!;
  status.hidden = false;
  setTimeout(() => (status.hidden = true), 2000);
});

load();
