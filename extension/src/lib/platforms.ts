export const SUPPORTED_PLATFORMS = [
  { id: "google_meet", label: "Google Meet", hostPattern: /meet\.google\.com/i },
  { id: "microsoft_teams", label: "Microsoft Teams", hostPattern: /teams\.(microsoft|live)\.com/i },
  { id: "zoom_web", label: "Zoom Web", hostPattern: /zoom\.us/i },
];

export function detectPlatform(url: string): string {
  for (const p of SUPPORTED_PLATFORMS) {
    if (p.hostPattern.test(url)) return p.id;
  }
  return "unknown";
}

export function isSupportedMeetingUrl(url: string): boolean {
  return detectPlatform(url) !== "unknown";
}
