# Install KRAI Meeting Extension (share with any Zoom host)

## For hosts — 3 steps

1. **Download** the `meet_extensiion` folder (or zip it and share)
2. Open Chrome → `chrome://extensions` → enable **Developer mode**
3. Click **Load unpacked** → select the `meet_extensiion` folder

## Before first use — set your website URLs

Edit `config.js` inside the extension folder:

```javascript
const EXTENSION_CONFIG = {
  BACKEND_URL: "https://YOUR-APP.onrender.com",
  FRONTEND_URL: "https://YOUR-APP.vercel.app",
};
```

Then click **Reload** on the extension in `chrome://extensions`.

## How hosts use it

1. Join Zoom meeting in Chrome (`zoom.us`)
2. Click extension icon → **Start Meeting Capture**
3. When meeting ends → **End Meeting & Open Share Page**
4. Website opens with summary + action items
5. Click **Copy Link**, **Email**, or **WhatsApp** to send to anyone

## Share with teammates

- Send them this folder + `INSTALL.md`
- Or zip `meet_extensiion` and share via Google Drive / email
- Each person loads it once in Chrome (Developer mode)

## Note

Live capture uses browser speech (host mic). For **all attendees' voices**, upload Zoom local recording (.mp4) on the website instead.
