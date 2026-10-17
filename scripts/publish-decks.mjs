#!/usr/bin/env node
// Publish every document under docs/architecture marked deck_publish: true as a deck with a PDF,
// into site/static/decks, where each page's banner links to its slides and PDF (site/src/components/ArchitectureBanner).
// The markdown-deck skill is optional tooling: without it this says so in one line and exits 0.
// Install the skills with: npm run skills   (then npm install once in .agents/skills/markdown-deck)
// PDF export needs a browser: Edge or Chrome where installed, else MARKDOWN_DECK_BROWSER=<path to a Chromium>.
import { existsSync } from "node:fs";
import { spawnSync } from "node:child_process";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const skill = path.join(root, ".agents", "skills", "markdown-deck", "bin", "markdown-deck.mjs");
if (!existsSync(skill)) {
  console.error("deck publishing skipped: the markdown-deck skill is not installed (run `npm run skills`, then `npm install` in .agents/skills/markdown-deck)");
  process.exit(0);
}
if (!existsSync(path.join(root, ".agents", "skills", "markdown-deck", "node_modules"))) {
  console.error("deck publishing skipped: markdown-deck's packages are not installed (run `npm install` in .agents/skills/markdown-deck)");
  process.exit(0);
}
const args = ["publish", "docs/architecture", "--out", "site/static/decks", "--pdf", ...process.argv.slice(2)];
const r = spawnSync(process.execPath, [skill, ...args], { cwd: root, stdio: "inherit" });
process.exit(r.status ?? 1);
