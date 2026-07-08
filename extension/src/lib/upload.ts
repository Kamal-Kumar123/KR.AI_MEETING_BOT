export {
  savePendingAudio,
  loadPendingAudio,
  savePageMicAudio,
  loadPageMicAudio,
} from "./session-audio";

export function buildMeetingPageUrl(
  frontendUrl: string,
  meetingId: string,
  shareToken?: string,
  apiUrl?: string
): string {
  // Redirect to the website report page. Share token allows read access without website login.
  const url = new URL(`${frontendUrl.replace(/\/$/, "")}/`);
  url.searchParams.set("meeting_id", meetingId);
  if (shareToken) url.searchParams.set("share", shareToken);
  if (apiUrl) url.searchParams.set("api", apiUrl.replace(/\/$/, ""));
  return url.toString();
}
