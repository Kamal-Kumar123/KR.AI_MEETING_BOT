import { registerPageMicHandlers } from "./mic-capture";

function emitMeetingEvent(event: string, platform: string) {
  chrome.runtime.sendMessage({ type: "MEETING_EVENT", event, platform, url: location.href });
}

const PLATFORM = "microsoft_teams";

function detectJoined() {
  return !!document.querySelector("[data-tid='call-screen'], .calling-screen");
}

registerPageMicHandlers();

let wasJoined = false;
setInterval(() => {
  const joined = detectJoined();
  if (joined && !wasJoined) emitMeetingEvent("meeting_started", PLATFORM);
  if (!joined && wasJoined) emitMeetingEvent("meeting_ended", PLATFORM);
  wasJoined = joined;
}, 3000);
