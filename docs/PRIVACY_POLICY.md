# Privacy Policy (Template)

**KRAI Meeting Assistant**

## What we collect

- Account email and hashed password
- Meeting audio recordings you explicitly start
- Transcripts, summaries, and action items generated from your recordings
- Meeting metadata (platform, URL, timestamps)

## How we use data

- Transcribe audio using speech-to-text
- Generate summaries and insights using AI
- Display results in your dashboard and share links you create

## Storage

- Recordings: S3-compatible object storage
- Metadata: PostgreSQL database
- Auth tokens: browser local storage (extension) / localStorage (web)

## Recording consent

The extension **never records silently**. Users must click Start Recording and receive a visible notification while recording is active.

## Deletion

Users can delete meetings via the dashboard or API. Deletion removes database records and stored audio files.

## Contact

Support: your-email@domain.com

## Updates

Last updated: 2026-07-06
