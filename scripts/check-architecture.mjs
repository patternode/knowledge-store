#!/usr/bin/env node
// Run the architecture continuum check (the aaa-continuum skill) over docs/architecture, when the
// skill is installed. The skills are optional tooling: a clone without them is complete, so this
// says so in one line and exits 0 rather than failing. Install them with: npm run skills
import { existsSync } from "node:fs";
import { spawnSync } from "node:child_process";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const skill = path.join(root, ".agents", "skills", "aaa-continuum", "bin", "continuum.mjs");
if (!existsSync(skill)) {
  console.error("architecture check skipped: the aaa-continuum skill is not installed (run `npm run skills` to install the architecture skills)");
  process.exit(0);
}
const r = spawnSync(process.execPath, [skill, "check", "--strict", ...process.argv.slice(2)], { cwd: root, stdio: "inherit" });
process.exit(r.status ?? 1);
