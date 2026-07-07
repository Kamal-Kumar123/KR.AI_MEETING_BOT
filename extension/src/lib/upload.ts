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
  // Redirect to the KR.AI BOT website (frontend/) which renders the report via
  // ?meeting_id. The share token lets it read the meeting without login and
  // ?api tells it which backend served the recording.
  const url = new URL(`${frontendUrl.replace(/\/$/, "")}/`);
  url.searchParams.set("meeting_id", meetingId);
  if (shareToken) url.searchParams.set("share", shareToken);
  if (apiUrl) url.searchParams.set("api", apiUrl.replace(/\/$/, ""));
  return url.toString();
}
