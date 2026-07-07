/**
 * Validates extension/dist is ready to load in Chrome (developer mode).
 * Run after: npm run build
 */
const fs = require("fs");
const path = require("path");

const dist = path.join(__dirname, "..", "dist");
const results = [];

function check(name, ok, detail = "") {
  results.push({ name, ok, detail, optional: false });
  const mark = ok ? "PASS" : "FAIL";
  console.log(`[${mark}] ${name}` + (detail ? ` - ${detail}` : ""));
}

function skip(name, detail = "") {
  results.push({ name, ok: true, detail, optional: true });
  console.log(`[SKIP] ${name}` + (detail ? ` - ${detail}` : ""));
}

function readJson(file) {
  return JSON.parse(fs.readFileSync(file, "utf8"));
}

function main() {
  if (!fs.existsSync(dist)) {
    console.error("dist/ not found. Run: npm run build");
    process.exit(1);
  }

  const manifestPath = path.join(dist, "manifest.json");
  check("manifest.json exists", fs.existsSync(manifestPath));
  if (!fs.existsSync(manifestPath)) {
    summarize();
    process.exit(1);
  }

  const manifest = readJson(manifestPath);
  check("manifest_version is 3", manifest.manifest_version === 3, String(manifest.manifest_version));
  check("service_worker declared", Boolean(manifest.background?.service_worker));
  check("popup declared", Boolean(manifest.action?.default_popup));

  const sw = manifest.background?.service_worker;
  if (sw) check(`service worker file: ${sw}`, fs.existsSync(path.join(dist, sw)));

  const popup = manifest.action?.default_popup;
  if (popup) check(`popup file: ${popup}`, fs.existsSync(path.join(dist, popup)));

  if (manifest.options_page) {
    check(`options page: ${manifest.options_page}`, fs.existsSync(path.join(dist, manifest.options_page)));
  }

  for (const [size, iconPath] of Object.entries(manifest.icons || {})) {
    check(`icon ${size}px: ${iconPath}`, fs.existsSync(path.join(dist, iconPath)));
  }

  for (const cs of manifest.content_scripts || []) {
    for (const js of cs.js || []) {
      check(`content script: ${js}`, fs.existsSync(path.join(dist, js)), (cs.matches || []).join(", "));
    }
  }

  const perms = manifest.permissions || [];
  const requiredPerms = ["storage", "tabCapture", "offscreen", "notifications"];
  for (const p of requiredPerms) {
    check(`permission: ${p}`, perms.includes(p));
  }

  const hosts = manifest.host_permissions || [];
  check("localhost API host", hosts.some((h) => h.includes("localhost:8000")));
  check("meet.google.com host", hosts.some((h) => h.includes("meet.google.com")));

  const oauthId = manifest.oauth2?.client_id || "";
  const oauthConfigured = oauthId && !oauthId.startsWith("YOUR_GOOGLE");
  if (oauthConfigured) {
    check("Google OAuth client_id configured", true, "set");
  } else {
    skip(
      "Google OAuth client_id configured",
      "optional — email/password login works; set oauth2.client_id in manifest.json for Google login"
    );
  }

  summarize();
  const hardFails = results.filter((r) => !r.ok && !r.optional);
  process.exit(hardFails.length ? 1 : 0);
}

function summarize() {
  const passed = results.filter((r) => r.ok && !r.optional).length;
  const skipped = results.filter((r) => r.optional).length;
  const failed = results.filter((r) => !r.ok).length;
  console.log(`\n${"=".repeat(50)}`);
  console.log(`TOTAL: ${passed} passed, ${skipped} skipped, ${failed} failed / ${results.length}`);
}

main();
