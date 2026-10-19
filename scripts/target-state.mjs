#!/usr/bin/env node
// Generate the target-state view of the domain from the architecture pages: each subdomain with
// the bounded context it maps to, overlaid with numbers a brainstorming session can point at and
// the measures read down the continuum (capabilities, building blocks, patterns, services, open
// considerations, the definition stage of each capability, and what is missing). Prototype for
// docs/design/target-state-view.md; nothing it writes is edited by hand.
//
// Writes, beside docs/architecture/landscape.md:
//   target-state.md               the page: the numbered map, the gaps, the patterns to elaborate
//   target-state.svg              the logical view, printable, numbers on every box
//   target-state-deployables.svg  the deployables against the same contexts (CN-006)
//   target-state.drawio           the same, editable, with the overlay on its own layers
//   target-state.json             the derived model, for tools
//
// The stage of each capability is the stage flow's (the definition ladder), never a second score:
// this script runs the stage tool with --json and reads its per-stage checks. The skills are
// optional tooling, so without one it says so in one line and exits 0, leaving what is committed.
//
// Usage: node scripts/target-state.mjs            regenerate
//        node scripts/target-state.mjs --check    exit 1 when the committed files are stale
import { existsSync, readFileSync, readdirSync, writeFileSync } from "node:fs";
import { spawnSync } from "node:child_process";
import path from "node:path";
import { fileURLToPath } from "node:url";
import yaml from "js-yaml";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const arch = path.join(root, "docs", "architecture");
// The stage flow: architecture-continuum v0.6's stage.py once this repository migrates, else aaa-rung's rung.py.
const rungPy = [path.join(root, ".agents", "skills", "architecture", "bin", "stage.py"), path.join(root, ".agents", "skills", "aaa-rung", "bin", "rung.py")].find(existsSync);
const check = process.argv.includes("--check");

if (!rungPy) {
  console.error("target-state view skipped: no stage skill is installed (npm run skills)");
  process.exit(0);
}
const python = ["python3", "python"].find((p) => spawnSync(p, ["--version"]).status === 0);
if (!python) {
  console.error("target-state view skipped: no python on PATH");
  process.exit(0);
}

// ------------------------------------------------------------------ read the pages

/** Every Markdown page under docs/architecture with a kind and an id in its front matter. */
function readPages(dir, out = new Map()) {
  for (const e of readdirSync(dir, { withFileTypes: true })) {
    const p = path.join(dir, e.name);
    if (e.isDirectory()) { if (e.name !== "dist") readPages(p, out); continue; }
    if (!e.name.endsWith(".md")) continue;
    const m = readFileSync(p, "utf8").match(/^---\r?\n([\s\S]*?)\r?\n---/);
    if (!m) continue;
    const fm = yaml.load(m[1]);
    if (!fm || !fm.kind || !fm.id) continue;
    // A service's id is its slug; numeric_id is its SV-NNN, the identifier everything else cites.
    const id = fm.kind === "service" && fm.numeric_id ? fm.numeric_id : fm.id;
    out.set(id, { ...fm, id, slug: fm.id, _path: path.relative(arch, p).split(path.sep).join("/") });
  }
  return out;
}
const pages = readPages(arch);
const ofKind = (k) => [...pages.values()].filter((p) => p.kind === k).sort((a, b) => a.id.localeCompare(b.id));
const list = (v) => (Array.isArray(v) ? v : v == null || v === "" ? [] : String(v).split(/[\s,]+/)).map(String).filter(Boolean);
const active = (p) => p && !["retired", "deprecated", "superseded", "withdrawn"].includes(p.status);
const name = (id) => { const p = pages.get(id); return p ? String(p.title || id).replace(new RegExp(`^${id}\\s*`), "") : id; };

const contexts = ofKind("bounded-context");
const caps = ofKind("capability");
const abbs = ofKind("abb");
const sbbs = ofKind("sbb");
const services = ofKind("service").map((s) => ({ ...s, context: s.part_of, composes: s.composes_contexts }));
const outcomes = ofKind("outcome");
const useCases = ofKind("use-case");
const considerations = ofKind("consideration");
// Patterns by their signature, never by name or folder: kind pattern with a pattern_type.
const patterns = ofKind("pattern").filter((p) => p.pattern_type);

// The domain and its subdomains. The continuum keeps no record of either (a domain is the
// platform's purpose and a context's subdomain_kind), so the only source is the table on the
// domain page. That is a finding of the investigation, and the first thing the method should fix.
const domainsMd = readFileSync(path.join(arch, "demand", "domains.md"), "utf8");
const domainName = (domainsMd.match(/The domain is ([^:.]+)[:.]/) || [, "the domain"])[1].trim();
const subdomains = [];
{
  const lines = domainsMd.split(/\r?\n/);
  const head = lines.findIndex((l) => /^\|\s*Subdomain\s*\|/.test(l));
  const cols = lines[head].split("|").slice(1, -1).map((c) => c.trim());
  for (const l of lines.slice(head + 2)) {
    if (!l.startsWith("|")) break;
    const cells = l.split("|").slice(1, -1).map((c) => c.trim());
    const row = Object.fromEntries(cols.map((c, i) => [c, cells[i]]));
    subdomains.push({ name: row["Subdomain"], need: row["What is needed"], kind: row["Kind"], contexts: (row["Maps to"].match(/BC-\d{3}/g) || []) });
  }
}
const kindOrder = ["core", "supporting", "generic"];
subdomains.sort((a, b) => kindOrder.indexOf(a.kind) - kindOrder.indexOf(b.kind));
subdomains.forEach((s, i) => (s.n = i + 1));

// The definition stage of every capability, from the stage tool.
const rung = spawnSync(python, [rungPy, "--json"], { cwd: root, encoding: "utf8" });
if (rung.status !== 0) { console.error(rung.stderr); process.exit(rung.status || 1); }
const ladder = JSON.parse(rung.stdout);
const stageOf = new Map(ladder.capabilities.map((c) => [c.id, c]));
const STAGES = ["R1", "R2", "R3", "R4", "R5", "R6"];
const stageNum = (r) => Number(String(r).slice(1));

// ------------------------------------------------------------------ map each subdomain down

// The registers, for the blocks that were folded into others and have no page any more.
function readCsv(file) {
  const rows = [];
  for (const line of readFileSync(path.join(arch, file), "utf8").split(/\r?\n/).filter(Boolean)) {
    const cells = []; let cur = "", q = false;
    for (const ch of line) { if (ch === '"') q = !q; else if (ch === "," && !q) { cells.push(cur); cur = ""; } else cur += ch; }
    rows.push([...cells, cur]);
  }
  const [head, ...body] = rows;
  return body.map((r) => Object.fromEntries(head.map((h, i) => [h, r[i] ?? ""])));
}
const abbRegister = readCsv("solution/abbs.csv");
const ucRegister = readCsv("demand/use-cases.csv");
const ctxOfAbb = new Map(abbRegister.map((a) => [a.id, a.part_of]));
const retiredAbb = new Set(abbRegister.filter((a) => a.status === "retired").map((a) => a.id));
const serviceById = new Map(services.map((s) => [s.id, s]));
// The open considerations that name a service, so a deployable spanning contexts cites the question it is part of.
const coveredBy = (sv) => considerations.filter((c) => c.consideration_status === "open" && list(c.affects).includes(sv)).map((c) => c.id).join(", ");
const view = subdomains.map((sd) => {
  const ctx = sd.contexts.map((id) => pages.get(id)).filter(Boolean);
  const ctxIds = ctx.map((c) => c.id);
  const capIds = [...new Set(ctx.flatMap((c) => list(c.realises_capabilities)))].sort();
  const ownAbbs = abbs.filter((a) => active(a) && ctxIds.includes(a.part_of)).map((a) => a.id);
  const realising = [...new Set(capIds.flatMap((id) => list(pages.get(id)?.realised_by_abbs)))].filter((id) => active(pages.get(id)));
  const borrowed = realising.filter((id) => !ownAbbs.includes(id)).sort();
  const ownSbbs = sbbs.filter((s) => active(s) && list(s.realises).some((a) => ownAbbs.includes(a))).map((s) => s.id);
  const pats = patterns.filter((p) => list(p.realises).some((c) => capIds.includes(c)));
  const scoped = pats.filter((p) => p.pattern_scope && p.pattern_scope !== "platform");
  const svOwn = services.filter((s) => ctxIds.includes(s.context)).map((s) => s.id);
  const svComposing = services.filter((s) => !ctxIds.includes(s.context) && list(s.composes).some((c) => ctxIds.includes(c))).map((s) => s.id);
  const touched = new Set([...ctxIds, ...capIds, ...ownAbbs]);
  const cnOpen = considerations.filter((c) => c.consideration_status === "open" && list(c.affects).some((a) => touched.has(a))).map((c) => c.id);
  const ocs = outcomes.filter((o) => list(o.requires_capabilities).some((c) => capIds.includes(c))).map((o) => o.id);

  const capRows = capIds.map((id) => {
    const s = stageOf.get(id);
    const passes = Object.fromEntries(STAGES.map((r) => [r, s ? (s.checks[r] || []).length === 0 : false]));
    return { id, name: name(id), held: s ? s.stage ?? s.rung : "R0", passes, blockers: s ? s.blockers : ["no capability page"], shared: contexts.filter((c) => !ctxIds.includes(c.id) && list(c.realises_capabilities).includes(id)).map((c) => c.id) };
  });
  const held = capRows.length ? capRows.map((c) => c.held).sort((a, b) => stageNum(a) - stageNum(b))[0] : "R0";

  // What is missing, each with the rule that found it. The stage blockers are the stage tool's.
  const gaps = [];
  const gap = (code, text) => gaps.push({ ref: `${sd.n}${String.fromCharCode(97 + gaps.length)}`, code, text });
  if (!ctx.length) gap("no-context", "The subdomain maps to no bounded context");
  for (const c of ctx) if (c.subdomain_kind !== sd.kind) gap("kind-mismatch", `The domain page says ${sd.kind}; ${c.id} says ${c.subdomain_kind}`);
  if (ctx.length && !ownAbbs.length) gap("no-abb", `${ctxIds.join(", ")} contains no building block of its own; its model runs inside ${borrowed.filter((a) => ctxOfAbb.get(a) !== undefined).map((a) => `${a} (${ctxOfAbb.get(a)})`).join(", ") || "nothing named"}`);
  const failing = (r) => capRows.filter((c) => stageNum(c.held) < stageNum(r) && !c.passes[r]);
  if (failing("R1").length) gap("no-demand", `${failing("R1").map((c) => c.id).join(", ")} ${failing("R1").length > 1 ? "name" : "names"} no demand on the capability page, so the stage tool holds ${failing("R1").length > 1 ? "them" : "it"} at R0 (the outcomes name them, the inverse is not written)`);
  if (failing("R2").length) gap("unbounded", `${failing("R2").map((c) => c.id).join(", ")} ${failing("R2").length > 1 ? "fail" : "fails"} R2: ${[...new Set(failing("R2").flatMap((c) => stageOf.get(c.id)?.checks.R2 || []))].map((t) => t.replace(/ CAP-\d{3}/g, " it")).join("; ")}`);
  const noOutcome = capRows.filter((c) => !outcomes.some((o) => list(o.requires_capabilities).includes(c.id))).map((c) => c.id);
  if (noOutcome.length) gap("no-outcome", `${noOutcome.join(", ")} ${noOutcome.length > 1 ? "are" : "is"} required by no outcome, so the demand ${noOutcome.length > 1 ? "they answer is" : "it answers is"} not recorded anywhere`);
  if (cnOpen.length) gap("open-consideration", `Open: ${cnOpen.map((c) => `${c} ${name(c)}`).join("; ")}. R3 needs each resolved by an accepted decision`);
  const noLogical = capRows.filter((c) => !patterns.some((p) => p.pattern_type === "architecture-pattern" && list(p.realises).includes(c.id))).map((c) => c.id);
  if (noLogical.length) gap("no-architecture-pattern", `${noLogical.join(", ")} ${noLogical.length > 1 ? "are" : "is"} realised by no architecture pattern, only by the reference architecture`);
  if (pats.length && !scoped.length) gap("platform-scope-only", `Only platform-scoped patterns (${pats.map((p) => p.id).join(", ")}) realise its capabilities; none is scoped to the subdomain`);
  const noSbb = ownAbbs.filter((a) => !sbbs.some((s) => active(s) && list(s.realises).includes(a)));
  if (noSbb.length) gap("no-sbb", `${noSbb.join(", ")} has no active solution building block`);
  if (ctx.length && !svOwn.length) gap("no-service", `No deployable is ${ctxIds.join(", ")}'s own${svComposing.length ? `; ${svComposing.join(", ")} compose${svComposing.length > 1 ? "" : "s"} it` : ""}`);
  const mixed = [...svOwn, ...svComposing].filter((id) => list(serviceById.get(id).composes).length > 1);
  if (mixed.length) gap("service-spans-contexts", mixed.map((id) => `${id} composes ${list(serviceById.get(id).composes).join(" ")} (${coveredBy(id) || "no consideration names it"})`).join("; "));
  const stale = ucRegister.flatMap((u) => list(u.realised_by_abbs).filter((a) => ctxIds.includes(ctxOfAbb.get(a)) && retiredAbb.has(a)).map((a) => `${u.id} ${a}`));
  if (stale.length) gap("register-drift", `The use-case register still cites retired blocks of this context, which the pages no longer do: ${stale.join(", ")}`);

  return {
    n: sd.n, subdomain: sd.name, kind: sd.kind, need: sd.need, contexts: ctxIds.map((id) => ({ id, name: name(id) })),
    outcomes: ocs, capabilities: capRows, held,
    measures: {
      capabilities: capIds.length, abbs_own: ownAbbs.length, abbs_borrowed: borrowed.length, sbbs: ownSbbs.length,
      architecture_patterns: pats.filter((p) => p.pattern_type === "architecture-pattern").length,
      reference_architectures: pats.filter((p) => p.pattern_type === "reference-architecture").length,
      patterns_scoped: scoped.length, services_own: svOwn.length, services_composing: svComposing.length, considerations_open: cnOpen.length, gaps: gaps.length,
    },
    ids: { abbs_own: ownAbbs, abbs_borrowed: borrowed, sbbs: ownSbbs, patterns: pats.map((p) => p.id), services_own: svOwn, services_composing: svComposing, considerations_open: cnOpen },
    gaps,
  };
});

// ------------------------------------------------------------------ patterns to elaborate next

// A suggestion is a pattern the gaps say is missing, ranked by the subdomain's kind (core first),
// then by how many gaps it would close. Patterns already in the catalogue with a portfolio block
// (t-vq6's signature) are listed with their state so a session sees what is already planned.
const weight = { core: 3, supporting: 2, generic: 1 };
const suggestions = [];
for (const v of view) {
  const codes = new Set(v.gaps.map((g) => g.code));
  const closes = (...cs) => v.gaps.filter((g) => cs.includes(g.code)).map((g) => g.ref);
  if (codes.has("no-abb") || codes.has("platform-scope-only") || codes.has("open-consideration")) {
    suggestions.push({
      kind: "architecture-pattern", scope: "domain", box: v.n, title: `${v.subdomain}: the ${v.contexts.map((c) => c.name).join(" and ")} context as an architecture pattern`,
      realises: v.capabilities.map((c) => c.id),
      why: [codes.has("no-abb") && "names the context's own building blocks, which the catalogue lacks", codes.has("platform-scope-only") && "scopes a logical pattern to the subdomain rather than the platform", codes.has("open-consideration") && `is where ${v.ids.considerations_open.join(" and ")} ${v.ids.considerations_open.length > 1 ? "are" : "is"} argued in boxes`].filter(Boolean).join("; "),
      closes: closes("no-abb", "platform-scope-only", "open-consideration"), score: weight[v.kind] * 10 + closes("no-abb", "platform-scope-only", "open-consideration").length,
    });
  }
  if (codes.has("no-architecture-pattern")) {
    const ids = v.gaps.find((g) => g.code === "no-architecture-pattern").text.match(/CAP-\d{3}/g);
    if (!suggestions.some((s) => s.box === v.n && s.kind === "architecture-pattern")) {
      suggestions.push({ kind: "architecture-pattern", scope: "capability-area", box: v.n, title: `${ids.map(name).join(" and ")}: the logical pattern behind the reference architecture`, realises: ids, why: "the capability reaches the physical pattern without a logical one, so its blocks are named only as products", closes: closes("no-architecture-pattern"), score: weight[v.kind] * 10 + 1 });
    } else suggestions.find((s) => s.box === v.n).closes.push(...closes("no-architecture-pattern"));
  }
}
// A capability realised in more than one subdomain is a capability-area pattern of its own.
for (const c of caps.filter((c) => c.level !== "L1")) {
  const boxes = view.filter((v) => v.capabilities.some((r) => r.id === c.id));
  if (boxes.length > 1) suggestions.push({ kind: "architecture-pattern", scope: "capability-area", box: boxes.map((b) => b.n).join("+"), title: `${name(c.id)} across ${boxes.map((b) => b.subdomain).join(", ")}`, realises: [c.id], why: `the capability is realised in ${boxes.length} contexts, and no pattern says how they divide it`, closes: [], score: Math.max(...boxes.map((b) => weight[b.kind])) * 10 - 5 });
}
// An open consideration about the deployables is answered by a physical pattern for the target.
for (const cn of considerations.filter((c) => c.consideration_status === "open" && list(c.affects).some((a) => a.startsWith("SV-")))) {
  const boxes = view.filter((v) => v.ids.considerations_open.includes(cn.id));
  suggestions.push({ kind: "reference-architecture", scope: "platform", box: boxes.map((b) => b.n).join("+"), title: `The deployables of the target state: ${name(cn.id)}`, realises: [], why: `a reference architecture variant per option of ${cn.id}, so the choice is made between drawn alternatives`, closes: boxes.flatMap((b) => b.gaps.filter((g) => g.code === "service-spans-contexts").map((g) => g.ref)), score: 25 });
}
suggestions.sort((a, b) => b.score - a.score || String(a.box).localeCompare(String(b.box), undefined, { numeric: true }));
suggestions.forEach((s, i) => (s.ref = `P${i + 1}`));
const portfolio = patterns.filter((p) => p.portfolio).map((p) => ({ id: p.id, ...p.portfolio }));

// ------------------------------------------------------------------ the deployables

const ctxColumns = view.flatMap((v) => v.contexts.map((c) => ({ ...c, n: v.n, kind: v.kind })));
const deployables = services.map((s) => ({ id: s.id, name: name(s.id), kind: s.kind, owner: s.context, composes: list(s.composes).length ? list(s.composes) : [s.context], considerations: coveredBy(s.id) }));

// ------------------------------------------------------------------ render

const esc = (s) => String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
const clip = (s, n) => (s.length > n ? s.slice(0, n - 1).trimEnd() + "…" : s);
const SANS = "IBM Plex Sans, Helvetica, Arial, sans-serif";
const MONO = "IBM Plex Mono, ui-monospace, Consolas, monospace";
const band = {
  core: { fill: "#e7f6fc", stroke: "#007fa0", ink: "#004e64", chip: "#007fa0", label: "Core", blurb: "What makes the store different" },
  supporting: { fill: "#eef0ff", stroke: "#4f46e5", ink: "#352da5", chip: "#4f46e5", label: "Supporting", blurb: "Needed and built here, not the difference" },
  generic: { fill: "#eef1f6", stroke: "#525c74", ink: "#2c3342", chip: "#525c74", label: "Generic", blurb: "Could be any organisation's" },
};
const GAP = { fill: "#fff4e5", stroke: "#b45309", ink: "#7c2d12" };

const W = 840, GUT = 16, CARD = (W - 32 - 3 * GUT) / 2;
const cardHeight = (v) => 96 + v.capabilities.length * 22 + 70;
function layout() {
  let y = 84; const bands = [], cards = [];
  for (const k of kindOrder) {
    const items = view.filter((v) => v.kind === k); if (!items.length) continue;
    const top = y; y += 56;
    for (let i = 0; i < items.length; i += 2) {
      const row = items.slice(i, i + 2), h = Math.max(...row.map(cardHeight));
      row.forEach((v, j) => cards.push({ v, x: 16 + GUT + j * (CARD + GUT), y, w: CARD, h }));
      y += h + GUT;
    }
    bands.push({ k, y: top, h: y - top }); y += GUT;
  }
  return { bands, cards, height: y };
}

function logicalSvg() {
  const { bands, cards, height } = layout();
  const H = height + 120; const o = [];
  o.push(`<?xml version="1.0" encoding="UTF-8"?>`);
  o.push(`<svg xmlns="http://www.w3.org/2000/svg" width="${W}" height="${H}" viewBox="0 0 ${W} ${H}" role="img" aria-labelledby="title desc">`);
  o.push(`<title id="title">The target state of ${esc(domainName)}, by subdomain, with the numbers overlay</title>`);
  o.push(`<desc id="desc">${esc(view.map((v) => `Box ${v.n}, ${v.subdomain} (${v.kind}, ${v.contexts.map((c) => c.id).join(" ")}): ${v.measures.capabilities} capabilities, lowest stage ${v.held}, ${v.measures.gaps} gaps`).join(". "))}.</desc>`);
  o.push(`<text x="0" y="24" fill="#1b202c" font-family="${SANS}" font-size="22" font-weight="600">${esc(domainName[0].toUpperCase() + domainName.slice(1))}: the target state</text>`);
  o.push(`<text x="0" y="48" fill="#525c74" font-family="${SANS}" font-size="14">Generated from the pages. Box numbers are for pointing at; the ladder is the stage tool's, R1 to R6.</text>`);
  o.push(`<rect x="0" y="68" width="${W}" height="${height - 52}" rx="16" fill="#f5f7fb" stroke="#d5dbe9" stroke-width="1.25"/>`);
  for (const b of bands) {
    const c = band[b.k];
    o.push(`<rect x="16" y="${b.y}" width="${W - 32}" height="${b.h - GUT}" rx="12" fill="${c.fill}"/>`);
    o.push(`<rect x="32" y="${b.y + 16}" width="${c.label.length * 8 + 26}" height="24" rx="12" fill="${c.chip}"/>`);
    o.push(`<text x="${32 + (c.label.length * 8 + 26) / 2}" y="${b.y + 32.3}" fill="#ffffff" font-family="${SANS}" font-size="12" font-weight="600" text-anchor="middle">${c.label}</text>`);
    o.push(`<text x="${32 + c.label.length * 8 + 38}" y="${b.y + 33}" fill="${c.ink}" font-family="${SANS}" font-size="14">${esc(c.blurb)}</text>`);
  }
  for (const { v, x, y, w, h } of cards) {
    const c = band[v.kind];
    o.push(`<g id="box-${v.n}">`);
    o.push(`<rect x="${x}" y="${y}" width="${w}" height="${h}" rx="10" fill="#ffffff" stroke="${c.stroke}" stroke-width="1.25"/>`);
    o.push(`<circle cx="${x + 26}" cy="${y + 26}" r="14" fill="${c.chip}"/><text x="${x + 26}" y="${y + 31}" fill="#ffffff" font-family="${SANS}" font-size="14" font-weight="700" text-anchor="middle">${v.n}</text>`);
    o.push(`<text x="${x + 50}" y="${y + 24}" fill="#1b202c" font-family="${SANS}" font-size="15" font-weight="600">${esc(v.subdomain)}</text>`);
    o.push(`<text x="${x + 50}" y="${y + 42}" fill="${c.ink}" font-family="${MONO}" font-size="12" font-weight="600">${esc(v.contexts.map((k) => k.id).join(" "))}<tspan fill="#525c74" font-family="${SANS}" font-weight="500"> ${esc(v.contexts.map((k) => k.name).join(", "))}</tspan></text>`);
    if (v.gaps.length) {
      o.push(`<rect x="${x + w - 74}" y="${y + 12}" width="62" height="22" rx="11" fill="${GAP.fill}" stroke="${GAP.stroke}"/>`);
      o.push(`<text x="${x + w - 43}" y="${y + 27.5}" fill="${GAP.ink}" font-family="${SANS}" font-size="12" font-weight="600" text-anchor="middle">${v.gaps.length} gap${v.gaps.length > 1 ? "s" : ""}</text>`);
    }
    let cy = y + 70;
    o.push(`<text x="${x + 16}" y="${cy}" fill="#7e8aa7" font-family="${SANS}" font-size="11" font-weight="600">CAPABILITY</text>`);
    o.push(`<text x="${x + w - 172}" y="${cy}" fill="#7e8aa7" font-family="${SANS}" font-size="11" font-weight="600">R1 R2 R3 R4 R5 R6</text>`);
    o.push(`<text x="${x + w - 16}" y="${cy}" fill="#7e8aa7" font-family="${SANS}" font-size="11" font-weight="600" text-anchor="end">HELD</text>`);
    for (const r of v.capabilities) {
      cy += 22;
      o.push(`<text x="${x + 16}" y="${cy}" fill="#2c3342" font-family="${SANS}" font-size="12"><tspan font-family="${MONO}" font-weight="600" fill="${c.ink}">${r.id}</tspan> ${esc(clip(r.name, r.shared.length ? 19 : 22))}${r.shared.length ? `<tspan fill="#7e8aa7"> +${r.shared.length}</tspan>` : ""}</text>`);
      STAGES.forEach((s, i) => {
        const pass = r.passes[s], counted = stageNum(s) <= stageNum(r.held);
        const fill = counted ? c.chip : pass ? "#c9d3e3" : "#ffffff";
        o.push(`<rect x="${x + w - 172 + i * 20}" y="${cy - 10}" width="14" height="12" rx="2" fill="${fill}" stroke="${pass || counted ? "none" : "#7e8aa7"}"/>`);
      });
      o.push(`<text x="${x + w - 16}" y="${cy}" fill="#1b202c" font-family="${MONO}" font-size="12" font-weight="600" text-anchor="end">${r.held}</text>`);
    }
    const m = v.measures;
    cy = y + h - 52;
    o.push(`<line x1="${x + 16}" y1="${cy - 14}" x2="${x + w - 16}" y2="${cy - 14}" stroke="#e4e9f2" stroke-width="1"/>`);
    o.push(`<text x="${x + 16}" y="${cy + 2}" fill="#525c74" font-family="${SANS}" font-size="12"><tspan font-weight="600" fill="#1b202c">ABB</tspan> ${m.abbs_own}+${m.abbs_borrowed}  <tspan font-weight="600" fill="#1b202c">SBB</tspan> ${m.sbbs}  <tspan font-weight="600" fill="#1b202c">AP</tspan> ${m.architecture_patterns}  <tspan font-weight="600" fill="#1b202c">RA</tspan> ${m.reference_architectures}  <tspan font-weight="600" fill="#1b202c">SV</tspan> ${m.services_own}+${m.services_composing}  <tspan font-weight="600" fill="#1b202c">CN</tspan> ${m.considerations_open}</text>`);
    // The gap references, wrapped onto two lines; the page has the text of each.
    const lines = [""];
    for (const g of v.gaps.map((g) => `${g.ref} ${g.code}`)) { const l = lines.length - 1; if ((lines[l] + "  " + g).length > 62 && lines[l]) lines.push(g); else lines[l] = lines[l] ? `${lines[l]}  ${g}` : g; }
    lines.slice(0, 2).forEach((l, i) => o.push(`<text x="${x + 16}" y="${cy + 20 + i * 16}" fill="${GAP.ink}" font-family="${SANS}" font-size="11">${esc(i === 1 && lines.length > 2 ? clip(l, 58) + " …" : l)}</text>`));
    o.push(`</g>`);
  }
  const ly = height + 8;
  o.push(`<text x="0" y="${ly + 16}" fill="#1b202c" font-family="${SANS}" font-size="13" font-weight="600">Reading a box</text>`);
  o.push(`<rect x="0" y="${ly + 30}" width="14" height="12" rx="2" fill="#007fa0"/><text x="20" y="${ly + 40}" fill="#2c3342" font-family="${SANS}" font-size="12">stage held (this and every stage below evidenced)</text>`);
  o.push(`<rect x="300" y="${ly + 30}" width="14" height="12" rx="2" fill="#c9d3e3"/><text x="320" y="${ly + 40}" fill="#2c3342" font-family="${SANS}" font-size="12">own check passes, not counted (latent)</text>`);
  o.push(`<rect x="580" y="${ly + 30}" width="14" height="12" rx="2" fill="#ffffff" stroke="#7e8aa7"/><text x="600" y="${ly + 40}" fill="#2c3342" font-family="${SANS}" font-size="12">check fails</text>`);
  o.push(`<text x="0" y="${ly + 64}" fill="#2c3342" font-family="${SANS}" font-size="12">ABB own+borrowed from another context · SBB solution building blocks · AP architecture patterns</text>`);
  o.push(`<text x="0" y="${ly + 82}" fill="#2c3342" font-family="${SANS}" font-size="12">RA reference architectures · SV services own+composing · CN open considerations</text>`);
  o.push(`<text x="0" y="${ly + 100}" fill="#2c3342" font-family="${SANS}" font-size="12">+n beside a capability: realised in n other contexts too. Gap references (3a, 3b) are on the page with the rule that found each.</text>`);
  o.push(`</svg>`);
  return o.join("\n") + "\n";
}

function deployablesSvg() {
  const left = 230, col = 74, rowH = 30, top = 120;
  const width = left + ctxColumns.length * col + 120, H = top + deployables.length * rowH + 80;
  const o = [];
  o.push(`<?xml version="1.0" encoding="UTF-8"?>`);
  o.push(`<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${H}" viewBox="0 0 ${width} ${H}" role="img" aria-labelledby="title desc">`);
  o.push(`<title id="title">The deployables against the bounded contexts of the target state</title>`);
  o.push(`<desc id="desc">${esc(deployables.map((d) => `${d.id} ${d.name} is owned by ${d.owner} and composes ${d.composes.join(" ")}`).join(". "))}.</desc>`);
  o.push(`<text x="0" y="24" fill="#1b202c" font-family="${SANS}" font-size="22" font-weight="600">The deployables against the same contexts</text>`);
  o.push(`<text x="0" y="48" fill="#525c74" font-family="${SANS}" font-size="14">A filled dot is the context a service is part of; a ring is a context it composes besides. One dot per row is the rule; the CN that names a row is beside its count.</text>`);
  ctxColumns.forEach((c, i) => {
    const x = left + i * col + col / 2, b = band[c.kind];
    o.push(`<circle cx="${x}" cy="${top - 46}" r="12" fill="${b.chip}"/><text x="${x}" y="${top - 41.5}" fill="#ffffff" font-family="${SANS}" font-size="12" font-weight="700" text-anchor="middle">${c.n}</text>`);
    o.push(`<text x="${x}" y="${top - 18}" fill="${b.ink}" font-family="${MONO}" font-size="11" font-weight="600" text-anchor="middle">${c.id}</text>`);
  });
  o.push(`<text x="${left + ctxColumns.length * col + 16}" y="${top - 18}" fill="#7e8aa7" font-family="${SANS}" font-size="11" font-weight="600">CONTEXTS</text>`);
  deployables.forEach((d, r) => {
    const y = top + r * rowH, bad = d.composes.length > 1;
    if (r % 2 === 0) o.push(`<rect x="0" y="${y - 8}" width="${width}" height="${rowH}" fill="#f5f7fb"/>`);
    o.push(`<text x="8" y="${y + 11}" fill="#1b202c" font-family="${SANS}" font-size="12"><tspan font-family="${MONO}" font-weight="600">${d.id}</tspan> ${esc(clip(d.name, 22))}</text>`);
    ctxColumns.forEach((c, i) => {
      const x = left + i * col + col / 2, b = band[c.kind];
      if (c.id === d.owner) o.push(`<circle cx="${x}" cy="${y + 7}" r="7" fill="${b.chip}"/>`);
      else if (d.composes.includes(c.id)) o.push(`<circle cx="${x}" cy="${y + 7}" r="6" fill="#ffffff" stroke="${bad ? GAP.stroke : b.chip}" stroke-width="2"/>`);
    });
    o.push(`<text x="${left + ctxColumns.length * col + 16}" y="${y + 11}" fill="${bad ? GAP.ink : "#525c74"}" font-family="${SANS}" font-size="12" font-weight="${bad ? 600 : 400}">${d.composes.length}${bad ? ` (${d.considerations || "no CN"})` : ""}</text>`);
  });
  o.push(`</svg>`);
  return o.join("\n") + "\n";
}

// draw.io: one page per view; on the logical page the structure, the numbers and the gaps are
// separate layers, so a session can hide the overlay or draw over it. Identifiers sit on <object>
// attributes as the model skill's contract asks, since cell ids do not survive copy and paste.
function drawio() {
  const { cards } = layout(); let id = 10; const cells = [], dep = [];
  const xa = (s) => esc(s).replace(/\n/g, "&#xa;");
  const cell = (into, layer, label, style, x, y, w, h, attrs = {}) => {
    const a = Object.entries(attrs).map(([k, v]) => ` ${k}="${xa(v)}"`).join("");
    into.push(`<object id="c${id++}" label="${xa(label)}"${a}><mxCell style="${style}" vertex="1" parent="${layer}"><mxGeometry x="${x}" y="${y}" width="${w}" height="${h}" as="geometry"/></mxCell></object>`);
  };
  for (const { v, x, y, w, h } of cards) {
    const b = band[v.kind];
    cell(cells, "structure", `${v.subdomain}\n${v.contexts.map((c) => `${c.id} ${c.name}`).join("\n")}\n${v.capabilities.map((c) => `${c.id} ${c.name}`).join("\n")}`, `rounded=1;whiteSpace=wrap;html=0;align=left;verticalAlign=top;spacingLeft=44;spacingTop=8;fillColor=#FFFFFF;strokeColor=${b.stroke};fontColor=#1B202C;fontSize=13;`, x, y, w, h, { subdomain: v.subdomain, subdomain_kind: v.kind, bc_id: v.contexts.map((c) => c.id).join(" ") });
    cell(cells, "numbers", String(v.n), `ellipse;whiteSpace=wrap;html=1;fillColor=${b.chip};strokeColor=none;fontColor=#FFFFFF;fontSize=14;fontStyle=1;`, x + 10, y + 10, 32, 32, { local_id: String(v.n) });
    const m = v.measures;
    cell(cells, "numbers", `${v.held} lowest · ABB ${m.abbs_own}+${m.abbs_borrowed} · SBB ${m.sbbs} · AP ${m.architecture_patterns} · RA ${m.reference_architectures} · SV ${m.services_own}+${m.services_composing} · CN ${m.considerations_open}`, "text;html=0;align=left;fontSize=11;fontColor=#525C74;", x + 12, y + h - 28, w - 24, 20);
    if (v.gaps.length) cell(cells, "gaps", v.gaps.map((g) => `${g.ref} ${g.code}`).join("\n"), `shape=note;size=12;whiteSpace=wrap;html=0;align=left;verticalAlign=top;spacingLeft=6;fillColor=${GAP.fill};strokeColor=${GAP.stroke};fontColor=${GAP.ink};fontSize=11;`, x + w - 150, y + 8, 140, 16 + v.gaps.length * 14);
  }
  const left = 230, col = 74, rowH = 30, top = 80;
  ctxColumns.forEach((c, i) => cell(dep, "dstructure", `${c.n}\n${c.id}`, `rounded=1;whiteSpace=wrap;html=0;fillColor=${band[c.kind].fill};strokeColor=${band[c.kind].stroke};fontSize=11;`, left + i * col + 4, top - 50, col - 8, 40, { bc_id: c.id }));
  deployables.forEach((d, r) => {
    const y = top + r * rowH;
    cell(dep, "dstructure", `${d.id} ${d.name}`, "text;html=0;align=left;fontSize=12;", 0, y, left - 10, 24, { sv_id: d.id });
    ctxColumns.forEach((c, i) => {
      if (c.id === d.owner) cell(dep, "dstructure", "", `ellipse;fillColor=${band[c.kind].chip};strokeColor=none;`, left + i * col + col / 2 - 7, y + 5, 14, 14);
      else if (d.composes.includes(c.id)) cell(dep, "doverlay", "", `ellipse;fillColor=#FFFFFF;strokeColor=${GAP.stroke};strokeWidth=2;`, left + i * col + col / 2 - 6, y + 6, 12, 12);
    });
  });
  const page = (pid, title, layers, body) => `  <diagram id="${pid}" name="${title}">\n    <mxGraphModel grid="1" gridSize="8" page="0"><root><mxCell id="0"/>${layers.map(([lid, ln]) => `<mxCell id="${lid}" value="${ln}" parent="0"/>`).join("")}\n${body.map((b) => "      " + b).join("\n")}\n    </root></mxGraphModel>\n  </diagram>`;
  return `<mxfile host="target-state.mjs">\n${page("logical", "Logical: subdomains and contexts", [["structure", "Structure"], ["numbers", "Numbers"], ["gaps", "Gaps"]], cells)}\n${page("deployables", "Deployables against contexts", [["dstructure", "Structure"], ["doverlay", "Composed contexts (CN-006)"]], dep)}\n</mxfile>\n`;
}

function page() {
  const o = [];
  const link = (id) => { const p = pages.get(id); return p ? `[${id}](${p._path})` : id; };
  o.push(`---\ntitle: "Target state by subdomain"\n---\n`);
  o.push(`<!-- Generated by scripts/target-state.mjs from the architecture pages and the aaa-rung skill's stages. Do not edit; regenerate. -->\n`);
  o.push(`# Target state by subdomain\n`);
  o.push(`The target state of ${domainName} is every subdomain on the [domain page](demand/domains.md) solved: each mapped through its bounded context to capabilities, building blocks, patterns and services, and each capability at the stage the [definition ladder](https://github.com/dermot-obrien/architecture-continuum/blob/main/standards/capabilities/standard-definition-ladder.md) calls buildable or beyond. This page is generated from the pages by \`node scripts/target-state.mjs\`; the reasoning behind it is the design note [Target-state view by subdomain](../design/target-state-view.md). The numbers are for pointing at in a session: a box is its subdomain's number, a gap is the box number and a letter, a pattern to elaborate is P and a number.\n`);
  o.push(`![${esc(`The target state of ${domainName}: ${view.length} subdomains in core, supporting and generic bands, each a numbered box with its context, its capabilities and their stage on the definition ladder, its measures and its gaps`)}](./target-state.svg)\n`);
  // A Markdown table cell: escape backslashes first, then the pipes that would end the cell.
  const cell = (t) => String(t).replace(/\\/g, "\\\\").replace(/\|/g, "\\|");
  o.push(`## The numbered map\n`);
  o.push(`| Box | Subdomain | Kind | Context | Outcomes | Capabilities | Lowest stage | ABB own+borrowed | SBB | AP | RA | SV own+composing | Open CN | Gaps |`);
  o.push(`|---|---|---|---|---|---|---|---|---|---|---|---|---|---|`);
  for (const v of view) {
    const m = v.measures;
    o.push(`| ${v.n} | ${v.subdomain} | ${v.kind} | ${v.contexts.map((c) => link(c.id)).join(", ")} | ${v.outcomes.join(", ")} | ${v.capabilities.map((c) => c.id).join(", ")} | ${v.held} | ${m.abbs_own}+${m.abbs_borrowed} | ${m.sbbs} | ${m.architecture_patterns} | ${m.reference_architectures} | ${m.services_own}+${m.services_composing} | ${m.considerations_open} | ${m.gaps} |`);
  }
  o.push(`\nThe lowest stage is the lowest held by any of the box's capabilities, as the stage tool derives it; a capability realised in more than one context counts in each. Borrowed building blocks realise the box's capabilities but are part of another context.\n`);
  o.push(`## Stage by capability\n`);
  o.push(`Each capability's stage and the first thing blocking the next one, from \`${path.basename(rungPy)} --json\`. A stage whose own check passes above the stage held is latent: it will count once the stages below it hold.\n`);
  o.push(`| Box | Capability | Held | Passes its own check | Blocking the next stage |`);
  o.push(`|---|---|---|---|---|`);
  for (const v of view) for (const c of v.capabilities) o.push(`| ${v.n} | ${link(c.id)} ${c.name} | ${c.held} | ${STAGES.filter((s) => c.passes[s]).join(" ") || "none"} | ${cell(c.blockers[0] || "")} |`);
  o.push(`\n## Gaps\n`);
  o.push(`| Ref | Rule | What is missing |`);
  o.push(`|---|---|---|`);
  for (const v of view) for (const g of v.gaps) o.push(`| ${g.ref} | ${g.code} | ${cell(g.text)} |`);
  o.push(`\n## Patterns to elaborate next\n`);
  o.push(`Suggested from the gaps, core subdomains first, then by the number of gaps each would close. A suggestion is a starting point for the session, not a decision; the pattern skill writes the document.\n`);
  o.push(`| Ref | Kind | Scope | Box | Pattern | Realises | Why | Closes |`);
  o.push(`|---|---|---|---|---|---|---|---|`);
  for (const s of suggestions) o.push(`| ${s.ref} | ${s.kind} | ${s.scope} | ${s.box} | ${s.title} | ${s.realises.join(", ")} | ${s.why} | ${[...new Set(s.closes)].sort().join(", ")} |`);
  o.push(`\n${portfolio.length ? `Patterns already in the portfolio: ${portfolio.map((p) => `${p.id} (${[p.state, p.priority, p.target_quarter].filter(Boolean).join(", ")})`).join("; ")}.` : "No pattern in the catalogue carries a portfolio block yet, so none is shown as planned."}\n`);
  o.push(`## The deployables against the same contexts\n`);
  o.push(`The view above is logical: subdomains and contexts, never the units that are deployed. The deployables are drawn from the same pages against the same numbered contexts, so the distance between the two is visible. This is the picture CN-006 asks about.\n`);
  o.push(`![${esc(`The ${deployables.length} services as rows against the ${ctxColumns.length} contexts as columns: a filled dot for the context a service is part of, a ring for each other context it composes`)}](./target-state-deployables.svg)\n`);
  o.push(`The editable form of both views is [target-state.drawio](./target-state.drawio), with the numbers and the gaps on their own layers, and the derived model is [target-state.json](./target-state.json).`);
  return o.join("\n") + "\n";
}

const model = { generated_by: "scripts/target-state.mjs", domain: domainName, stage_source: `${path.basename(rungPy)} --json`, subdomains: view, suggestions, portfolio, deployables };
const outputs = {
  "target-state.md": page(),
  "target-state.svg": logicalSvg(),
  "target-state-deployables.svg": deployablesSvg(),
  "target-state.drawio": drawio(),
  "target-state.json": JSON.stringify(model, null, 2) + "\n",
};
let stale = 0;
for (const [f, text] of Object.entries(outputs)) {
  const p = path.join(arch, f);
  if (check) { if (!existsSync(p) || readFileSync(p, "utf8") !== text) { console.error(`stale: docs/architecture/${f}`); stale++; } }
  else writeFileSync(p, text);
}
if (check && stale) { console.error("regenerate with: node scripts/target-state.mjs"); process.exit(1); }
console.error(`${check ? "checked" : "wrote"} the target-state view: ${view.length} subdomains, ${view.reduce((n, v) => n + v.gaps.length, 0)} gaps, ${suggestions.length} patterns to elaborate`);
