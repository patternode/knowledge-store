#!/usr/bin/env node
// Regenerate what the architecture pages derive, before the site is built: the diagrams and
// walkthroughs each use case and pattern document is a model of (the pattern skill's publish.py
// over the model skill), then every deck and PDF into site/static/decks (markdown-deck). The
// pages are the source; nothing here is edited by hand.
//
// The skills are optional tooling. A step whose skill is not installed is skipped in one line and
// the build goes on with what is committed, so a clone without the skills builds the same site.
// A step whose skill is installed and fails stops the build, since that is a real error in a page.
//
// Runs as npm's prebuild hook (npm run build), and on its own: node scripts/regenerate.mjs
import { existsSync } from "node:fs";
import { spawnSync } from "node:child_process";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const skills = path.join(root, ".agents", "skills");
const skip = (what, why) => console.error(`${what} skipped: ${why}`);
const run = (what, cmd, args) => {
  const r = spawnSync(cmd, args, { cwd: root, stdio: "inherit", env: process.env });
  if (r.status !== 0) {
    console.error(`${what} failed (exit ${r.status ?? "signal"}); fix the page it names, or run with REGENERATE=0 to build without regenerating`);
    process.exit(r.status || 1);
  }
};

if (process.env.REGENERATE === "0") {
  skip("regeneration", "REGENERATE=0");
  process.exit(0);
}

// 1. Diagrams, their stamped exports and the use case walkthroughs, from the documents' tables.
const publishPy = path.join(skills, "pattern", "scripts", "publish.py");
const modelPy = path.join(skills, "model", "bin", "model.py");
const python = spawnSync("python3", ["--version"]).status === 0 ? "python3" : spawnSync("python", ["--version"]).status === 0 ? "python" : null;
if (!existsSync(publishPy) || !existsSync(modelPy)) skip("diagram regeneration", "the pattern and model skills are not installed (npm run skills)");
else if (!python) skip("diagram regeneration", "no python on PATH");
else {
  for (const folder of ["docs/architecture/demand/use-cases", "docs/architecture/solution/patterns"]) {
    run(`diagram regeneration (${folder})`, python, [publishPy, folder, "--recursive", "--render", "never", "--no-deck"]);
  }
}

// 2. The target-state view by subdomain, from the pages and the aaa-rung skill's stages. It skips
// itself in one line when that skill is not installed.
run("target-state view", process.execPath, [path.join(root, "scripts", "target-state.mjs")]);

// 3. Decks and PDFs into site/static/decks, which the pages link to.
const deck = path.join(skills, "markdown-deck", "bin", "markdown-deck.mjs");
if (!existsSync(deck)) skip("deck publishing", "the markdown-deck skill is not installed (npm run skills)");
else if (!existsSync(path.join(skills, "markdown-deck", "node_modules"))) skip("deck publishing", "markdown-deck's packages are not installed (npm install in .agents/skills/markdown-deck)");
else run("deck publishing", process.execPath, [deck, "publish", "docs/architecture", "--out", "site/static/decks", "--pdf"]);
