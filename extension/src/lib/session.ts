import type { SessionState } from "./config";

const SESSION_KEY = "recording_session";

export async function getSession(): Promise<SessionState> {
  const result = (await chrome.storage.session.get(SESSION_KEY)) as {
    [k: string]: SessionState | undefined;
  };
  const session = result[SESSION_KEY];
  return (
    session || {
      meetingId: null,
      platform: "unknown",
      meetingUrl: "",
      status: "idle",
      startedAt: null,
      pausedAt: null,
      elapsedMs: 0,
      tabId: null,
      chunks: [],
    }
  );
}

export async function saveSession(session: SessionState): Promise<void> {
  await chrome.storage.session.set({ [SESSION_KEY]: session });
}

export async function clearSession(): Promise<void> {
  await chrome.storage.session.remove(SESSION_KEY);
}
