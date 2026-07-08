export const DEFAULT_CONFIG = {
  API_URL: "https://kr-ai-meeting-bot-api.onrender.com",
  FRONTEND_URL: "https://krai-omega.vercel.app",
  CHUNK_MS: 45000,
};

export interface CaptureMode {
  hasTab: boolean;
  hasMic: boolean;
}

export interface SessionState {
  meetingId: string | null;
  platform: string;
  meetingUrl: string;
  status: "idle" | "recording" | "paused" | "uploading" | "processing";
  startedAt: number | null;
  pausedAt: number | null;
  elapsedMs: number;
  tabId: number | null;
  chunks: Blob[];
  captureMode?: CaptureMode;
  pageMicActive?: boolean;
}

export async function getConfig() {
  const stored = await chrome.storage.sync.get(["API_URL", "FRONTEND_URL", "CHUNK_MS"]);
  return { ...DEFAULT_CONFIG, ...stored };
}

export async function getToken(): Promise<string | null> {
  const { token } = (await chrome.storage.local.get("token")) as { token?: string };
  return token || null;
}

export async function apiFetch(path: string, init: RequestInit = {}) {
  const config = await getConfig();
  const token = await getToken();
  const headers: Record<string, string> = {
    ...(init.headers as Record<string, string>),
  };
  if (token) headers.Authorization = `Bearer ${token}`;
  if (init.body && typeof init.body === "string" && !headers["Content-Type"]) {
    headers["Content-Type"] = "application/json";
  }
  const res = await fetch(`${config.API_URL}${path}`, { ...init, headers });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "API request failed");
  }
  return res.json();
}
