import { registerPageMicHandlers } from "./mic-capture";

function emitMeetingEvent(event: string, platform: string) {
  chrome.runtime.sendMessage({ type: "MEETING_EVENT", event, platform, url: location.href });
}

const PLATFORM = "zoom_web";

function detectJoined() {
  return !!document.querySelector(".meeting-app, #wc-container");
}

registerPageMicHandlers();

let wasJoined = false;
setInterval(() => {
  const joined = detectJoined();
  if (joined && !wasJoined) emitMeetingEvent("meeting_started", PLATFORM);
  if (!joined && wasJoined) emitMeetingEvent("meeting_ended", PLATFORM);
  wasJoined = joined;
}, 3000);
