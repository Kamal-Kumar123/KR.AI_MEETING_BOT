# Chrome Web Store Submission

## Pre-submission Checklist

- [ ] `extension/dist` built with `npm run build`
- [ ] Icons 16/48/128 PNG (replace placeholders in `extension/dist/icons`)
- [ ] Privacy policy hosted at public URL
- [ ] Terms of service URL
- [ ] Support email / URL
- [ ] Screenshots (1280x800 or 640x400)
- [ ] Promotional tile 440x280

## Permissions Justification

| Permission | Why |
|------------|-----|
| `tabCapture` | Record meeting tab audio after user clicks Start |
| `offscreen` | MediaRecorder for tab audio (MV3 requirement) |
| `notifications` | Show visible recording indicator |
| `storage` | Auth token + user settings |
| `activeTab` | Detect current meeting tab |
| `scripting` | Inject platform detectors when needed |

## Privacy Policy Must Cover

- Audio is recorded only after explicit user action
- Data sent to your backend for transcription and AI analysis
- Storage location (S3 region)
- Retention and deletion (`DELETE /api/v1/meeting/{id}`)
- No sale of user data
- Compliance with Meet/Teams/Zoom terms — users must have consent to record

## Package

Zip contents of `extension/dist/` (not the repo root).

## Review Tips

- Demo video showing consent flow + notification
- Clear single purpose: meeting transcription assistant
- No broad `<all_urls>` without justification — tighten host_permissions before submit

## Developer Account

One-time $5 fee at [Chrome Web Store Developer Dashboard](https://chrome.google.com/webstore/devconsole).
