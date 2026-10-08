/* Knowledge Store chat. Plain ES2020, no framework, no build step.
 *
 * Answers, sources and document titles come from uploaded documents and a model, so no server
 * text ever reaches innerHTML: every node is built with h(), which sets textContent and
 * attributes only. The answer is rendered from its structured claims, never parsed as markdown.
 *
 * Sign-in, the API client and the helpers are in common.js, which the ontology page shares.
 */
(() => {
  'use strict';
  const { $, h, clear, lstore, safeUrl, sleep, str, auth, api, COLL_KEY } = window.KS;
  // ---- state ------------------------------------------------------------------------------
  const S = { collections: [], id: null, private: false, gen: 0, busy: false, turns: [], seq: 0 };
  const HISTORY_TURNS = 6, POLL_MS = 2000, POLL_LIMIT_MS = 5 * 60 * 1000;

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
  function answerBody(turn, r) {
    const sources = Array.isArray(r.sources) ? r.sources : [];
    const known = new Set(sources.map((s) => s.n));
    const claims = Array.isArray(r.claims) ? r.claims.filter((c) => c && str(c.text).trim()) : [];
    if (!claims.length) return h('p', { class: 'answer-text', text: str(r.answer) });
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
    const sources = (Array.isArray(r.sources) ? r.sources : []).slice().sort((a, b) => a.n - b.n);
    const out = [];
    if (r.blocked) {
      out.push(h('div', { class: 'refusal' }, h('p', { class: 'label', text: 'This question cannot be answered here' }), h('p', { text: str(r.answer) })));
    } else if (r.abstained) {
      const gaps = (r.gaps || []).map(str).filter((g) => g.trim());
      out.push(h('div', { class: 'abstain' }, answerBody(turn, r),
        gaps.length ? [h('p', { class: 'label', text: 'What the sources don\'t cover' }), h('ul', null, gaps.map((g) => h('li', { text: g })))] : null));
    } else {
      out.push(answerBody(turn, r));
    }
    if (sources.length) {
      out.push(h('h3', { class: 'sources-title', text: sources.length === 1 ? 'Source' : 'Sources' }),
        h('ol', { class: 'cards' }, sources.map((s) => sourceCard(turn, s, claims))));
    }
    if (r.ontology_version) out.push(h('p', { class: 'meta', text: `Ontology version ${str(r.ontology_version)}` }));
    clear(turn.body, out);
    turn.body.classList.remove('pending');
  }
  function renderFailed(turn, message, canRetry) {
    const retry = canRetry ? h('button', { class: 'btn', type: 'button' }, 'Try again') : null;
    if (retry) retry.addEventListener('click', () => { if (!S.busy) runTurn(turn); });
    clear(turn.body, h('div', { class: 'failed' }, h('p', { text: message }), retry));
    turn.body.classList.remove('pending');
  }

  // ---- asking -------------------------------------------------------------------------
  function recentTurns() { // not history(): that would hide window.history inside this scope
    return S.turns.filter((t) => t.done).slice(-HISTORY_TURNS).map((t) => ({ q: t.question, a: t.answer }));
  }
  function ask() {
    const ta = $('#question'), question = ta.value.trim();
    if (!question || S.busy || !S.id) return;
    const key = ++S.seq;
    const body = h('div', { class: 'a' });
    const el = h('article', { class: 'turn', 'aria-label': `Question ${key}` },
      h('div', { class: 'q' }, h('p', { class: 'sr-only', text: 'You asked' }), h('p', { text: question })), body);
    $('#log').append(el);
    $('#intro').hidden = true;
    const turn = { key, question, el, body, done: false, answer: '', history: recentTurns() };
    S.turns.push(turn);
    ta.value = '';
    runTurn(turn);
  }
  async function runTurn(turn) {
    const gen = S.gen, started = Date.now();
    setBusy(true);
    const elapsed = h('span', { text: 'Reading the documents.' });
    clear(turn.body, h('div', { class: 'progress', role: 'status' }, h('span', { class: 'spinner', 'aria-hidden': 'true' }), elapsed));
    turn.body.classList.add('pending');
    turn.el.scrollIntoView({ block: 'nearest' });
    const tick = setInterval(() => { elapsed.textContent = `Reading the documents (${Math.round((Date.now() - started) / 1000)} s). This can take a minute.`; }, 1000);
    try {
      let id;
      try {
        ({ id } = await api('/chat', { c: S.id }, { method: 'POST', body: { question: turn.question, history: turn.history } }));
      } catch (e) {
        if (e.status === 429) return renderFailed(turn, `${(e.body && e.body.error) || 'You have reached today\'s question limit.'} The limit resets tomorrow.`, false);
        if (e.status === 400) return renderFailed(turn, (e.body && e.body.error) || 'The question could not be accepted.', false);
        throw e;
      }
      let r = null, errors = 0;
      while (Date.now() - started < POLL_LIMIT_MS) {
        await sleep(POLL_MS);
        if (gen !== S.gen) return;
        try { r = await api('/chat', { c: S.id, id }); errors = 0; } catch (e) { if (e.status === 401 || ++errors >= 3) throw e; continue; }
        if (r && (r.status === 'done' || r.status === 'failed')) break;
        r = null;
      }
      if (gen !== S.gen) return;
      if (!r) return renderFailed(turn, 'No answer after five minutes. The agent may still be working; try again in a moment.', true);
      if (r.status === 'failed') return renderFailed(turn, r.error || 'The answer failed.', true);
      renderDone(turn, r);
      turn.done = true; turn.answer = str(r.answer);
      announce(r.blocked ? 'The question was declined.' : `Answer ready. ${turn.answer}`);
    } catch (e) {
      if (gen === S.gen) renderFailed(turn, e.message || 'Something went wrong.', true);
    } finally {
      clearInterval(tick);
      if (gen === S.gen) { setBusy(false); if (!turn.done) announce('The question did not get an answer.'); }
    }
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
  }
  function switchCollection(id) {
    if (S.busy || id === S.id) return;
    S.id = id; S.gen++; S.turns = [];
    lstore.set(COLL_KEY, id);
    clear($('#log'));
    showCollection();
    $('#question').focus();
  }

  // ---- boot ------------------------------------------------------------------------------
  function wire() {
    $('#ask').addEventListener('submit', (e) => { e.preventDefault(); ask(); });
    $('#question').addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && !e.shiftKey && !e.isComposing) { e.preventDefault(); ask(); }
    });
    $('#coll-select').addEventListener('change', (e) => switchCollection(e.target.value));
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
    // ?ask= fills the box (the ontology page links here with a question), and never sends it
    const asked = new URLSearchParams(location.search).get('ask');
    if (asked) { $('#question').value = asked.slice(0, 2000); window.history.replaceState(null, '', location.pathname); }
    $('#question').focus();
  }
  boot();
})();
