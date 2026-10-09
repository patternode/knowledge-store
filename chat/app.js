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
 * A step's input says whether that call was a knowledge graph query, a vector query, or a
 * keyword passage search.
 * A question has a mode: "ask" answers it; "gaps" asks the analyst what it
 * would take to answer it (ontology extensions, data, missed extraction), which a curator can keep
 * as an ontology request.
 */
function main() {
  'use strict';
  const { $, h, clear, lstore, safeUrl, sleep, str, auth, api, COLL_KEY } = window.KS;
  // ---- state ------------------------------------------------------------------------------
  const S = { collections: [], id: null, private: false, gen: 0, busy: false, turns: [], seq: 0, selected: null };
  const HISTORY_TURNS = 6, POLL_MS = 1500, POLL_LIMIT_MS = 10 * 60 * 1000;
  const BENCH_KEY = 'ks.chat.bench';
  const DEMO_KEY = 'ks.chat.demo';
  const GRAPH_TOOLS = new Set(['search_entities', 'list_entities', 'get_entity', 'neighbourhood', 'find_paths']);
  const SOURCE_LABEL = {
    graph: 'Knowledge graph query',
    vector: 'Vector query',
    keyword: 'Keyword passage search',
  };
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
  // Matching ignores case and treats any run of whitespace as one space. norm() keeps, for each
  // character of the normalised text, its index in the original, so a match maps back exactly.
  function norm(s) {
    let out = '';
    const map = [];
    let space = false;
    for (let i = 0; i < s.length; i++) {
      const ch = s[i];
      if (/\s/.test(ch)) { if (!space && out.length) { out += ' '; map.push(i); } space = true; continue; }
      space = false;
      out += ch.toLowerCase(); map.push(i);
    }
    if (out.endsWith(' ')) { out = out.slice(0, -1); map.pop(); }
    return { text: out, map };
  }
  function highlight(text, quotes) {
    const src = str(text), n = norm(src), ranges = [], missing = [];
    for (const q of quotes) {
      const nq = norm(str(q)).text;
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
  function flashCard(turn, n) {
    const card = document.getElementById(cardId(turn, n));
    if (!card) return;
    card.scrollIntoView({ behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth', block: 'center' });
    card.classList.remove('flash'); void card.offsetWidth; card.classList.add('flash');
    card.focus({ preventScroll: true });
    setTimeout(() => card.classList.remove('flash'), 2000);
  }
  function citeLinks(turn, nums, known) {
    return nums.map((n) => (known.has(n)
      ? h('a', { class: 'cite', href: `#${cardId(turn, n)}`, 'aria-label': `Source ${n}`,
        onclick: (e) => { e.preventDefault(); flashCard(turn, n); } }, `[${n}]`)
      : h('span', { class: 'cite dead', title: 'This source is not listed' }, `[${n}]`)));
  }
  // The agent returns numbered sources. The portal tool loop returns citations and writes
  // [p:<id>] in the answer. Both are shown the same way: the answer, then a card per source.
  function groundedSources(r) {
    const listed = (Array.isArray(r.sources) ? r.sources : []).slice().sort((a, b) => (a.n || 0) - (b.n || 0));
    if (listed.length) return listed;
    const cites = (Array.isArray(r.citations) ? r.citations : []).filter((c) => c && typeof c === 'object');
    if (!cites.length) return [];
    const byId = new Map(cites.map((c) => [c.id || c.passage_id, c]));
    const order = [], seen = new Set();
    const re = /\[p:([^\]\s]+)\]/g;
    let m;
    while ((m = re.exec(str(r.answer)))) if (!seen.has(m[1])) { seen.add(m[1]); order.push(m[1]); }
    for (const id of byId.keys()) if (id && !seen.has(id)) { seen.add(id); order.push(id); }
    return order.map((id, i) => {
      const c = byId.get(id) || {};
      return { n: i + 1, passage_id: id, doc: c.doc, title: c.title, name: c.name,
        text: c.text || '', quotes: Array.isArray(c.quotes) ? c.quotes : [] };
    });
  }
  function inlineParts(text, cite) {
    const out = [], re = /\[p:([^\]\s]+)\]|\*\*([^*]+)\*\*|`([^`]+)`/g;
    let last = 0, m;
    while ((m = re.exec(text))) {
      if (m.index > last) out.push(text.slice(last, m.index));
      if (m[1]) out.push(cite(m[1]));
      else if (m[2]) out.push(h('strong', { text: m[2] }));
      else out.push(h('code', { text: m[3] }));
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
  function sourceCard(turn, s, claims) {
    const quotes = [...(s.quotes || [])];
    for (const c of claims) for (const cit of c.citations || []) if (cit && cit.passage_id === s.passage_id && cit.quote) quotes.push(cit.quote);
    const unique = [...new Set(quotes.map(str).filter((q) => q.trim()))];
    const { nodes, missing } = highlight(s.text, unique);
    const title = str(s.title || s.name || s.doc) || 'Untitled document';
    const status = h('p', { class: 'card-status', role: 'status' });
    const open = h('button', { class: 'btn', type: 'button', 'aria-label': `Open document: ${title}` }, 'Open document');
    open.addEventListener('click', () => openDocument(s.doc, open, status));
    return h('li', { class: 'card', id: cardId(turn, s.n), tabindex: '-1', 'aria-label': `Source ${s.n}: ${title}` },
      h('div', { class: 'card-head' }, h('span', { class: 'num', 'aria-hidden': 'true', text: str(s.n) }), h('h4', { text: title })),
      nodes.length ? h('blockquote', { class: 'passage' }, nodes) : null,
      missing.length ? h('div', { class: 'missing' }, h('p', { text: 'Quoted from this source, not shown in the passage above:' }),
        h('ul', null, missing.map((q) => h('li', { text: q })))) : null,
      s.doc ? h('div', { class: 'card-actions' }, open, status) : null);
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
    if (sources.length) {
      out.push(h('h3', { class: 'sources-title', text: sources.length === 1 ? 'Source' : 'Sources' }),
        h('ol', { class: 'cards' }, sources.map((s) => sourceCard(turn, s, claims))));
    }
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
    let gaps = null;
    if (turn.mode === 'ask') {
      const r = turn.result || {};
      const weak = r.abstained || !(r.claims || r.citations || []).length;
      gaps = h('button', { class: `btn small${weak ? ' primary' : ''}`, type: 'button' }, 'What would it take to answer this?');
      gaps.addEventListener('click', () => askGaps(turn));
    }
    return h('div', { class: 'turn-actions' }, show, gaps);
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
      : 'Answers come only from the documents in this collection, and every statement links to its source.';
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
    if (s.source === 'graph' || s.source === 'vector' || s.source === 'keyword') return s.source;
    const tool = str(s.tool);
    if (tool === 'search_passages') return 'keyword';
    if (GRAPH_TOOLS.has(tool)) return 'graph';
    return '';
  }
  function stepItem(s) {
    const terms = Object.entries(s.terms || {}).flatMap(([k, names]) => (names || []).map((n) => h('span', { class: 'term-mini', title: KIND_LABEL[k] || k, text: n })));
    const source = querySource(s);
    const input = s.input && Object.keys(s.input).length
      ? h('details', { class: `step-input${source ? ' ' + source : ''}` },
        h('summary', { text: SOURCE_LABEL[source] || 'Input' }),
        h('pre', { text: JSON.stringify(s.input, null, 1) })) : null;
    const spend = s.kind === 'model' && s.usd != null ? `${usdText(s.usd)} · ` : '';
    return h('li', { class: `step ${str(s.kind)}${source ? ' q-' + source : ''}${s.error ? ' error' : ''}` },
      h('span', { class: 'step-dot', 'aria-hidden': 'true' }),
      h('div', { class: 'step-body' },
        h('p', { class: 'step-title' }, h('span', { text: str(s.title) }),
          h('span', { class: 'step-time', title: s.usd != null ? 'List price of this model call' : '', text: spend + secs(s.ms) })),
        s.detail ? h('p', { class: 'step-detail', text: str(s.detail) }) : null,
        s.error ? h('p', { class: 'step-detail error', text: str(s.error) }) : null,
        terms.length ? h('p', { class: 'step-terms' }, terms) : null,
        input));
  }
  // List price. Under a cent, four places, so a split of small calls does not all read as the same amount.
  function usdText(n) {
    const x = Number(n);
    if (!Number.isFinite(x)) return '';
    if (x === 0) return '$0.00';
    return '$' + (Math.abs(x) < 0.01 ? x.toFixed(4) : x.toFixed(2));
  }
  function renderCost(t) {
    const box = $('#bench-cost');
    const running = t && (t.status === 'pending' || t.status === 'running');
    const cost = t && t.result && t.result.cost;
    if (!t) { box.hidden = true; return; }
    box.hidden = false;
    if (!cost) {
      clear(box, h('h3', { id: 'bench-cost-title', text: 'Cost' }),
        h('p', { class: 'small muted', text: running
          ? 'The price appears when the question finishes.'
          : 'This answer did not report token use, so it has no price.' }));
      return;
    }
    const rows = cost.parts || [];
    const calls = (cost.calls || []).filter((c) => c && c.usd != null);
    const total = cost.priced && cost.usd != null
      ? h('p', { class: 'cost-total' }, 'This question ', h('b', { text: usdText(cost.usd) }))
      : h('p', { class: 'cost-total', text: 'This model has no list price here.' });
    clear(box,
      h('h3', { id: 'bench-cost-title', text: 'Cost' }),
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
          h('span', { text: str(c.title) }), h('span', { class: 'num-cell', text: usdText(c.usd) }))))] : null);
  }
  function renderBench() {
    const t = S.selected;
    const stepsBox = $('#bench-steps'), termsBox = $('#bench-terms');
    if (!t) {
      clear(stepsBox, h('h3', { id: 'bench-steps-title', text: 'Steps' }),
        h('p', { class: 'small muted', text: 'Ask a question to see what the agent does: each search, each read and each check, as it happens.' }));
      termsBox.hidden = true;
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
    clear(stepsBox,
      h('h3', { id: 'bench-steps-title', text: t.mode === 'gaps' ? 'Steps: what would it take' : 'Steps' }),
      h('p', { class: 'bench-q', text: t.question }),
      statusLine,
      t.steps.length ? h('ol', { class: 'steps' }, t.steps.map(stepItem))
        : h('p', { class: 'small muted', text: running ? 'Waiting for the first step.' : 'This answer reported no steps.' }));
    renderCost(t);
    const hits = t.hits || {};
    const groups = Object.keys(KIND_LABEL).filter((k) => Object.keys(hits[k] || {}).length);
    termsBox.hidden = !groups.length;
    if (groups.length) {
      clear(termsBox, h('h3', { id: 'bench-terms-title', text: t.mode === 'gaps' ? 'Ontology the analyst looked at' : 'Ontology used' }),
        h('p', { class: 'small muted', text: 'Asked for: the agent searched by it. Read: it came back in what the agent read. Cited: a fact of it is in a passage the answer cites. Select one to see it in the ontology.' }),
        groups.map((k) => [h('h4', { text: KIND_LABEL[k] }),
          h('p', { class: 'terms' }, Object.entries(hits[k]).map(([name, levels]) => termChip(k, name, levels)))]));
    }
    renderSession();
  }
  function renderSession() {
    const u = window.KS.sessionUsage(S.id), box = $('#bench-session');
    box.hidden = !u.questions;
    if (!u.questions) return;
    const rows = Object.keys(KIND_LABEL).flatMap((k) => Object.entries(u[k] || {}).map(([name, c]) => ({ k, name, c, n: Math.max(c.queried, c.read, c.cited) })))
      .sort((a, b) => b.c.cited - a.c.cited || b.n - a.n || a.name.localeCompare(b.name)).slice(0, 10);
    const q = new URLSearchParams({ overlay: 'session' });
    if (S.collections.length > 1) q.set('c', S.id);
    clear(box, h('h3', { id: 'bench-session-title', text: 'This session' }),
      h('p', { class: 'small muted', text: `${plural(u.questions, 'question')} answered. The terms they used most:` }),
      h('table', { class: 'kv small' }, h('thead', null, h('tr', null, ['Term', 'Read', 'Cited'].map((x) => h('th', { scope: 'col', text: x })))),
        h('tbody', null, rows.map((r) => h('tr', null, h('td', null, h('a', { href: ontologyLink(r.k, r.name), text: r.name })),
          h('td', { class: 'num-cell', text: String(r.c.read) }), h('td', { class: 'num-cell', text: String(r.c.cited) }))))),
      h('p', null, h('a', { href: `ontology.html?${q}` }, 'Show this session on the ontology')));
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
    const items = raw.map((x) => (typeof x === 'string' ? { text: x, level: 'medium' } : { text: str(x && x.text), level: str(x && x.level) || 'medium' }))
      .filter((x) => x.text);
    return items.length ? items : SAMPLE_FALLBACK;
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
          return b;
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
    document.addEventListener('keydown', (e) => { if (e.key === 'Escape' && !wide() && !$('#bench').hidden) setBench(false); });
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
