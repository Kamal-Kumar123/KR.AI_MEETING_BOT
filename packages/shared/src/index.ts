/** Shared types between extension, web, and API clients */

export type MeetingPlatform = "google_meet" | "microsoft_teams" | "zoom_web" | "unknown";

export type MeetingStatus =
  | "detecting"
  | "recording"
  | "uploading"
  | "transcribing"
  | "processing"
  | "ready"
  | "failed";

export type RecordingStatus = "pending" | "uploading" | "uploaded" | "failed";

export interface ActionItemDto {
  id?: string;
  task: string;
  owner: string;
  deadline: string;
  status?: string;
}

export interface ParticipantDto {
  id?: string;
  name: string;
  email?: string | null;
}

export interface MeetingSummaryDto {
  executive_summary: string;
  detailed_summary: string;
  bullet_summary: string[];
  key_decisions: string[];
  discussion_points: string[];
  open_questions: string[];
  risks: string[];
  next_steps: string[];
  keywords: string[];
}

export interface MeetingDto {
  id: string;
  title: string;
  platform: MeetingPlatform;
  status: MeetingStatus;
  duration_seconds: number | null;
  started_at: string | null;
  ended_at: string | null;
  recording_date: string | null;
  tags: string[];
  is_favorite: boolean;
  share_token: string | null;
  transcript: string | null;
  summary: MeetingSummaryDto | null;
  action_items: ActionItemDto[];
  participants: ParticipantDto[];
  progress_message: string | null;
}

export interface AuthTokens {
  access_token: string;
  token_type: string;
}

export interface ExtensionSettings {
  auto_upload: boolean;
  auto_summary: boolean;
  open_dashboard: boolean;
  recording_quality: "low" | "medium" | "high";
  language: string;
  notifications: boolean;
}

export const SUPPORTED_PLATFORMS: { id: MeetingPlatform; label: string; hostPattern: RegExp }[] = [
  { id: "google_meet", label: "Google Meet", hostPattern: /meet\.google\.com/i },
  { id: "microsoft_teams", label: "Microsoft Teams", hostPattern: /teams\.(microsoft|live)\.com/i },
  { id: "zoom_web", label: "Zoom Web", hostPattern: /zoom\.us/i },
];
