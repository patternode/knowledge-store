/* Knowledge Store chat. Plain ES2020, no framework, no build step.
 *
 * Answers, sources and document titles come from uploaded documents and a model, so no server
 * text ever reaches innerHTML: every node is built with h(), which sets textContent and
 * attributes only. The answer is rendered from its structured claims, never parsed as markdown.
 *
 * Sign-in, the API client and the helpers are in common.js, which the ontology page shares.
 *
 * The page opens as the chat alone. Demonstrate, in the header, shows the sample questions and
 * the workbench; User view hides them again. The choice is remembered in this browser.
 *
 * Sample questions sit to the left of the chat, grouped low, medium and high, from the collection's
 * profile (or three general ones when it has none). Choosing one fills the box and does not send it.
 *
 * The workbench (the panel beside the chat) shows the selected question's steps while the agent
 * works: each search, read and check, polled from GET /api/chat while it runs, then the ontology
 * terms the answer used, and what the question cost, split by token kind and by model call.
 * Steps, cost, ontology terms and this session are sections. They start collapsed.
 * A step is coloured by what it was: model thinking, a knowledge graph query, a vector query,
 * a keyword search, a structured lookup, a passage read, an ontology read, or a check. The list ends with a count of
 * every type, including the ones that did not happen, and of each tool that was called. A model
 * step shows how long it thought and the tokens that call reported. The cost table names each
 * model call for the tool that followed it ("Thinking, then a word search"). The step badge
 * keeps the tool's own name ("Keyword search"). The tool is not what the price pays for.
 *
 * Sources are not part of the conversation. They sit in a panel to the right of the questions
 * and answers, shown and hidden from a citation or from Sources. One source is open at a time.
 * The words the claim quotes are highlighted in the passage. A table citation shows that row,
 * with the cited cell highlighted.
 * A question has a mode: "ask" answers it; "gaps" asks the analyst what it
 * would take to answer it (ontology extensions, data, missed extraction), which a curator can keep
 * as an ontology request.
 */
function main() {
  'use strict';
  const { $, h, clear, lstore, safeUrl, sleep, str, auth, api, COLL_KEY } = window.KS;
  // ---- state ------------------------------------------------------------------------------
  const S = { collections: [], id: null, private: false, gen: 0, busy: false, turns: [], seq: 0, selected: null,
    sourceTurn: null, sourceN: null, lastCite: null };
  const HISTORY_TURNS = 6, POLL_MS = 1500, POLL_LIMIT_MS = 10 * 60 * 1000;
  const BENCH_KEY = 'ks.chat.bench';
  const DEMO_KEY = 'ks.chat.demo';
  const GRAPH_TOOLS = new Set(['search_entities', 'list_entities', 'get_entity', 'neighbourhood', 'find_paths']);
  const STRUCTURED_TOOLS = new Set(['describe_structured', 'lookup_rows', 'aggregate']);
  const SOURCE_LABEL = {
    graph: 'Knowledge graph query',
    vector: 'Vector query',
    keyword: 'Keyword passage search',
    structured: 'Structured lookup',
  };
  // Every type is counted, including the ones this question did not use.
  const STEP_TYPES = [
    ['model', 'Model thinking'],
    ['graph', 'Knowledge graph query'],
    ['vector', 'Vector query'],
    ['keyword', 'Keyword search'],
    ['structured', 'Structured lookup'],
    ['read', 'Passage read'],
    ['ontology', 'Ontology read'],
    ['check', 'Check'],
    ['repair', 'Repair'],
    ['guardrail', 'Guardrail'],
    ['other', 'Other tool'],
    ['done', 'Finished'],
    ['error', 'Stopped'],
  ];
  const STEP_LABEL = Object.fromEntries(STEP_TYPES);
  const TOKEN_KINDS = [
    ['inputTokens', 'in'],
    ['outputTokens', 'out'],
    ['cacheWriteInputTokens', 'cache write'],
    ['cacheReadInputTokens', 'cache read'],
  ];
  const secs = (ms) => `${(Number(ms || 0) / 1000).toFixed(1)} s`;
  const plural = (k, one, many) => `${k} ${k === 1 ? one : (many || one + 's')}`;

  function notice(...kids) { const n = $('#notice'); n.hidden = !kids.length; clear(n, kids); }
  function setBusy(on) {
    S.busy = on;
    $('#send').disabled = on;
    $('#coll-select').disabled = on;
    $('#question').setAttribute('aria-busy', String(on));
  }
  const announce = (text) => { const a = $('#announce'); a.textContent = ''; setTimeout(() => { a.textContent = text; }, 50); };

  // ---- quotes in a passage -------------------------------------------------------------
  // Matching follows the grounding check: case, spacing, curly quotes and dashes. Each folded
  // character remembers its index in the original, so the highlight is the passage text.
  const FOLD = {
    '\u2018': "'", '\u2019': "'", '\u201a': "'", '\u201b': "'", '\u2032': "'",
    '\u201c': '"', '\u201d': '"', '\u201e': '"', '\u2033': '"',
    '\u2010': '-', '\u2011': '-', '\u2012': '-', '\u2013': '-', '\u2014': '-',
    '\u2015': '-', '\u2212': '-', '\u00a0': ' ',
  };
  function foldChars(s) {
    let out = '';
    const map = [];
    for (let i = 0; i < s.length; i++) {
      let ch = s[i];
      if (FOLD[ch]) ch = FOLD[ch];
      else if (/[*_`#>|]/.test(ch)) ch = ' ';
      else {
        const n = ch.normalize('NFKC');
        if (n !== ch) { for (const c of n) { out += c.toLowerCase(); map.push(i); } continue; }
      }
      out += ch.toLowerCase();
      map.push(i);
    }
    return { text: out, map };
  }
  function squash(folded) {
    let out = '';
    const map = [];
    let space = false;
    for (let i = 0; i < folded.text.length; i++) {
      const ch = folded.text[i];
      if (/\s/.test(ch)) { if (!space && out.length) { out += ' '; map.push(folded.map[i]); } space = true; continue; }
      space = false;
      out += ch; map.push(folded.map[i]);
    }
    if (out.endsWith(' ')) { out = out.slice(0, -1); map.pop(); }
    return { text: out, map };
  }
  function highlight(text, quotes) {
    const src = str(text), n = squash(foldChars(src)), ranges = [], missing = [];
    for (const q of quotes) {
      const nq = squash(foldChars(str(q))).text.replace(/^[\s.,;:'"()[\]]+|[\s.,;:'"()[\]]+$/g, '');
      if (!nq) continue;
      const at = n.text.indexOf(nq);
      if (at < 0) { missing.push(str(q)); continue; }
      ranges.push([n.map[at], n.map[at + nq.length - 1] + 1]);
    }
    ranges.sort((a, b) => a[0] - b[0]);
    const merged = [];
    for (const r of ranges) {
      const last = merged[merged.length - 1];
      if (last && r[0] <= last[1]) last[1] = Math.max(last[1], r[1]); else merged.push(r.slice());
    }
    const nodes = [];
    let pos = 0;
    for (const [a, b] of merged) {
      if (a > pos) nodes.push(src.slice(pos, a));
      nodes.push(h('mark', { text: src.slice(a, b) }));
      pos = b;
    }
    if (pos < src.length) nodes.push(src.slice(pos));
    return { nodes, missing };
  }

  // ---- rendering an answer ------------------------------------------------------------
  const cardId = (turn, n) => `src-${turn.key}-${n}`;
  function citeLinks(turn, nums, known) {
    return nums.map((n) => (known.has(n)
      ? h('a', { class: 'cite', href: `#${cardId(turn, n)}`, 'aria-label': `Source ${n}`, 'aria-expanded': 'false',
        onclick: (e) => { e.preventDefault(); S.lastCite = e.currentTarget; showSource(turn, n); } }, `[${n}]`)
      : h('span', { class: 'cite dead', title: 'This source is not listed' }, `[${n}]`)));
  }
  // The agent returns numbered sources. The portal tool loop returns citations and writes
  // [p:<id>] in the answer. The numbers stay in the answer. The passages open in the sources panel.
  function groundedSources(r) {
    const listed = (Array.isArray(r.sources) ? r.sources : []).slice().sort((a, b) => (a.n || 0) - (b.n || 0));
    if (listed.length) return listed;
    const cites = (Array.isArray(r.citations) ? r.citations : []).filter((c) => c && typeof c === 'object');
    if (!cites.length) return [];
    const byId = new Map(cites.map((c) => [c.id || c.passage_id, c]));
    const order = [], seen = new Set();
    const re = /\[([pcm]):([^\]\s]+)\]/g;
    let m;
    while ((m = re.exec(str(r.answer)))) {
      const id = markerId(m[1], m[2]);
      if (!seen.has(id)) { seen.add(id); order.push(id); }
    }
    for (const id of byId.keys()) if (id && !seen.has(id)) { seen.add(id); order.push(id); }
    return order.map((id, i) => {
      const c = byId.get(id) || {};
      return { n: i + 1, passage_id: id, doc: c.doc, title: c.title, name: c.name, kind: c.kind || '',
        text: c.text || '', quotes: Array.isArray(c.quotes) ? c.quotes : [],
        row: Array.isArray(c.row) ? c.row : [] };
    });
  }
  // A passage marker is [p:<id>]. A cell id already starts with c:, so its marker is [c:c:...],
  // and the same for a metric. The id the source carries is the cell or metric id.
  function markerId(kind, rest) {
    if (kind === 'p') return rest;
    return rest.startsWith(`${kind}:`) ? rest : `${kind}:${rest}`;
  }
  function inlineParts(text, cite) {
    const out = [], re = /\[([pcm]):([^\]\s]+)\]|\*\*([^*]+)\*\*|`([^`]+)`/g;
    let last = 0, m;
    while ((m = re.exec(text))) {
      if (m.index > last) out.push(text.slice(last, m.index));
      if (m[1]) out.push(cite(markerId(m[1], m[2])));
      else if (m[3]) out.push(h('strong', { text: m[3] }));
      else out.push(h('code', { text: m[4] }));
      last = re.lastIndex;
    }
    if (last < text.length) out.push(text.slice(last));
    return out;
  }
  function proseAnswer(turn, text, sources) {
    const known = new Set(sources.map((s) => s.n));
    const nOf = new Map(sources.filter((s) => s.passage_id).map((s) => [s.passage_id, s.n]));
    const cite = (pid) => {
      const n = nOf.get(pid);
      return n != null ? citeLinks(turn, [n], known) : h('span', { class: 'cite dead', title: 'This source is not listed' }, `[${pid}]`);
    };
    const md = h('div', { class: 'answer-text md' });
    const bullet = /^\s*(?:[-*•]|\d+[.)])\s+/;
    let para = null, list = null;
    for (const raw of String(text || '').split('\n')) {
      const line = raw.trimEnd();
      if (!line.trim()) { para = list = null; continue; }
      if (/^\s*(?:[-*_]\s*){3,}$/.test(line)) { para = list = null; md.append(h('hr')); continue; }
      if (/^#{1,6}\s/.test(line)) {
        para = list = null;
        md.append(h('h4', null, inlineParts(line.replace(/^#+\s*/, ''), cite)));
        continue;
      }
      if (bullet.test(line)) {
        const tag = /^\s*\d/.test(line) ? 'ol' : 'ul';
        if (!list || list.tagName !== tag.toUpperCase()) { para = null; list = h(tag); md.append(list); }
        list.append(h('li', null, inlineParts(line.replace(bullet, ''), cite)));
        continue;
      }
      list = null;
      if (!para) { para = h('p'); md.append(para); } else para.append(h('br'));
      para.append(...inlineParts(line, cite).flat());
    }
    if (!md.childNodes.length) md.append(h('p', { text: str(text) }));
    return md;
  }
  function answerBody(turn, r, sources) {
    const known = new Set(sources.map((s) => s.n));
    const claims = Array.isArray(r.claims) ? r.claims.filter((c) => c && str(c.text).trim()) : [];
    if (!claims.length) return proseAnswer(turn, str(r.answer), sources);
    return h('p', { class: 'answer-text' }, claims.map((c, i) => [i ? ' ' : null,
      h('span', { class: 'claim' }, str(c.text).trim(), citeLinks(turn, (c.sources || []).filter((x) => x != null), known))]));
  }
  function cellTable(s) {
    const row = (Array.isArray(s.row) ? s.row : []).filter((c) => c && str(c.column));
    if (!row.length) return null;
    return h('div', { class: 'cell-row-wrap' },
      h('table', { class: 'cell-row' },
        h('thead', null, h('tr', null, row.map((c) => h('th', { scope: 'col', text: str(c.column) })))),
        h('tbody', null, h('tr', null, row.map((c) => {
          const cited = str(c.cell) === str(s.passage_id);
          const value = str(c.value);
          return h('td', { class: cited ? 'cited' : '' }, cited ? h('mark', { text: value }) : value);
        })))));
  }
  function sourceBody(turn, s, claims) {
    const quotes = [...(s.quotes || [])];
    for (const c of claims) for (const cit of c.citations || []) {
      if (!cit) continue;
      if (cit.passage_id === s.passage_id && cit.quote) quotes.push(cit.quote);
      if (cit.cell_id === s.passage_id && cit.value) quotes.push(cit.value);
    }
    const unique = [...new Set(quotes.map(str).filter((q) => q.trim()))];
    const table = s.kind === 'cell' ? cellTable(s) : null;
    const { nodes, missing } = table ? { nodes: [], missing: [] } : highlight(s.text, unique);
    const title = str(s.title || s.name || s.doc) || 'Untitled document';
    const status = h('p', { class: 'card-status', role: 'status' });
    const open = h('button', { class: 'btn', type: 'button', 'aria-label': `Open document: ${title}` }, 'Open document');
    open.addEventListener('click', () => openDocument(s.doc, open, status));
    const passage = table || (nodes.length
      ? h('blockquote', { class: 'passage' }, nodes)
      : h('p', { class: 'small muted', text: 'This source has no passage text.' }));
    return h('div', { class: 'card source-body' },
      passage,
      missing.length ? h('div', { class: 'missing' }, h('p', { text: 'Quoted from this source, not shown in the passage above:' }),
        h('ul', null, missing.map((q) => h('li', { text: q })))) : null,
      s.doc ? h('div', { class: 'card-actions' }, open, status) : null);
  }
  function setSources(open) {
    $('#sources').hidden = !open;
    $('#sources-open').setAttribute('aria-expanded', String(open));
    for (const a of document.querySelectorAll('a.cite')) a.setAttribute('aria-expanded', 'false');
    if (open && S.lastCite && S.sourceN != null) S.lastCite.setAttribute('aria-expanded', 'true');
    if (!open) {
      const back = S.lastCite && S.lastCite.isConnected ? S.lastCite : $('#sources-open');
      if (back) back.focus({ preventScroll: true });
    }
  }
  function renderSources() {
    const turn = S.sourceTurn;
    const box = $('#sources-body');
    if (!turn || !(turn.sources || []).length) { clear(box); $('#sources-q').textContent = ''; return; }
    $('#sources-q').textContent = turn.question;
    const claims = turn.claims || [];
    clear(box, turn.sources.map((s) => {
      const expanded = S.sourceN === s.n;
      const title = str(s.title || s.name || s.doc) || 'Untitled document';
      const row = h('button', { class: `source-row${expanded ? ' current' : ''}`, type: 'button', 'aria-expanded': String(expanded) },
        h('span', { class: 'num', 'aria-hidden': 'true', text: str(s.n) }),
        h('span', { class: 'source-name', text: title }));
      row.addEventListener('click', () => {
        S.sourceN = expanded ? null : s.n;
        S.lastCite = null;
        renderSources();
      });
      return h('div', { class: 'source-item', id: cardId(turn, s.n) }, row, expanded ? sourceBody(turn, s, claims) : null);
    }));
    const current = S.sourceN != null ? document.getElementById(cardId(turn, S.sourceN)) : null;
    if (!current) return;
    current.classList.add('flash');
    const markEl = current.querySelector('mark');
    const target = markEl || current;
    const delta = target.getBoundingClientRect().top - box.getBoundingClientRect().top;
    box.scrollBy({ top: delta - (markEl ? 48 : 8), behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth' });
    const row = current.querySelector('.source-row');
    if (row) row.focus({ preventScroll: true });
    setTimeout(() => current.classList.remove('flash'), 2000);
  }
  function showSource(turn, n) {
    if (!turn || !(turn.sources || []).length) return;
    const open = !$('#sources').hidden;
    if (open && S.sourceTurn === turn && S.sourceN === n && n != null) { setSources(false); return; }
    S.sourceTurn = turn;
    S.sourceN = n;
    setSources(true);
    renderSources();
    announce(n == null ? `Sources for this question, ${turn.sources.length}.` : `Source ${n}.`);
  }
  async function openDocument(doc, btn, status) {
    btn.disabled = true; status.textContent = 'Opening the document.';
    try {
      const d = await api('/document', { c: S.id, doc });
      const url = safeUrl(d && d.url);
      if (!url) { status.textContent = 'This document has no link to open.'; return; }
      const link = h('a', { href: url, target: '_blank', rel: 'noopener noreferrer' }, `Open ${str(d.title || d.name || 'the document')} in a new tab`);
      clear(status, link);
      link.click(); // the visible link stays in case the browser blocked the new tab
    } catch (e) {
      status.textContent = e.status === 404 ? 'You do not have access to this document, or it no longer exists.' : e.message;
    } finally { btn.disabled = false; }
  }
  function renderDone(turn, r) {
    const claims = Array.isArray(r.claims) ? r.claims : [];
    const sources = groundedSources(r);
    const out = [];
    if (r.blocked) {
      out.push(h('div', { class: 'refusal' }, h('p', { class: 'label', text: 'This question cannot be answered here' }), h('p', { text: str(r.answer) })));
    } else if (r.abstained) {
      const gaps = (r.gaps || []).map(str).filter((g) => g.trim());
      out.push(h('div', { class: 'abstain' }, answerBody(turn, r, sources),
        gaps.length ? [h('p', { class: 'label', text: 'What the sources don\'t cover' }), h('ul', null, gaps.map((g) => h('li', { text: g })))] : null));
    } else {
      out.push(answerBody(turn, r, sources));
    }
    turn.sources = sources;
    turn.claims = claims;
    if (sources.length) $('#sources-open').hidden = false;
    if (r.ontology_version) out.push(h('p', { class: 'meta', text: `Ontology version ${str(r.ontology_version)}` }));
    out.push(turnActions(turn));
    clear(turn.body, out);
    turn.body.classList.remove('pending');
  }
  // ---- what would it take: the analyst's report --------------------------------------------
  const VERDICT = {
    answerable: 'The graph can answer it now',
    data_missing: 'Data is missing',
    ontology_missing: 'The ontology needs extending',
    extraction_missed: 'Extraction missed it',
    out_of_scope: 'Out of scope for this collection',
  };
  const ontologyLink = (kind, name) => {
    const q = new URLSearchParams({ [kind === 'classes' ? 'class' : 'prop']: name });
    if (S.collections.length > 1) q.set('c', S.id);
    return `ontology.html?${q}`;
  };
  function reportSection(title, items) {
    return items.length ? [h('h4', { text: title }), h('ul', { class: 'report-list' }, items)] : null;
  }
  function renderReport(turn, r) {
    const rep = r.report || {}, o = rep.ontology || {};
    const li = (...kids) => h('li', null, kids);
    const why = (x) => (x.why ? h('span', { class: 'muted', text: ` Why: ${str(x.why)}` }) : null);
    const status = h('p', { class: 'card-status', role: 'status' });
    let keep = null;
    if (S.private) {
      keep = h('button', { class: 'btn', type: 'button' }, 'Keep as an ontology request');
      keep.addEventListener('click', async () => {
        keep.disabled = true; status.textContent = 'Keeping the request.';
        try {
          const k = await api('/requests', { c: S.id }, { method: 'POST', body: { question: turn.question, report: rep, ontology_version: r.ontology_version } });
          status.textContent = `Kept as request ${str(k.id)}. It joins the candidate register, so the next revision (knowledge-store candidates --propose) considers it.`;
        } catch (e) { keep.disabled = false; status.textContent = e.message; }
      });
    }
    const rewrites = (rep.rewrites || []).map((q) => li(h('button', { class: 'linkish', type: 'button',
      onclick: () => { setMode('ask'); $('#question').value = str(q); $('#question').focus(); } }, str(q))));
    clear(turn.body,
      h('div', { class: `report ${str(rep.verdict)}` },
        h('p', { class: 'label', text: VERDICT[rep.verdict] || 'Report' }),
        rep.summary ? h('p', { class: 'answer-text', text: str(rep.summary) }) : null,
        reportSection('Classes to add', (o.classes || []).map((c) => li(h('b', { text: str(c.name) }),
          c.parent ? [', a kind of ', h('a', { href: ontologyLink('classes', c.parent), text: str(c.parent) })] : null,
          `: ${str(c.definition)}`, why(c)))),
        reportSection('Relations to add', (o.relations || []).map((p) => li(h('b', { text: str(p.name) }),
          ` (${str(p.domain) || 'any'} → ${str(p.range) || 'any'}): ${str(p.definition)}`, why(p)))),
        reportSection('Attributes to add', (o.attributes || []).map((p) => li(h('b', { text: str(p.name) }),
          ` (of ${str(p.domain) || 'any'}, ${str(p.datatype) || 'string'}): ${str(p.definition)}`, why(p)))),
        reportSection('Already in the ontology', (rep.existing || []).map((x) => li(h('b', { text: str(x.term) }),
          x.kind ? ` (${str(x.kind)})` : '', x.use ? `: ${str(x.use)}` : ''))),
        reportSection('Data to add', (rep.data || []).map((x) => li(str(x.what), x.where ? h('span', { class: 'muted', text: ` Where: ${str(x.where)}` }) : null, why(x)))),
        reportSection('In the passages, missing from the graph', (rep.extraction || []).map((x) => li(str(x.what),
          x.passage_id ? h('span', { class: 'mono small muted', text: ` ${str(x.passage_id)}` }) : null, why(x)))),
        reportSection('Questions it can answer now', rewrites),
        h('div', { class: 'card-actions' }, keep,
          keep ? null : h('p', { class: 'small muted', text: 'Curators (people with private access) can keep this as an ontology request.' }), status)),
      r.ontology_version ? h('p', { class: 'meta', text: `Ontology version ${str(r.ontology_version)}` }) : null,
      turnActions(turn));
    turn.body.classList.remove('pending');
  }

  // Under every finished turn: show its steps in the workbench, and, for an answer, ask what it
  // would take to answer it better (offered first when the agent could not answer).
  function turnActions(turn) {
    const show = h('button', { class: 'btn small', type: 'button' }, `Steps (${(turn.steps || []).length})`);
    show.addEventListener('click', () => { selectTurn(turn); setBench(true); });
    let sources = null;
    if ((turn.sources || []).length) {
      sources = h('button', { class: 'btn small', type: 'button' }, `Sources (${turn.sources.length})`);
      sources.addEventListener('click', () => {
        if (S.sourceTurn === turn && !$('#sources').hidden) setSources(false);
        else showSource(turn, null);
      });
    }
    let gaps = null;
    if (turn.mode === 'ask') {
      const r = turn.result || {};
      const weak = r.abstained || !(r.claims || r.citations || []).length;
      gaps = h('button', { class: `btn small${weak ? ' primary' : ''}`, type: 'button' }, 'What would it take to answer this?');
      gaps.addEventListener('click', () => askGaps(turn));
    }
    return h('div', { class: 'turn-actions' }, show, sources, gaps);
  }

  function renderFailed(turn, message, canRetry) {
    const retry = canRetry ? h('button', { class: 'btn', type: 'button' }, 'Try again') : null;
    if (retry) retry.addEventListener('click', () => { if (!S.busy) runTurn(turn); });
    clear(turn.body, h('div', { class: 'failed' }, h('p', { text: message }), retry), (turn.steps || []).length ? turnActions(turn) : null);
    turn.body.classList.remove('pending');
  }

  // ---- asking -------------------------------------------------------------------------
  function recentTurns() { // not history(): that would hide window.history inside this scope
    return S.turns.filter((t) => t.done && t.mode === 'ask').slice(-HISTORY_TURNS).map((t) => ({ q: t.question, a: t.answer }));
  }
  const mode = () => (document.querySelector('input[name=mode]:checked') || {}).value || 'ask';
  function setMode(m) {
    const r = document.querySelector(`input[name=mode][value=${m}]`);
    if (r) r.checked = true;
    showMode();
  }
  function showMode() {
    const gaps = mode() === 'gaps';
    $('#question').placeholder = gaps ? 'A question the graph cannot answer yet' : 'Ask a question about the documents';
    $('#hint').textContent = gaps
      ? 'The analyst explores the graph and reports what this question needs: ontology extensions, data to add, and facts extraction missed. It changes nothing.'
      : 'Answers come only from this collection, and every statement links to its source.';
  }
  function newTurn(question, turnMode, about) {
    const key = ++S.seq;
    const body = h('div', { class: 'a' });
    const label = turnMode === 'gaps' ? 'What would it take to answer' : 'You asked';
    const el = h('article', { class: `turn ${turnMode}`, 'aria-label': `Question ${key}` },
      h('div', { class: 'q' }, h('p', { class: turnMode === 'gaps' ? 'q-label' : 'sr-only', text: label }), h('p', { text: question })), body);
    $('#log').append(el);
    $('#intro').hidden = true;
    const turn = { key, question, mode: turnMode, about, el, body, done: false, answer: '', steps: [], hits: null,
      result: null, status: 'pending', started: 0, history: turnMode === 'ask' ? recentTurns() : [] };
    S.turns.push(turn);
    selectTurn(turn);
    runTurn(turn);
    return turn;
  }
  function ask() {
    const ta = $('#question'), question = ta.value.trim();
    if (!question || S.busy || !S.id) return;
    ta.value = '';
    newTurn(question, mode(), null);
  }
  function askGaps(turn) {
    if (S.busy) return;
    const r = turn.result || {};
    newTurn(turn.question, 'gaps', { answer: turn.answer, gaps: (r.gaps || []).map(str),
      steps: (turn.steps || []).filter((s) => s.kind === 'tool').map((s) => str(s.title)) });
  }
  async function runTurn(turn) {
    const gen = S.gen;
    turn.started = Date.now(); turn.status = 'pending'; turn.steps = []; turn.done = false;
    setBusy(true);
    const progressText = h('span', { text: turn.mode === 'gaps' ? 'Exploring the graph.' : 'Reading the documents.' });
    clear(turn.body, h('div', { class: 'progress', role: 'status' }, h('span', { class: 'spinner', 'aria-hidden': 'true' }), progressText));
    turn.body.classList.add('pending');
    turn.el.scrollIntoView({ block: 'nearest' });
    const showProgress = () => {
      const last = turn.steps[turn.steps.length - 1];
      const took = Math.round((Date.now() - turn.started) / 1000);
      const waiting = last ? str(last.title) : (turn.mode === 'gaps' ? 'Exploring the graph' : 'Reading the documents');
      const cold = !last && turn.mode !== 'gaps' ? '. The first question after a break can take a minute.' : '';
      progressText.textContent = `${waiting} (${took} s)${cold}`;
      if (S.selected === turn) renderBench();
    };
    const tick = setInterval(showProgress, 1000);
    renderBench();
    try {
      let id;
      try {
        ({ id } = await api('/chat', { c: S.id }, { method: 'POST',
          body: { question: turn.question, history: turn.history, mode: turn.mode, about: turn.about || undefined } }));
      } catch (e) {
        if (e.status === 429) return renderFailed(turn, `${(e.body && e.body.error) || 'You have reached today\'s question limit.'} The limit resets tomorrow.`, false);
        if (e.status === 400) return renderFailed(turn, (e.body && e.body.error) || 'The question could not be accepted.', false);
        throw e;
      }
      let r = null, errors = 0;
      while (Date.now() - turn.started < POLL_LIMIT_MS) {
        await sleep(POLL_MS);
        if (gen !== S.gen) return;
        try { r = await api('/chat', { c: S.id, id }); errors = 0; } catch (e) { if (e.status === 401 || ++errors >= 3) throw e; continue; }
        if (r && Array.isArray(r.steps)) { turn.steps = r.steps; turn.status = r.status === 'running' ? 'running' : turn.status; showProgress(); }
        if (r && (r.status === 'done' || r.status === 'failed')) break;
        r = null;
      }
      if (gen !== S.gen) return;
      if (!r) { turn.status = 'failed'; return renderFailed(turn, 'No answer after ten minutes. The agent may still be working; try again in a moment.', true); }
      turn.result = r; turn.steps = r.steps || turn.steps; turn.hits = r.ontology_hits || null;
      if (r.status === 'failed') { turn.status = 'failed'; return renderFailed(turn, r.error || 'The answer failed.', true); }
      turn.status = 'done'; turn.done = true;
      if (turn.mode === 'gaps') {
        renderReport(turn, r);
        announce(`Report ready: ${VERDICT[(r.report || {}).verdict] || 'see the report'}.`);
      } else {
        turn.answer = str(r.answer);
        window.KS.addSessionUsage(S.id, turn.hits);
        renderDone(turn, r);
        announce(r.blocked ? 'The question was declined.' : `Answer ready. ${turn.answer}`);
      }
    } catch (e) {
      if (gen === S.gen) { turn.status = 'failed'; renderFailed(turn, e.message || 'Something went wrong.', true); }
    } finally {
      clearInterval(tick);
      if (gen === S.gen) {
        setBusy(false);
        if (!turn.done) announce('The question did not get an answer.');
        if (S.selected === turn) renderBench();
      }
    }
  }

  // ---- the workbench ---------------------------------------------------------------------
  const KIND_LABEL = { classes: 'Classes', relations: 'Relations', attributes: 'Attributes' };
  const LEVEL_LABEL = { queried: 'asked for', read: 'read', cited: 'cited' };
  function termChip(kind, name, levels) {
    const strongest = levels.includes('cited') ? 'cited' : levels.includes('queried') ? 'queried' : 'read';
    return h('a', { class: `term ${strongest}`, href: ontologyLink(kind, name), title: `${name}: ${levels.map((l) => LEVEL_LABEL[l]).join(', ')}` },
      h('span', { text: name }), h('span', { class: 'term-level', text: levels.map((l) => LEVEL_LABEL[l]).join(' · ') }));
  }
  function querySource(s) {
    if (s.source === 'graph' || s.source === 'vector' || s.source === 'keyword' || s.source === 'structured') return s.source;
    const tool = str(s.tool);
    if (tool === 'search_passages') return 'keyword';
    if (GRAPH_TOOLS.has(tool)) return 'graph';
    if (STRUCTURED_TOOLS.has(tool)) return 'structured';
    return '';
  }
  function stepType(s) {
    if (STEP_LABEL[s.kind] && s.kind !== 'tool') return s.kind;
    const source = querySource(s);
    if (source) return source;
    const tool = str(s.tool);
    if (tool === 'read_passages') return 'read';
    if (tool === 'describe_ontology') return 'ontology';
    return 'other';
  }
  function tokenLine(usage) {
    return TOKEN_KINDS.map(([key, label]) => `${Number(usage[key] || 0).toLocaleString()} ${label}`).join(' · ');
  }
  function modelUsage(s) {
    const think = s.took_ms != null ? `${secs(s.took_ms)} thinking` : '';
    const tokens = s.usage ? tokenLine(s.usage) : 'No token report for this call';
    const price = s.usd != null ? usdText(s.usd) : '';
    return [think, tokens, price].filter(Boolean).join(' · ');
  }
  function stepItem(s) {
    const terms = Object.entries(s.terms || {}).flatMap(([k, names]) => (names || []).map((n) => h('span', { class: 'term-mini', title: KIND_LABEL[k] || k, text: n })));
    const type = stepType(s);
    const source = querySource(s);
    const input = s.input && Object.keys(s.input).length
      ? h('details', { class: `step-input${source ? ' ' + source : ''}` },
        h('summary', { text: SOURCE_LABEL[source] || 'Input' }),
        h('pre', { text: JSON.stringify(s.input, null, 1) })) : null;
    const when = s.kind === 'tool' && s.took_ms != null ? `${secs(s.took_ms)} in the tool · ` : '';
    return h('li', { class: `step ${str(s.kind)} t-${type}${s.error ? ' error' : ''}` },
      h('span', { class: 'step-dot', 'aria-hidden': 'true' }),
      h('div', { class: 'step-body' },
        h('p', { class: 'step-title' },
          h('span', { class: 'step-name' },
            h('span', { class: 'step-kind', text: STEP_LABEL[type] || 'Step' }),
            h('span', { text: str(s.title) })),
          h('span', { class: 'step-time', title: 'Time from the start of the question', text: when + secs(s.ms) })),
        s.kind === 'model' ? h('p', { class: 'step-usage', text: modelUsage(s) }) : null,
        s.detail ? h('p', { class: 'step-detail', text: str(s.detail) }) : null,
        s.error ? h('p', { class: 'step-detail error', text: str(s.error) }) : null,
        terms.length ? h('p', { class: 'step-terms' }, terms) : null,
        input));
  }
  // The price is the model call. The label names the tool that followed it, so a free word
  // search is not mistaken for the thing that cost the money. The step list keeps the tool name.
  const COST_PATHS = [
    ['graph', 'Thinking, then the knowledge graph'],
    ['vector', 'Thinking, then a vector search'],
    ['keyword', 'Thinking, then a word search'],
    ['structured', 'Thinking, then a structured lookup'],
    ['read', 'Thinking, then a passage read'],
    ['ontology', 'Thinking, then the ontology'],
    ['other', 'Thinking, then another tool'],
    ['answer', 'Thinking, then the answer'],
  ];
  const PATH_IDS = new Set(COST_PATHS.map(([id]) => id).filter((id) => id !== 'answer'));
  function costByPath(steps, done) {
    const usd = Object.fromEntries(COST_PATHS.map(([id]) => [id, 0]));
    const priced = Object.fromEntries(COST_PATHS.map(([id]) => [id, false]));
    const unpriced = Object.fromEntries(COST_PATHS.map(([id]) => [id, false]));
    let pending = null;
    let paths = [];
    function assign() {
      if (!pending) { paths = []; return; }
      const targets = [...new Set(paths)].filter((id) => PATH_IDS.has(id));
      if (!targets.length) targets.push('answer');
      if (pending.usd == null) {
        for (const id of targets) unpriced[id] = true;
      } else {
        const share = pending.usd / targets.length;
        for (const id of targets) { usd[id] += share; priced[id] = true; }
      }
      pending = null;
      paths = [];
    }
    for (const s of steps) {
      if (s.kind === 'model') {
        assign();
        pending = { usd: s.usd == null ? null : Number(s.usd) };
      } else {
        const type = stepType(s);
        if (PATH_IDS.has(type)) paths.push(type);
      }
    }
    if (done) assign();
    return { usd, priced, unpriced };
  }
  function answerText(t) {
    const running = t.status === 'pending' || t.status === 'running';
    if (running) return '';
    if (t.mode === 'gaps' && t.result && t.result.report) {
      const report = t.result.report;
      const verdict = VERDICT[report.verdict] || str(report.verdict) || 'Report';
      return report.summary ? `${verdict}. ${str(report.summary)}` : verdict;
    }
    if (t.answer) return t.answer;
    if (t.status === 'failed') return (t.result && t.result.error) || 'The question did not get an answer.';
    return '';
  }
  function stepSummary(t) {
    const steps = t.steps;
    const counts = Object.fromEntries(STEP_TYPES.map(([id]) => [id, 0]));
    const tools = {};
    const tokens = Object.fromEntries(TOKEN_KINDS.map(([key]) => [key, 0]));
    let reported = 0;
    for (const s of steps) {
      counts[stepType(s)] += 1;
      if (s.tool) tools[str(s.tool)] = (tools[str(s.tool)] || 0) + 1;
      if (s.kind === 'model' && s.usage) {
        reported += 1;
        for (const key of Object.keys(tokens)) tokens[key] += Number(s.usage[key] || 0);
      }
    }
    const toolRows = Object.entries(tools).sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]));
    const done = t.status !== 'pending' && t.status !== 'running';
    const costs = costByPath(steps, done);
    const countRow = (id, label) => h('tr', { class: `t-${id}` },
      h('th', { scope: 'row' }, h('span', { class: 'step-swatch', 'aria-hidden': 'true' }), h('span', { text: label })),
      h('td', { class: 'num-cell', text: String(counts[id]) }));
    const priceCell = (id) => {
      if (costs.priced[id] && costs.unpriced[id]) return `${usdText(costs.usd[id])} · some calls not priced`;
      if (costs.priced[id]) return usdText(costs.usd[id]);
      if (costs.unpriced[id]) return 'not priced';
      return usdText(0);
    };
    const answer = answerText(t);
    return h('div', { class: 'step-summary' },
      h('h4', { text: 'Steps by type' }),
      h('table', { class: 'kv small' },
        h('thead', null, h('tr', null, [h('th', { scope: 'col', text: 'Type' }), h('th', { scope: 'col', text: 'Steps' })])),
        h('tbody', null, STEP_TYPES.map(([id, label]) => countRow(id, label)))),
      h('h4', { text: 'Tools called' }),
      toolRows.length
        ? h('table', { class: 'kv small' },
          h('thead', null, h('tr', null, [h('th', { scope: 'col', text: 'Tool' }), h('th', { scope: 'col', text: 'Calls' })])),
          h('tbody', null, toolRows.map(([name, n]) => h('tr', null,
            h('th', { scope: 'row', text: name }), h('td', { class: 'num-cell', text: String(n) })))))
        : h('p', { class: 'small muted', text: 'No tools were called.' }),
      h('h4', { text: 'Model tokens' }),
      h('p', { class: 'small', text: reported
        ? tokenLine(tokens)
        : 'No model call reported tokens.' }),
      h('h4', { text: 'What the model rounds paid for' }),
      h('p', { class: 'small muted', text: 'The price is the model call. The name is the tool that followed it. A call that used several tools is split evenly across them. The tools themselves are not charged.'
        + (done ? '' : ' The model call still in progress is not in this table yet.') }),
      h('table', { class: 'kv small' },
        h('thead', null, h('tr', null, [h('th', { scope: 'col', text: 'Model round' }), h('th', { scope: 'col', text: 'Price' })])),
        h('tbody', null, COST_PATHS.map(([id, label]) => h('tr', { class: `t-${id === 'answer' ? 'done' : id}` },
          h('th', { scope: 'row' }, h('span', { class: 'step-swatch', 'aria-hidden': 'true' }), h('span', { text: label })),
          h('td', { class: 'num-cell', text: priceCell(id) }))))),
      h('h4', { text: 'Answer' }),
      h('p', { class: answer ? 'bench-answer' : 'small muted', text: answer || (done ? 'No answer was recorded.' : 'The answer appears when the question finishes.') }));
  }
  // List price. Under a cent, four places, so a split of small calls does not all read as the same amount.
  function usdText(n) {
    const x = Number(n);
    if (!Number.isFinite(x)) return '';
    if (x === 0) return '$0.00';
    return '$' + (Math.abs(x) < 0.01 ? x.toFixed(4) : x.toFixed(2));
  }
  // Sections start collapsed. A section the person opens stays open while the steps update.
  const BENCH_OPEN = new Set();
  function fold(titleId, title, ...body) {
    const attrs = { class: 'bench-fold' };
    if (BENCH_OPEN.has(titleId)) attrs.open = true;
    const details = h('details', attrs,
      h('summary', null, h('h3', { id: titleId, text: title })),
      h('div', { class: 'bench-fold-body' }, body));
    details.addEventListener('toggle', () => {
      if (details.open) BENCH_OPEN.add(titleId);
      else BENCH_OPEN.delete(titleId);
    });
    return details;
  }
  function renderCost(t) {
    const box = $('#bench-cost');
    const running = t && (t.status === 'pending' || t.status === 'running');
    const cost = t && t.result && t.result.cost;
    box.hidden = false;
    if (!cost) {
      clear(box, fold('bench-cost-title', 'Cost',
        h('p', { class: 'small muted', text: !t || running
          ? 'The price appears when the question finishes.'
          : 'This answer did not report token use, so it has no price.' })));
      return;
    }
    const rows = cost.parts || [];
    const calls = (cost.calls || []).filter((c) => c && c.usd != null);
    const total = cost.priced && cost.usd != null
      ? h('p', { class: 'cost-total' }, 'This question ', h('b', { text: usdText(cost.usd) }))
      : h('p', { class: 'cost-total', text: 'This model has no list price here.' });
    clear(box, fold('bench-cost-title', 'Cost',
      total,
      cost.note ? h('p', { class: 'small muted', text: str(cost.note) }) : null,
      cost.omitted ? h('p', { class: 'small muted', text: str(cost.omitted) }) : null,
      rows.length ? h('table', { class: 'kv small' },
        h('thead', null, h('tr', null, ['Where', 'Tokens', 'Price'].map((x) => h('th', { scope: 'col', text: x })))),
        h('tbody', null, rows.map((p) => h('tr', null,
          h('td', { text: str(p.label) }),
          h('td', { class: 'num-cell', text: Number(p.tokens || 0).toLocaleString() }),
          h('td', { class: 'num-cell', text: p.usd == null ? 'not priced' : usdText(p.usd) }))))) : null,
      calls.length ? [h('h4', { text: 'By model call' }),
        h('ul', { class: 'cost-calls' }, calls.map((c) => h('li', null,
          h('span', { text: str(c.title) }), h('span', { class: 'num-cell', text: usdText(c.usd) }))))] : null));
  }
  function renderBench() {
    const t = S.selected;
    const stepsBox = $('#bench-steps'), termsBox = $('#bench-terms');
    if (!t) {
      clear(stepsBox, fold('bench-steps-title', 'Steps',
        h('p', { class: 'small muted', text: 'Ask a question to see what the agent does: each search, each read and each check, as it happens.' })));
      termsBox.hidden = false;
      clear(termsBox, fold('bench-terms-title', 'Ontology used',
        h('p', { class: 'small muted', text: 'The terms a question uses appear here.' })));
      renderCost(null);
      return renderSession();
    }
    const running = t.status === 'pending' || t.status === 'running';
    const took = Math.round(((running ? Date.now() : t.started + ((t.steps[t.steps.length - 1] || {}).ms || 0)) - t.started) / 1000);
    const tools = t.steps.filter((s) => s.kind === 'tool').length, models = t.steps.filter((s) => s.kind === 'model').length;
    const statusLine = running
      ? h('p', { class: 'bench-status' }, h('span', { class: 'spinner', 'aria-hidden': 'true' }), ` Working for ${took} s: ${plural(tools, 'tool call')} so far`)
      : h('p', { class: 'bench-status' }, t.status === 'failed' ? 'Stopped' : 'Done',
        `: ${plural(tools, 'tool call')}, ${plural(models, 'model call')}${t.result && t.result.ms ? `, ${secs(t.result.ms)}` : ''}`);
    clear(stepsBox, fold('bench-steps-title', t.mode === 'gaps' ? 'Steps: what would it take' : 'Steps',
      h('p', { class: 'bench-q', text: t.question }),
      statusLine,
      t.steps.length ? h('ol', { class: 'steps' }, t.steps.map(stepItem))
        : h('p', { class: 'small muted', text: running ? 'Waiting for the first step.' : 'This answer reported no steps.' }),
      t.steps.length ? stepSummary(t) : null));
    renderCost(t);
    const hits = t.hits || {};
    const groups = Object.keys(KIND_LABEL).filter((k) => Object.keys(hits[k] || {}).length);
    termsBox.hidden = false;
    clear(termsBox, fold('bench-terms-title', t.mode === 'gaps' ? 'Ontology the analyst looked at' : 'Ontology used',
      groups.length
        ? [h('p', { class: 'small muted', text: 'Asked for: the agent searched by it. Read: it came back in what the agent read. Cited: a fact of it is in a passage the answer cites. Select one to see it in the ontology.' }),
          groups.map((k) => [h('h4', { text: KIND_LABEL[k] }),
            h('p', { class: 'terms' }, Object.entries(hits[k]).map(([name, levels]) => termChip(k, name, levels)))])]
        : h('p', { class: 'small muted', text: 'The terms a question uses appear here.' })));
    renderSession();
  }
  function renderSession() {
    const u = window.KS.sessionUsage(S.id), box = $('#bench-session');
    box.hidden = false;
    if (!u.questions) {
      clear(box, fold('bench-session-title', 'This session',
        h('p', { class: 'small muted', text: 'No questions in this session yet.' })));
      return;
    }
    const rows = Object.keys(KIND_LABEL).flatMap((k) => Object.entries(u[k] || {}).map(([name, c]) => ({ k, name, c, n: Math.max(c.queried, c.read, c.cited) })))
      .sort((a, b) => b.c.cited - a.c.cited || b.n - a.n || a.name.localeCompare(b.name)).slice(0, 10);
    const q = new URLSearchParams({ overlay: 'session' });
    if (S.collections.length > 1) q.set('c', S.id);
    clear(box, fold('bench-session-title', 'This session',
      h('p', { class: 'small muted', text: `${plural(u.questions, 'question')} answered. The terms they used most:` }),
      h('table', { class: 'kv small' }, h('thead', null, h('tr', null, ['Term', 'Read', 'Cited'].map((x) => h('th', { scope: 'col', text: x })))),
        h('tbody', null, rows.map((r) => h('tr', null, h('td', null, h('a', { href: ontologyLink(r.k, r.name), text: r.name })),
          h('td', { class: 'num-cell', text: String(r.c.read) }), h('td', { class: 'num-cell', text: String(r.c.cited) }))))),
      h('p', null, h('a', { href: `ontology.html?${q}` }, 'Show this session on the ontology'))));
  }
  function selectTurn(turn) {
    for (const t of S.turns) t.el.classList.toggle('selected', t === turn);
    S.selected = turn;
    renderBench();
  }
  const wide = () => matchMedia('(min-width: 1280px)').matches;
  function setDemo(on, remember) {
    $('#workspace').classList.toggle('demo-off', !on);
    $('#samples').hidden = !on;
    const btn = $('#demo');
    btn.setAttribute('aria-pressed', String(on));
    btn.textContent = on ? 'User view' : 'Demonstrate';
    btn.title = on ? 'Hide the sample questions and the workbench' : 'Show the sample questions and the workbench';
    $('#bench-open').hidden = !on;
    if (on) setBench(wide(), false);
    else setBench(false, false);
    if (remember) lstore.set(DEMO_KEY, on ? 'on' : 'off');
  }
  function setBench(open, remember) {
    $('#bench').hidden = !open;
    $('#workspace').classList.toggle('bench-off', !open);
    $('#bench-open').setAttribute('aria-expanded', String(open));
    if (remember && wide()) lstore.set(BENCH_KEY, open ? 'open' : 'closed');
  }

  // ---- collections ---------------------------------------------------------------------
  function current() { return S.collections.find((c) => c.id === S.id) || {}; }
  function showCollection() {
    const c = current();
    const multi = S.collections.length > 1;
    $('#coll-wrap').hidden = !multi;
    $('#coll-name').hidden = multi;
    $('#coll-name').textContent = str(c.name || c.id);
    $('#coll-select').value = S.id;
    const intro = $('#intro');
    intro.textContent = c.description ? str(c.description) : 'Ask a question about the documents in this collection.';
    intro.hidden = S.turns.length > 0;
    document.title = `${str(c.name || c.id)} · ${window.KS.brandName()}`;
    renderSamples();
  }
  // Same idea as the earnings lab's suggested questions: a click fills the box and does not spend
  // a question. Levels come from the collection profile. Without any, three general questions stand in.
  const SAMPLE_LEVELS = [
    { id: 'low', label: 'Low', hint: 'One lookup' },
    { id: 'medium', label: 'Medium', hint: 'A few facts, connected' },
    { id: 'high', label: 'High', hint: 'A comparison, or a why' },
  ];
  const SAMPLE_FALLBACK = [
    { level: 'low', text: 'What are the main subjects in this collection?' },
    { level: 'medium', text: 'Which subjects appear in more than one document, and what connects them?' },
    { level: 'high', text: 'Compare the two subjects the documents connect most closely, and say how the passages support that.' },
  ];
  function sampleItems(c) {
    const raw = Array.isArray(c.example_questions) ? c.example_questions : [];
    const items = raw.map((x) => (typeof x === 'string'
      ? { text: x, level: 'medium' }
      : { text: str(x && x.text), level: str(x && x.level) || 'medium',
          link: str(x && x.link), link_label: str(x && x.link_label) }))
      .filter((x) => x.text);
    return items.length ? items : SAMPLE_FALLBACK;
  }
  function safeSampleLink(link) {
    const s = str(link);
    if (!/^https:\/\/[a-z0-9.-]+(?:\/[^\s]*)?$/i.test(s) || /[<>"']/.test(s)) return '';
    return s;
  }
  function useSample(text) {
    setMode('ask');
    const ta = $('#question');
    ta.value = text.slice(0, 2000);
    ta.focus();
  }
  function renderSamples() {
    const c = current();
    const fromProfile = Array.isArray(c.example_questions) && c.example_questions.length > 0;
    const items = sampleItems(c);
    $('#samples').hidden = $('#workspace').classList.contains('demo-off');
    $('#samples-note').textContent = fromProfile
      ? 'From this collection. Choosing one fills the question box. It is not sent until you press Send.'
      : 'Examples for any collection. Choosing one fills the question box. It is not sent until you press Send.';
    clear($('#samples-list'), SAMPLE_LEVELS.map((lv) => {
      const qs = items.filter((x) => x.level === lv.id);
      if (!qs.length) return null;
      return h('section', { class: 'sample-group' },
        h('h3', { text: lv.label }),
        h('p', { class: 'sample-hint', text: lv.hint }),
        qs.map((q) => {
          const b = h('button', { class: `sample ${lv.id}`, type: 'button' }, q.text);
          b.addEventListener('click', () => useSample(q.text));
          const href = safeSampleLink(q.link);
          const link = href
            ? h('a', { class: 'sample-link', href, target: '_blank', rel: 'noopener noreferrer' }, q.link_label || 'Open')
            : null;
          return link ? h('div', null, b, link) : b;
        }));
    }));
  }
  function switchCollection(id) {
    if (S.busy || id === S.id) return;
    S.id = id; S.gen++; S.turns = []; S.selected = null;
    lstore.set(COLL_KEY, id);
    clear($('#log'));
    showCollection();
    renderBench();
    $('#question').focus();
  }

  // ---- boot ------------------------------------------------------------------------------
  function wire() {
    $('#ask').addEventListener('submit', (e) => { e.preventDefault(); ask(); });
    $('#question').addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && !e.shiftKey && !e.isComposing) { e.preventDefault(); ask(); }
    });
    $('#coll-select').addEventListener('change', (e) => switchCollection(e.target.value));
    for (const r of document.querySelectorAll('input[name=mode]')) r.addEventListener('change', showMode);
    $('#sources-open').addEventListener('click', () => {
      if (!$('#sources').hidden) { S.lastCite = null; setSources(false); return; }
      const turn = S.sourceTurn || [...S.turns].reverse().find((t) => (t.sources || []).length);
      if (turn) showSource(turn, S.sourceTurn === turn ? S.sourceN : null);
    });
    $('#sources-close').addEventListener('click', () => setSources(false));
    $('#demo').addEventListener('click', () => {
      const on = $('#demo').getAttribute('aria-pressed') !== 'true';
      setDemo(on, true);
      if (on && wide()) $('#bench-close').focus();
      else if (!on) $('#question').focus();
    });
    $('#bench-close').addEventListener('click', () => { setBench(false, true); $('#bench-open').focus(); });
    $('#bench-open').addEventListener('click', () => {
      const open = $('#bench').hidden;
      setBench(open, true);
      if (open) $('#bench-close').focus();
    });
    document.addEventListener('keydown', (e) => {
      if (e.key !== 'Escape') return;
      if (!$('#sources').hidden) { setSources(false); return; }
      if (!wide() && !$('#bench').hidden) setBench(false);
    });
  }
  function signedOut(started) {
    $('#signin').hidden = started.cfg.mode === 'site';
    notice(window.KS.signedOutNotice(started, 'Sign in to ask questions'));
  }
  async function boot() {
    const started = await window.KS.start();
    const { cfg, error, signedIn, claims } = started;
    const brand = window.KS.brandName();
    $('#brand-name').textContent = brand; document.title = brand;
    wire();
    if (cfg.mode === 'hosted') {
      if (!cfg.oidc || !cfg.oidc.clientId) return notice(h('p', { class: 'error', text: error }));
      $('#signin').addEventListener('click', () => auth.login());
      $('#signout').addEventListener('click', () => auth.logout());
      if (!signedIn) return signedOut(started);
      $('#user').textContent = str(claims.email || claims.preferred_username || claims['cognito:username'] || '');
      $('#signout').hidden = false;
    }
    if (cfg.mode === 'site') { // signed in on the website, which frames this page
      if (error) return notice(h('p', { class: 'error', text: error }));
      if (!signedIn) return signedOut(started);
      $('#user').textContent = str(claims.name || claims.email || '');
    }
    notice(h('p', { class: 'muted', text: 'Loading.' }));
    try {
      const r = await api('/collections');
      S.collections = (r && r.collections) || [];
      S.private = !!(r && r.private);
    } catch (e) {
      if (e.status === 401 && cfg.mode !== 'site') return; // hosted: already signing in again
      return notice(h('h2', { text: e.status === 401 ? 'Your sign-in was not accepted' : 'The service could not be reached' }), h('p', { text: e.message }),
        h('button', { class: 'btn', type: 'button', onclick: () => location.reload() }, 'Try again'));
    }
    if (!S.collections.length) return notice(h('h2', { text: 'No collections yet' }), h('p', { text: 'There are no collections to ask about.' }));
    $('#private-pill').hidden = !S.private;
    clear($('#coll-select'), S.collections.map((c) => h('option', { value: c.id }, str(c.name || c.id))));
    const remembered = lstore.get(COLL_KEY);
    S.id = S.collections.some((c) => c.id === remembered) ? remembered : S.collections[0].id;
    lstore.set(COLL_KEY, S.id);
    notice();
    showCollection();
    $('#ask').hidden = false;
    $('#demo').hidden = false;
    setDemo(lstore.get(DEMO_KEY) === 'on', false);
    renderBench();
    showMode();
    // ?ask= fills the box (the ontology page links here with a question), and never sends it
    const asked = new URLSearchParams(location.search).get('ask');
    if (asked) { $('#question').value = asked.slice(0, 2000); window.history.replaceState(null, '', location.pathname); }
    $('#question').focus();
  }
  boot();
}

// common.js normally runs first (both are deferred). If it did not, because the browser kept a
// broken copy from a deploy or something blocked the request, fetch a fresh copy once; if that
// fails too, say so on the page rather than leaving it blank.
(function withCommon(run) {
  if (window.KS) return run();
  const failed = () => {
    const n = document.getElementById('notice');
    if (!n) return;
    n.hidden = false;
    n.textContent = 'This page could not load its script (common.js). Reload it; if that does not help, '
      + 'a browser extension may be blocking it.';
  };
  const s = document.createElement('script');
  s.src = `common.js?fresh=${Date.now()}`;
  s.onload = () => (window.KS ? run() : failed());
  s.onerror = failed;
  document.head.append(s);
})(main);
