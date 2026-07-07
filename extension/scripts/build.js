const esbuild = require("esbuild");
const fs = require("fs");
const path = require("path");

const root = path.join(__dirname, "..");
const dist = path.join(root, "dist");
fs.mkdirSync(dist, { recursive: true });

// Remove known stale artifacts from earlier builds (e.g. removed pages).
// Avoid nuking the whole dist folder — on Windows it can be locked while the
// unpacked extension is loaded in Chrome, which breaks the build.
const stale = ["mic-permission.html", "mic-permission"];
for (const rel of stale) {
  const target = path.join(dist, rel);
  if (fs.existsSync(target)) {
    fs.rmSync(target, { recursive: true, force: true, maxRetries: 5, retryDelay: 200 });
  }
}

const entries = [
  ["src/background/service-worker.ts", "background/service-worker.js"],
  ["src/popup/popup.ts", "popup/popup.js"],
  ["src/offscreen/offscreen.ts", "offscreen/offscreen.js"],
  ["src/options/options.ts", "options/options.js"],
  ["src/content/meet.ts", "content/meet.js"],
  ["src/content/zoom.ts", "content/zoom.js"],
  ["src/content/teams.ts", "content/teams.js"],
];

for (const [entry, out] of entries) {
  esbuild.buildSync({
    entryPoints: [path.join(root, entry)],
    bundle: true,
    outfile: path.join(dist, out),
    platform: "browser",
    target: ["chrome114"],
    format: "iife",
  });
}

for (const f of ["manifest.json", "popup.html", "options.html", "offscreen.html"]) {
  fs.copyFileSync(path.join(root, f), path.join(dist, f));
}

const iconsSrc = path.join(root, "icons");
const iconsDist = path.join(dist, "icons");
if (fs.existsSync(iconsSrc)) {
  fs.mkdirSync(iconsDist, { recursive: true });
  for (const file of fs.readdirSync(iconsSrc)) {
    if (file.endsWith(".png")) {
      fs.copyFileSync(path.join(iconsSrc, file), path.join(iconsDist, file));
    }
  }
} else {
  fs.mkdirSync(iconsDist, { recursive: true });
  const png = Buffer.from(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==",
    "base64"
  );
  for (const size of [16, 48, 128]) {
    fs.writeFileSync(path.join(iconsDist, `icon${size}.png`), png);
  }
}

console.log("Extension built to dist/");
