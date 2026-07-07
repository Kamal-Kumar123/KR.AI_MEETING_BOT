const fs = require("fs");
const path = require("path");

const root = __dirname.replace(/scripts$/, "");
const files = ["manifest.json", "popup.html", "options.html", "offscreen.html"];
for (const f of files) {
  fs.copyFileSync(path.join(root, f), path.join(root, "dist", f));
}
