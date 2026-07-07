import { isSupportedMeetingUrl } from "./platforms";

/** Find the meeting tab in the current window (active tab first, then any Meet/Teams/Zoom tab). */
export async function findMeetingTab(): Promise<chrome.tabs.Tab | null> {
  const [active] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (active?.id && active.url && isSupportedMeetingUrl(active.url)) return active;

  const tabs = await chrome.tabs.query({ currentWindow: true });
  return tabs.find((t) => t.id && t.url && isSupportedMeetingUrl(t.url)) ?? null;
}
