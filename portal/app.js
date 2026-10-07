/* Knowledge Store portal. Vanilla ES2020, no build step.
 *
 * Everything shown here comes from the portal API, and most of it from uploaded documents, so
 * no API text ever reaches innerHTML: the DOM is built with h(), which only sets textContent
 * and attributes. The page names no domain. Type colours are a hash of each type's root class
 * into a fixed palette, and every grouping comes from the ontology's class hierarchy.
 */
(() => {
  'use strict';

  // ---- utilities ------------------------------------------------------------------------
  const $ = (sel) => document.querySelector(sel);
  function h(tag, attrs, ...kids) {
    const e = document.createElement(tag);
    for (const [k, v] of Object.entries(attrs || {})) {
      if (v == null || v === false) continue;
      if (k === 'class') e.className = v;
      else if (k === 'text') e.textContent = v;
      else if (k.startsWith('on')) e.addEventListener(k.slice(2), v);
      else e.setAttribute(k, v === true ? '' : String(v));
    }
    for (const c of kids.flat(Infinity)) if (c != null && c !== false) e.append(c instanceof Node ? c : String(c));
    return e;
  }
  const clear = (el, ...kids) => { el.replaceChildren(...kids.flat(Infinity).filter((k) => k != null && k !== false)); return el; };
  const store = { // sessionStorage can be unavailable (private windows, blocked storage)
    get(k) { try { return sessionStorage.getItem(k); } catch { return null; } },
    set(k, v) { try { sessionStorage.setItem(k, v); } catch { /* ignore */ } },
    del(k) { try { sessionStorage.removeItem(k); } catch { /* ignore */ } },
  };
  const lstore = { // remembers the chosen collection; storage can be blocked
    get(k) { try { return localStorage.getItem(k); } catch { return null; } },
    set(k, v) { try { localStorage.setItem(k, v); } catch { /* ignore */ } },
  };
  const n = (x) => (typeof x === 'number' ? x.toLocaleString() : (x ?? '0'));
  const plural = (k, one, many) => `${n(k)} ${k === 1 ? one : (many || one + 's')}`;
  const when = (iso) => { const d = iso ? new Date(iso) : null; return d && !isNaN(d) ? d.toLocaleString() : ''; };
  const trunc = (s, k) => (s && s.length > k ? s.slice(0, k - 1) + '…' : s || '');
  const safeUrl = (u) => (/^https?:\/\//i.test(String(u || '')) ? String(u) : null);
  const debounce = (fn, ms) => { let t; return (...a) => { clearTimeout(t); t = setTimeout(() => fn(...a), ms); }; };
  const nameOf = (x) => (x && typeof x === 'object' ? (x.name || x.term || x.label || JSON.stringify(x)) : String(x));

  // A categorical palette that reads on both light and dark surfaces. Marks are always paired
  // with text, so colour is never the only carrier of a type.
  const PALETTE = ['#0099c0', '#7077ff', '#e69f00', '#e8457c', '#009e73', '#d55e00', '#56b4e9', '#b07cd8', '#a89200', '#7e8aa7'];
  function hash(s) { let x = 2166136261; for (const ch of String(s)) { x ^= ch.codePointAt(0); x = Math.imul(x, 16777619); } return x >>> 0; }

  // ---- config and sign-in (OIDC authorization code with PKCE: Cognito or Entra ID) ------
  let cfg = { mode: 'local', apiBase: '/api' };
  const TOK = 'kl.tokens', PKCE = 'kl.pkce';
  const b64url = (buf) => btoa(String.fromCharCode(...new Uint8Array(buf))).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
  const randomB64 = (k) => b64url(crypto.getRandomValues(new Uint8Array(k)));
  const jwtClaims = (t) => { try { return JSON.parse(decodeURIComponent(escape(atob(t.split('.')[1].replace(/-/g, '+').replace(/_/g, '/'))))); } catch { return {}; } };

  const auth = {
    get tokens() { try { return JSON.parse(store.get(TOK) || 'null'); } catch { return null; } },
    save(t, old) {
      const claims = jwtClaims((cfg.oidc.useAccessToken ? t.access_token : t.id_token) || '');
      store.set(TOK, JSON.stringify({ id_token: t.id_token, access_token: t.access_token,
        refresh_token: t.refresh_token || (old && old.refresh_token),
        expires_at: claims.exp ? claims.exp * 1000 : Date.now() + (t.expires_in || 3600) * 1000 }));
    },
    redirectUri() { return cfg.redirectUri || (location.origin + location.pathname); },
    async login() {
      const verifier = randomB64(48), state = randomB64(16);
      const challenge = b64url(await crypto.subtle.digest('SHA-256', new TextEncoder().encode(verifier)));
      store.set(PKCE, JSON.stringify({ verifier, state, back: location.hash }));
      const q = new URLSearchParams({ response_type: 'code', client_id: cfg.oidc.clientId, redirect_uri: this.redirectUri(),
        scope: cfg.oidc.scope || 'openid email', state, code_challenge_method: 'S256', code_challenge: challenge });
      location.assign(`${cfg.oidc.authorize}?${q}`);
    },
    async tokenRequest(params) {
      const r = await fetch(cfg.oidc.token, { method: 'POST',
        headers: { 'content-type': 'application/x-www-form-urlencoded' },
        body: new URLSearchParams({ client_id: cfg.oidc.clientId, ...params, ...(cfg.oidc.logoutStyle !== 'cognito' && cfg.oidc.scope ? { scope: cfg.oidc.scope } : {}) }) });
      if (!r.ok) throw new Error(`sign-in failed (${r.status})`);
      return r.json();
    },
    async handleRedirect() { // returns an error message, or null
      const q = new URLSearchParams(location.search);
      if (!q.has('code') && !q.has('error')) return null;
      const saved = (() => { try { return JSON.parse(store.get(PKCE) || 'null'); } catch { return null; } })();
      store.del(PKCE);
      history.replaceState(null, '', location.pathname + ((saved && saved.back) || ''));
      if (q.has('error')) return q.get('error_description') || q.get('error');
      if (!saved || saved.state !== q.get('state')) return 'The sign-in response did not match this browser session. Please sign in again.';
      try {
        this.save(await this.tokenRequest({ grant_type: 'authorization_code', code: q.get('code'),
          redirect_uri: this.redirectUri(), code_verifier: saved.verifier }));
        return null;
      } catch (e) { return e.message; }
    },
    refreshing: null,
    refresh() {
      const t = this.tokens;
      if (!t || !t.refresh_token) return Promise.resolve(false);
      this.refreshing = this.refreshing || this.tokenRequest({ grant_type: 'refresh_token', refresh_token: t.refresh_token })
        .then((r) => { this.save(r, t); return true; }).catch(() => { store.del(TOK); return false; })
        .finally(() => { this.refreshing = null; });
      return this.refreshing;
    },
    // The token the API accepts. Cognito: the ID token, because API Gateway's JWT authorizer checks
    // aud, which only the ID token carries. Entra ID: the access token issued for the API.
    async apiToken() {
      let t = this.tokens;
      if (!t) return null;
      if (Date.now() > t.expires_at - 60000) { if (!(await this.refresh())) return null; t = this.tokens; }
      return cfg.oidc.useAccessToken ? t.access_token : t.id_token;
    },
    logout() {
      store.del(TOK);
      const q = cfg.oidc.logoutStyle === 'cognito'
        ? new URLSearchParams({ client_id: cfg.oidc.clientId, logout_uri: this.redirectUri() })
        : new URLSearchParams({ client_id: cfg.oidc.clientId, post_logout_redirect_uri: this.redirectUri() });
      location.assign(`${cfg.oidc.logout}?${q}`);
    },
  };

  class ApiError extends Error { constructor(status, msg, body) { super(msg); this.status = status; this.body = body; } }
  async function api(path, { method = 'GET', body, retried = false } = {}) {
    const headers = {};
    if (body !== undefined) headers['content-type'] = 'application/json';
    if (cfg.mode === 'hosted') {
      const t = await auth.apiToken();
      if (!t) { auth.login(); throw new ApiError(401, 'Signing in again.'); }
      headers.authorization = `Bearer ${t}`;
    }
    const r = await fetch(cfg.apiBase + scoped(path), { method, headers, body: body === undefined ? undefined : JSON.stringify(body) });
    if (r.status === 401 && cfg.mode === 'hosted') {
      if (!retried && await auth.refresh()) return api(path, { method, body, retried: true });
      store.del(TOK); auth.login(); throw new ApiError(401, 'Signing in again.');
    }
    let data = null;
    try { data = await r.json(); } catch { /* empty body */ }
    if (!r.ok) throw new ApiError(r.status, (data && data.error) || `Request failed (${r.status})`, data);
    return data;
  }
  // Every route but /collections is scoped to one collection with ?c=.
  const COLL = { list: [], id: null, private: false, gen: 0 };
  const scoped = (path) => (path === '/collections' || !COLL.id ? path
    : path + (path.includes('?') ? '&' : '?') + 'c=' + encodeURIComponent(COLL.id));
  const collection = () => COLL.list.find((c) => c.id === COLL.id) || {};
  const q = (params) => new URLSearchParams(Object.entries(params).filter(([, v]) => v != null && v !== '')).toString();

  // ---- state and ontology helpers --------------------------------------------------------
  const S = { status: null, summary: null, ontology: null, classes: new Map(), props: new Map(), children: new Map(), roots: [], built: false };
  function indexOntology(o) {
    S.ontology = o;
    S.classes = new Map((o.classes || []).map((c) => [c.name, c]));
    S.props = new Map([...(o.relations || []).map((p) => [p.name, { ...p, kind: 'relation' }]), ...(o.attributes || []).map((p) => [p.name, { ...p, kind: 'attribute' }])]);
    S.children = new Map(); S.roots = [];
    for (const c of S.classes.values()) {
      const ps = (c.parents || []).filter((p) => S.classes.has(p));
      if (!ps.length) S.roots.push(c.name);
      for (const p of ps) { if (!S.children.has(p)) S.children.set(p, []); S.children.get(p).push(c.name); }
    }
    const byLabel = (a, b) => classLabel(a).localeCompare(classLabel(b));
    S.roots.sort(byLabel); for (const v of S.children.values()) v.sort(byLabel);
  }
  const classLabel = (t) => (S.classes.get(t) && S.classes.get(t).label) || t || '';
  const propLabel = (p) => (S.props.get(p) && S.props.get(p).label) || p || '';
  function rootOf(t) {
    const seen = new Set();
    while (S.classes.has(t) && !seen.has(t)) {
      seen.add(t);
      const ps = (S.classes.get(t).parents || []).filter((p) => S.classes.has(p));
      if (!ps.length) break;
      t = ps.slice().sort()[0];
    }
    return t;
  }
  const colourCache = new Map(); // per collection: types differ between collections
  // Roots take palette slots in name order, so up to PALETTE.length roots never share a colour
  // (a hash can collide); a type outside the ontology falls back to the hash.
  function rootSlot(r) {
    const roots = [...S.classes.keys()].filter((c) => rootOf(c) === c).sort();
    const i = roots.indexOf(r);
    return i >= 0 ? i : hash(r);
  }
  const colourOf = (t) => { if (!colourCache.has(t)) colourCache.set(t, PALETTE[rootSlot(rootOf(t)) % PALETTE.length]); return colourCache.get(t); };
  function classOrder() { // depth-first over the hierarchy: [{name, depth}]
    const out = [], walk = (c, d, path) => {
      if (path.has(c)) return;
      out.push({ name: c, depth: d });
      for (const k of S.children.get(c) || []) walk(k, d + 1, new Set([...path, c]));
    };
    S.roots.forEach((r) => walk(r, 0, new Set()));
    return out;
  }
  const typeChip = (t, onclick) => h(onclick ? 'button' : 'span', { class: 'chip', type: onclick ? 'button' : null, onclick, title: t },
    dot(t), classLabel(t));
  function dot(t) { const d = h('span', { class: 'dot', 'aria-hidden': 'true' }); d.style.background = colourOf(t); return d; }
  function typeOptions(sel, current) {
    clear(sel, h('option', { value: '' , text: 'All types' }),
      classOrder().map(({ name, depth }) => h('option', { value: name, selected: name === current },
        '  '.repeat(depth) + classLabel(name) + ` (${n(S.classes.get(name).count)})`)));
  }
  const notBuilt = () => h('div', { class: 'notice' }, h('p', { text: 'The knowledge graph is not built yet. The Overview tab shows where the pipeline is.' }));

  // ---- tabs and routing ------------------------------------------------------------------
  const TABS = ['overview', 'ontology', 'explore', 'graph', 'terms', 'chat'];
  let current = null;
  function parseHash() {
    let rest = location.hash.replace(/^#/, ''), c = null;
    if (rest.startsWith('c=')) { const i = rest.indexOf('/'); c = decodeURIComponent(i < 0 ? rest.slice(2) : rest.slice(2, i)); rest = i < 0 ? '' : rest.slice(i + 1); }
    const [tab, raw] = rest.split('/');
    return { c, tab, arg: raw ? decodeURIComponent(raw) : null };
  }
  function hashFor(tab, arg) { return `c=${encodeURIComponent(COLL.id || '')}/${tab}${arg ? '/' + encodeURIComponent(arg) : ''}`; }
  function go(tab, arg) { location.hash = hashFor(tab, arg); }
  function route() {
    const { c, tab, arg } = parseHash();
    if (c && c !== COLL.id && COLL.list.some((x) => x.id === c)) { switchCollection(c, false); return; }
    const t = TABS.includes(tab) ? tab : 'overview';
    for (const name of TABS) {
      const on = name === t;
      const b = $(`#tab-${name}`);
      b.setAttribute('aria-selected', String(on)); b.tabIndex = on ? 0 : -1;
      $(`#panel-${name}`).hidden = !on;
    }
    const first = current !== t;
    current = t;
    if (t === 'explore') showExplore(first, arg);
    if (t === 'graph') showGraph(first);
    if (t === 'terms' && first) renderTerms();
    if (t === 'chat' && first) setTimeout(() => $('#chat-q').focus(), 0);
  }
  function wireTabs() {
    const tabs = [...document.querySelectorAll('[role="tab"]')];
    tabs.forEach((b, i) => {
      b.addEventListener('click', () => go(b.dataset.tab));
      b.addEventListener('keydown', (e) => {
        const k = { ArrowRight: 1, ArrowLeft: -1 }[e.key];
        if (k) { const nb = tabs[(i + k + tabs.length) % tabs.length]; nb.focus(); go(nb.dataset.tab); }
        if (e.key === 'Home' || e.key === 'End') { const nb = tabs[e.key === 'Home' ? 0 : tabs.length - 1]; nb.focus(); go(nb.dataset.tab); }
      });
    });
    addEventListener('hashchange', route);
  }

  // ---- dialog ----------------------------------------------------------------------------
  function openDialog(title, body) {
    $('#dlg-title').textContent = title;
    clear($('#dlg-body'), body);
    $('#dlg').showModal();
  }

  // ---- overview --------------------------------------------------------------------------
  const STAGES = {
    never_run: ['Not started', 'The pipeline has not run yet. Add documents to a source and it starts on its own; the scheduled sweep picks up anything it missed.'],
    waiting_for_documents: ['Waiting for documents', (s) => `The lab needs at least ${plural(s.needed || 0, 'document')} before it can propose an ontology, and it has ${n(s.silver_documents || 0)} so far. Add more documents and it continues on its own.`],
    discovering: ['Discovering an ontology', 'The lab is reading a sample of the documents and proposing a draft ontology: the types of thing they talk about, how those relate, and what is recorded about them.'],
    awaiting_curation: ['Awaiting curation', 'A draft ontology is waiting for a person to review and publish it. Nothing is extracted until a version is published, so a person decides the vocabulary the graph uses. The drafts are listed below and in Emerging terms.'],
    extracting: ['Extracting', 'Documents are being read against the active ontology. Entities and facts are recorded with the passages they were found in, so every fact can be traced to its source.'],
    ready: ['Ready', 'The graph is up to date with the documents and the active ontology.'],
    failed: ['Failed', (s) => `The last pipeline run failed${s.error ? ': ' + trunc(s.error, 300) : '.'} Running the pipeline again redoes only the work that is missing.`],
  };
  function stageText(s) {
    const [name, text] = STAGES[s.stage] || [s.stage, 'The pipeline reported a stage this page does not know.'];
    return { name, text: typeof text === 'function' ? text(s) : text };
  }
  function statusCard(s) {
    const { name, text } = stageText(s);
    const bad = s.stage === 'failed', warn = s.stage === 'awaiting_curation';
    return h('div', { class: `notice${bad ? ' bad' : warn ? ' warn' : ''}` },
      h('div', { class: 'status-stage' }, h('strong', { text: name }), h('span', { class: 'stage-name muted', text: s.stage }),
        s.updated_at && h('span', { class: 'small muted', text: `updated ${when(s.updated_at)}` })),
      h('p', { text }),
      h('p', { class: 'small muted' }, [s.active_version ? `Active ontology ${s.active_version}. ` : 'No ontology is active yet. ',
        `${plural(s.silver_documents || 0, 'document')} read.`, s.private ? ' You can see private-scope content.' : '']));
  }
  function draftCard(d) {
    const counts = d.counts ? Object.entries(d.counts).map(([k, v]) => `${n(v)} ${k}`).join(', ') : '';
    const diff = d.diff && typeof d.diff === 'object' ? d.diff : null;
    return h('div', { class: 'card' },
      h('div', { class: 'term-head' }, h('span', { class: 't mono', text: d.draft_id }),
        h('span', { class: 'row' }, h('span', { class: `badge k-${d.kind}`, text: d.kind }),
          (diff && diff.kind) ? h('span', { class: `badge k-${diff.kind}`, text: diff.kind }) : (typeof d.diff === 'string' && h('span', { class: `badge k-${d.diff}`, text: d.diff })))),
      h('p', { class: 'small' }, [d.proposed_version ? `Proposes version ${d.proposed_version}${d.base ? ' over ' + d.base : ''}. ` : '',
        counts ? `Terms: ${counts}. ` : '', d.required_bump ? `Needs a ${d.required_bump} version bump.` : '']),
      diff && h('p', { class: 'small muted' }, ['added', 'removed', 'semantic', 'descriptive'].filter((k) => (diff[k] || []).length)
        .map((k) => `${k}: ${trunc(diff[k].join(', '), 240)}`).join('. ')),
      d.stability_jaccard && typeof d.stability_jaccard === 'object' && h('p', { class: 'small muted', text: 'Stability across samples (Jaccard): ' +
        Object.entries(d.stability_jaccard).map(([k, v]) => `${k} ${v == null ? 'n/a' : Number(v).toFixed(2)}`).join(', ') }),
      d.warning && h('p', { class: 'small error', text: d.warning }),
      (d.rejected || []).length ? h('details', null, h('summary', { text: `${plural(d.rejected.length, 'term')} the model rejected` }),
        h('p', { class: 'small', text: d.rejected.map(nameOf).join(', ') })) : null,
      h('div', { class: 'row mt8' }, h('button', { class: 'btn small', type: 'button', onclick: () => viewDraft(d.draft_id) }, 'View ontology draft (Turtle)')));
  }
  async function viewDraft(id) {
    const pre = h('pre', { class: 'pre', text: 'Loading.' });
    openDialog(`Draft ${id}`, pre);
    try { pre.textContent = (await api('/draft?' + q({ id }))).ttl; } catch (e) { pre.textContent = e.message; }
  }
  function renderOverview() {
    const s = S.status || { stage: 'never_run' }, sm = S.summary, panel = $('#panel-overview');
    if (!sm) {
      const co = collection(), box = h('div', null, (s.drafts || []).length ? s.drafts.map(draftCard) : h('p', { class: 'empty', text: 'No drafts yet.' }));
      clear(panel, h('h3', { text: co.name || co.id || 'Knowledge Store' }), co.description ? h('p', { class: 'lead', text: co.description }) : null,
        h('h2', { class: 'mt12', text: 'Pipeline' }), statusCard(s), h('h2', { text: 'Ontology drafts' }), box);
      if ((s.drafts || []).length) loadDraftsInto(box); // the full reports carry more than the status
      return;
    }
    const p = sm.profile || {}, c = sm.counts || {};
    const chain = new Set(sm.chain || []);
    clear(panel,
      h('div', { class: 'grid2' },
        h('div', null,
          h('h3', { text: p.name || 'Knowledge Store' }),
          h('p', { class: 'lead', text: p.description || '' }),
          (p.key_terms || []).length ? [h('h4', { text: 'Key terms' }), h('div', { class: 'chips' }, p.key_terms.map((t) => h('span', { class: 'chip', text: t })))] : null,
          (p.example_questions || []).length ? [h('h4', { text: 'Try asking' }), h('div', { class: 'chips' },
            p.example_questions.map((x) => h('button', { class: 'chip', type: 'button', onclick: () => askFromElsewhere(x) }, x)))] : null),
        h('div', null,
          h('div', { class: 'tiles' }, [['documents', 'documents'], ['entities', 'entities'], ['facts', 'facts'], ['passages', 'cited passages']]
            .map(([k, l]) => h('div', { class: 'tile' }, h('span', { class: 'num', text: n(c[k] || 0) }), h('span', { class: 'lbl', text: l })))),
          h('h2', { class: 'mt12', text: 'Pipeline' }), statusCard(s))),
      h('h2', { text: 'Sources' }),
      (sm.sources || []).length ? h('div', { class: 'table-wrap' }, h('table', { class: 'kv' },
        h('thead', null, h('tr', null, h('th', { text: 'Name' }), h('th', { text: 'Kind' }), h('th', { text: 'Scope' }))),
        h('tbody', null, sm.sources.map((x) => h('tr', null, h('td', { text: x.name }), h('td', { class: 'mono', text: x.type }), h('td', { text: x.scope })))))) :
        h('p', { class: 'empty', text: 'No sources configured.' }),
      h('h2', { text: 'Ontology versions' }),
      h('p', { class: 'small muted', text: 'Each version records what kind of change it made. The graph is built from the active version and the chain of versions it extends; a semantic or removal change starts a new chain, because earlier extractions no longer mean the same thing.' }),
      h('div', { class: 'table-wrap' }, h('table', { class: 'kv' },
        h('thead', null, h('tr', null, ['Version', 'Change', 'Published', 'Terms', 'Note'].map((t) => h('th', { text: t })))),
        h('tbody', null, (sm.history || []).slice().reverse().map((v) => h('tr', null,
          h('td', null, h('span', { class: 'mono', text: v.version }), v.version === sm.version ? h('span', { class: 'small', text: ' (active)' }) : null,
            chain.has(v.version) || v.in_chain ? h('div', { class: 'small muted', text: 'in active chain' }) : null),
          h('td', null, h('span', { class: `badge k-${v.kind}`, text: v.kind }), v.base ? h('div', { class: 'small muted', text: `over ${v.base}` }) : null),
          h('td', { class: 'small', text: when(v.published_at) }),
          h('td', { class: 'small', text: v.counts ? Object.entries(v.counts).map(([k, x]) => `${n(x)} ${k}`).join(', ') : '' }),
          h('td', { class: 'small', text: v.note || '' })))))),
      (s.drafts || []).length ? [h('h2', { text: 'Ontology drafts awaiting curation' }), h('div', { id: 'ov-drafts' }, s.drafts.map(draftCard))] : null,
      h('p', { class: 'small muted mt12', text: sm.built_at ? `Graph built ${when(sm.built_at)}.` : '' }));
  }
  async function loadDraftsInto(box) { // /api/drafts carries more than the status's summary of each draft
    const gen = COLL.gen;
    try {
      const { drafts } = await api('/drafts');
      if (gen === COLL.gen && box.isConnected) clear(box, drafts.length ? drafts.map(draftCard) : h('p', { class: 'empty', text: 'No drafts yet.' }));
    } catch { /* the status summary is already shown */ }
  }

  // ---- ontology --------------------------------------------------------------------------
  function renderOntology() {
    const panel = $('#panel-ontology');
    if (!S.ontology) return clear(panel, notBuilt());
    const o = S.ontology;
    const node = (name, path) => {
      const c = S.classes.get(name), kids = path.has(name) ? [] : (S.children.get(name) || []);
      const multi = (c.parents || []).filter((p) => S.classes.has(p)).length > 1;
      return h('li', { role: 'treeitem', 'aria-expanded': kids.length ? 'true' : null },
        h('div', { class: 'cls' },
          h('div', { class: 'cls-head' }, dot(name),
            h('button', { class: 'linkish name', type: 'button', title: 'Explore entities of this type', onclick: () => exploreType(name) }, classLabel(name)),
            classLabel(name) !== name ? h('span', { class: 'mono small muted', text: name }) : null,
            h('span', { class: 'pill', text: `${n(c.count)}` }),
            multi ? h('span', { class: 'small muted', text: `also under ${c.parents.filter((p) => S.classes.has(p)).map(classLabel).join(', ')}` }) : null),
          c.definition ? h('p', { class: 'def', text: c.definition }) : null,
          (c.synonyms || []).length ? h('p', { class: 'def', text: 'Also called: ' + c.synonyms.join(', ') }) : null),
        kids.length ? h('ul', { role: 'group' }, kids.map((k) => node(k, new Set([...path, name])))) : null);
    };
    const sig = (xs) => (xs && xs.length ? xs.map(classLabel).join(' | ') : 'any');
    clear(panel,
      h('p', { class: 'small muted' }, `${o.label || 'Ontology'} version ${o.version}. `, h('span', { class: 'mono', text: o.namespace || '' })),
      h('h2', { text: `Classes (${n((o.classes || []).length)})` }),
      h('p', { class: 'small muted', text: 'Counts include entities of every subtype. Select a class to explore its entities.' }),
      h('ul', { class: 'tree', role: 'tree', 'aria-label': 'Class hierarchy' }, S.roots.map((r) => node(r, new Set()))),
      h('h2', { text: `Relations (${n((o.relations || []).length)})` }),
      h('div', { class: 'table-wrap' }, h('table', { class: 'kv' },
        h('thead', null, h('tr', null, ['Relation', 'From', 'To', 'Facts', 'Definition'].map((t) => h('th', { text: t })))),
        h('tbody', null, (o.relations || []).map((r) => h('tr', null,
          h('td', null, h('div', { text: r.label || r.name }), (r.label && r.label !== r.name) ? h('div', { class: 'mono small muted', text: r.name }) : null),
          h('td', { text: sig(r.domain) }), h('td', { text: sig(r.range) }),
          h('td', { class: 'num', text: n(r.count) }), h('td', { class: 'small', text: r.definition || '' })))))),
      h('h2', { text: `Attributes (${n((o.attributes || []).length)})` }),
      h('div', { class: 'table-wrap' }, h('table', { class: 'kv' },
        h('thead', null, h('tr', null, ['Attribute', 'Of', 'Datatype', 'Facts', 'Definition'].map((t) => h('th', { text: t })))),
        h('tbody', null, (o.attributes || []).map((a) => h('tr', null,
          h('td', null, h('div', { text: a.label || a.name }), (a.label && a.label !== a.name) ? h('div', { class: 'mono small muted', text: a.name }) : null),
          h('td', { text: sig(a.domain) }), h('td', { class: 'mono small', text: a.datatype || '' }),
          h('td', { class: 'num', text: n(a.count) }), h('td', { class: 'small', text: a.definition || '' })))))));
  }
  function exploreType(t) { E.type = t; $('#ex-type').value = t; E.dirty = true; go('explore'); }

  // ---- explore and the entity panel ------------------------------------------------------
  const freshE = () => ({ q: '', type: '', offset: 0, items: [], total: 0, dirty: true, selected: null, seq: 0 });
  const E = freshE();
  const PAGE = 50;
  function showExplore(first, id) {
    if (!S.built) { clear($('#ex-detail'), notBuilt()); return; }
    if (E.dirty) { E.dirty = false; searchEntities(true); }
    if (id && id !== E.selected) openEntity($('#ex-detail'), id, 'explore');
    else if (!id && !E.selected) clear($('#ex-detail'), h('div', { class: 'card' }, h('p', { class: 'muted small', text: 'Select an entity to see its types, facts, relations and the passages they were found in.' })));
  }
  async function searchEntities(reset) {
    if (reset) { E.offset = 0; E.items = []; }
    const seq = ++E.seq;
    $('#ex-count').textContent = 'Searching.';
    try {
      const r = await api('/entities?' + q({ q: E.q, type: E.type, limit: PAGE, offset: E.offset }));
      if (seq !== E.seq) return;
      E.items = E.items.concat(r.items || []); E.total = r.total || 0;
      renderResults();
    } catch (e) { if (seq === E.seq) $('#ex-count').textContent = e.message; }
  }
  function renderResults() {
    $('#ex-count').textContent = `${plural(E.total, 'entity', 'entities')}${E.type ? ' of type ' + classLabel(E.type) : ''}${E.q ? ` matching "${E.q}"` : ''}.`;
    clear($('#ex-results'), E.items.map((it) => h('li', null, h('button', { type: 'button', 'aria-current': it.id === E.selected ? 'true' : null,
      onclick: () => go('explore', it.id) },
      h('span', { class: 't', text: it.label }),
      h('span', { class: 'm' }, dot(it.type), classLabel(it.type), h('span', { text: `${plural(it.docs, 'doc')}, ${plural(it.links, 'link')}` })),
      (it.aliases || []).length ? h('span', { class: 'm', text: 'aka ' + it.aliases.join(', ') }) : null))));
    $('#ex-more').hidden = E.items.length >= E.total;
  }
  function wireExplore() {
    const run = debounce(() => { E.q = $('#ex-q').value.trim(); searchEntities(true); }, 250);
    $('#ex-q').addEventListener('input', run);
    $('#ex-type').addEventListener('change', (e) => { E.type = e.target.value; searchEntities(true); });
    $('#ex-more').addEventListener('click', () => { E.offset += PAGE; searchEntities(false); });
  }

  // Renders an entity into a container. ctx is 'explore' or 'graph'; links to other entities
  // stay in the same context.
  async function openEntity(box, id, ctx) {
    if (ctx === 'explore') { E.selected = id; renderResultsCurrent(); }
    clear(box, h('div', { class: 'card' }, h('p', { class: 'thinking' }, h('span', { class: 'spinner', 'aria-hidden': 'true' }), 'Loading entity.')));
    let e;
    try { e = await api('/entity?' + q({ id })); } catch (err) { return clear(box, h('div', { class: 'card' }, h('p', { class: 'error', text: err.message }))); }
    const pids = e.passages || [], pindex = new Map(pids.map((p, i) => [p, i + 1]));
    const passageList = h('div');
    const cite = (ps) => (ps || []).map((p) => h('button', { class: 'cite', type: 'button', title: 'Show the passage',
      'aria-label': `Passage ${pindex.get(p) || p}`, onclick: () => revealPassage(passageList, p) }, String(pindex.get(p) || '?')));
    const label = (i) => (e.labels && e.labels[i]) || i;
    const link = (i) => h('button', { class: 'linkish', type: 'button', onclick: () => (ctx === 'graph' ? openEntity(box, i, 'graph') : go('explore', i)) }, label(i));
    const group = (rows, key) => { const m = new Map(); for (const r of rows) { if (!m.has(r.p)) m.set(r.p, []); m.get(r.p).push(r); } return [...m].map(([p, rs]) => ({ p, rs, key })); };
    const rels = (rows, key, heading) => rows.length ? [h('h4', { text: `${heading} (${rows.length})` }),
      h('ul', { class: 'rel-list' }, group(rows, key).map(({ p, rs }) => rs.map((r) =>
        h('li', null, h('span', { class: 'p', text: propLabel(p) }), link(r[key]), ' ', cite(r.passages)))))] : null;
    const docs = e.doc_info || {};
    for (const p of pids) passageList.append(passageBlock(p, (e.passage_text || {})[p], pindex.get(p), docs));
    clear(box, h('div', { class: 'card accent' },
      h('h3', { text: e.label }),
      h('div', { class: 'chips' }, (e.types || [e.type]).map((t) => typeChip(t, ctx === 'explore' ? () => { exploreType(t); } : null))),
      (e.aliases || []).length ? h('p', { class: 'small muted', text: 'Also known as: ' + e.aliases.join(', ') }) : null,
      e.scope === 'private' ? h('p', { class: 'small', text: 'Private scope: visible to you because you have private access.' }) : null,
      h('div', { class: 'row mt8' },
        ctx === 'graph' ? h('button', { class: 'btn small', type: 'button', onclick: () => refocus(e.id) }, 'Refocus graph here') :
          h('button', { class: 'btn small', type: 'button', onclick: () => { G.focus = e.id; G.dirty = true; go('graph'); } }, 'Show in graph'),
        ctx === 'graph' ? h('button', { class: 'btn small', type: 'button', onclick: () => go('explore', e.id) }, 'Open in Explore') : null),
      (e.attributes || []).length ? [h('h4', { text: 'Attributes' }), h('div', { class: 'table-wrap' }, h('table', { class: 'kv' },
        h('tbody', null, e.attributes.map((a) => h('tr', null, h('td', { class: 'small muted', text: propLabel(a.p) }),
          h('td', null, a.v, ' ', cite(a.passages)))))))] : null,
      rels(e.out || [], 'o', 'Relations out'),
      rels(e.in || [], 's', 'Relations in'),
      h('h4', { text: `Source passages (${pids.length})` }),
      pids.length ? passageList : h('p', { class: 'empty small', text: 'No visible passages.' })));
  }
  function renderResultsCurrent() { if (E.items.length) renderResults(); }
  function passageBlock(pid, p, num, docs) {
    const wrap = h('div', { class: 'passage', 'data-pid': pid });
    const fill = (pv) => {
      const d = (docs && docs[pv.doc]) || {};
      const title = pv.title || d.title || d.name || pv.doc;
      const url = safeUrl(d.source);
      // A markdown source is rendered (safely); any other format shows the text it was parsed to.
      const text = pv.format === 'markdown' ? renderMarkdown(pv.text) : h('div', { text: pv.text });
      text.classList.add('quote', 'clip');
      const toggle = h('button', { class: 'linkish small', type: 'button', 'aria-expanded': 'false' }, 'Show the whole passage');
      toggle.addEventListener('click', () => { const open = text.classList.toggle('clip'); toggle.setAttribute('aria-expanded', String(!open)); toggle.textContent = open ? 'Show the whole passage' : 'Show less'; });
      clear(wrap, h('div', { class: 'small' }, h('span', { class: 'cite', text: String(num || '') }), ' ',
        url ? h('a', { href: url, target: '_blank', rel: 'noopener noreferrer' }, title) : h('strong', { text: title }),
        pv.seq != null ? h('span', { class: 'muted', text: ` · passage ${pv.seq}` }) : null),
      text, (pv.text || '').length > 280 ? toggle : null);
    };
    if (p) fill(p);
    else clear(wrap, h('button', { class: 'linkish small', type: 'button', onclick: async () => {
      try { fill(await api('/passage?' + q({ id: pid }))); } catch (e) { wrap.textContent = e.message; }
    } }, `Load passage ${num || ''}`));
    return wrap;
  }
  function revealPassage(list, pid) {
    const el = [...list.children].find((c) => c.dataset.pid === pid);
    if (!el) return;
    const btn = el.querySelector('button.linkish');
    if (btn && /^Load/.test(btn.textContent)) btn.click();
    el.scrollIntoView({ behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth', block: 'center' });
    el.classList.remove('flash'); void el.offsetWidth; el.classList.add('flash');
  }

  // ---- graph -----------------------------------------------------------------------------
  const freshG = () => ({ type: '', focus: null, limit: 150, dirty: true, hidden: new Set(), sel: null, api: null });
  const G = freshG();
  function showGraph() {
    if (!S.built) { clear($('#g-overlay'), notBuilt()); return; }
    if (typeof d3 === 'undefined') { $('#g-overlay').textContent = 'The graph library did not load. Check your connection and reload the page.'; return; }
    if (G.dirty) { G.dirty = false; loadGraph(); }
  }
  function refocus(id) { G.focus = id; loadGraph(); }
  function wireGraph() {
    $('#g-type').addEventListener('change', (e) => { G.type = e.target.value; G.focus = null; loadGraph(); });
    $('#g-limit').addEventListener('change', (e) => { G.limit = +e.target.value; loadGraph(); });
  }
  async function loadGraph() {
    $('#g-overlay').textContent = 'Loading the graph.';
    G.sel = null;
    const fc = $('#g-focus');
    if (G.focus) {
      clear(fc, 'Focused on an entity ', h('button', { class: 'btn small', type: 'button', onclick: () => { G.focus = null; loadGraph(); } }, 'Clear focus'));
      fc.hidden = false;
    } else fc.hidden = true;
    try {
      const data = await api('/graph?' + q({ type: G.focus ? '' : G.type, focus: G.focus, limit: G.limit }));
      drawGraph(data);
      if (G.focus) { const f = (data.nodes || []).find((x) => x.id === G.focus); if (f) { fc.firstChild.textContent = `Focused on ${f.label} `; selectNode(f); } }
    } catch (e) { $('#g-overlay').textContent = e.message; }
  }
  // Lay the graph out once, in short chunks so the page stays responsive, then hold it still.
  function settle(sim, draw, done) {
    sim.stop(); draw();
    let spent = 0;
    (function chunk() {
      const t0 = performance.now();
      while (sim.alpha() > sim.alphaMin() && performance.now() < t0 + 30) sim.tick();
      spent += performance.now() - t0;
      if (sim.alpha() > sim.alphaMin() && spent < 3000) setTimeout(chunk); else { draw(); if (done) done(); }
    })();
  }
  function drawGraph(data) {
    const box = $('#g-box');
    box.querySelectorAll('svg').forEach((s) => s.remove());
    const nodes = (data.nodes || []).map((d) => ({ ...d }));
    const ids = new Set(nodes.map((d) => d.id));
    const links = (data.edges || []).filter((e) => ids.has(e.s) && ids.has(e.o)).map((e) => ({ source: e.s, target: e.o, p: e.p }));
    $('#g-meta').textContent = `${plural(nodes.length, 'entity', 'entities')}, ${plural(links.length, 'link')}`;
    $('#g-overlay').textContent = nodes.length ? '' : 'No entities to show for this selection.';
    // Legend: one entry per root class present, since colour is by root.
    const roots = new Map();
    for (const d of nodes) { const r = rootOf(d.type); if (!roots.has(r)) roots.set(r, new Set()); roots.get(r).add(d.type); }
    clear($('#g-legend'), [...roots].sort((a, b) => classLabel(a[0]).localeCompare(classLabel(b[0]))).map(([r, types]) => {
      const b = h('button', { class: 'chip', type: 'button', 'aria-pressed': String(!G.hidden.has(r)),
        title: [...types].map(classLabel).join(', ') }, dot(r), classLabel(r), types.size > 1 || !types.has(r) ? h('span', { class: 'muted small', text: `(${[...types].map(classLabel).join(', ')})` }) : null);
      b.addEventListener('click', () => { G.hidden.has(r) ? G.hidden.delete(r) : G.hidden.add(r); b.setAttribute('aria-pressed', String(!G.hidden.has(r))); applyHidden(); });
      return b;
    }));
    if (!nodes.length) return;
    const W = box.clientWidth || 800, H = box.clientHeight || 560;
    const svg = d3.select(box).append('svg').attr('viewBox', [0, 0, W, H])
      .attr('role', 'group').attr('aria-label', `Knowledge graph with ${nodes.length} entities`);
    svg.append('defs').append('marker').attr('id', 'arrow').attr('viewBox', '0 -4 8 8').attr('refX', 8).attr('refY', 0)
      .attr('markerWidth', 6).attr('markerHeight', 6).attr('orient', 'auto')
      .append('path').attr('d', 'M0,-4L8,0L0,4').attr('fill', 'currentColor').attr('class', 'muted');
    const root = svg.append('g');
    const zoom = d3.zoom().scaleExtent([0.15, 6]).on('zoom', (ev) => root.attr('transform', ev.transform));
    svg.call(zoom).on('dblclick.zoom', null);
    svg.on('click', (ev) => { if (ev.target === svg.node()) { G.sel = null; highlight(); } });
    const radius = (d) => Math.min(18, 4 + Math.sqrt(d.links || 0) * 1.6);
    const link = root.append('g').selectAll('line').data(links).join('line').attr('class', 'link').attr('marker-end', 'url(#arrow)');
    link.append('title').text((d) => propLabel(d.p));
    const labelled = new Set(nodes.slice().sort((a, b) => (b.links || 0) - (a.links || 0)).slice(0, 40).map((d) => d.id));
    if (G.focus) labelled.add(G.focus);
    const node = root.append('g').selectAll('g').data(nodes, (d) => d.id).join('g').attr('class', 'node')
      .attr('tabindex', 0).attr('role', 'button').attr('aria-label', (d) => `${d.label}, ${classLabel(d.type)}, ${d.links || 0} links`)
      .on('click', (ev, d) => { ev.stopPropagation(); selectNode(d); })
      .on('dblclick', (ev, d) => { ev.stopPropagation(); refocus(d.id); })
      .on('keydown', (ev, d) => { if (ev.key === 'Enter' || ev.key === ' ') { ev.preventDefault(); selectNode(d); } });
    node.append('circle').attr('r', radius).attr('fill', (d) => colourOf(d.type));
    node.append('text').attr('dx', (d) => radius(d) + 3).attr('dy', '0.35em').text((d) => (labelled.has(d.id) ? trunc(d.label, 32) : ''));
    node.append('title').text((d) => `${d.label} (${classLabel(d.type)})`);
    const draw = () => {
      link.each(function (d) { // stop the line at the target's edge so the arrow shows
        const dx = d.target.x - d.source.x, dy = d.target.y - d.source.y, len = Math.hypot(dx, dy) || 1, r = radius(d.target) + 2;
        this.setAttribute('x1', d.source.x); this.setAttribute('y1', d.source.y);
        this.setAttribute('x2', d.target.x - (dx / len) * r); this.setAttribute('y2', d.target.y - (dy / len) * r);
      });
      node.attr('transform', (d) => `translate(${d.x},${d.y})`);
    };
    const sim = d3.forceSimulation(nodes)
      .force('link', d3.forceLink(links).id((d) => d.id).distance(70).strength(0.35))
      .force('charge', d3.forceManyBody().strength(-160).distanceMax(400))
      .force('center', d3.forceCenter(W / 2, H / 2))
      .force('collide', d3.forceCollide().radius((d) => radius(d) + 4))
      .force('x', d3.forceX(W / 2).strength(0.04)).force('y', d3.forceY(H / 2).strength(0.04));
    node.call(d3.drag().on('start', (ev) => ev.sourceEvent && ev.sourceEvent.stopPropagation())
      .on('drag', (ev, d) => { d.x = ev.x; d.y = ev.y; draw(); }));
    settle(sim, draw, () => { // fit the finished layout to the box
      const xs = nodes.map((d) => d.x), ys = nodes.map((d) => d.y), pad = 40;
      const x0 = Math.min(...xs) - pad, x1 = Math.max(...xs) + pad * 3, y0 = Math.min(...ys) - pad, y1 = Math.max(...ys) + pad;
      const k = Math.min(2, W / (x1 - x0), H / (y1 - y0));
      svg.call(zoom.transform, d3.zoomIdentity.translate(W / 2, H / 2).scale(k).translate(-(x0 + x1) / 2, -(y0 + y1) / 2));
    });
    const nb = new Map(nodes.map((d) => [d.id, new Set([d.id])]));
    for (const l of links) { nb.get(l.source.id || l.source).add(l.target.id || l.target); nb.get(l.target.id || l.target).add(l.source.id || l.source); }
    function highlight() {
      const s = G.sel, near = s ? nb.get(s) || new Set([s]) : null;
      node.classed('hit', (d) => d.id === s).classed('dim', (d) => near && !near.has(d.id));
      link.classed('hot', (d) => s && (d.source.id === s || d.target.id === s)).classed('dim', (d) => near && d.source.id !== s && d.target.id !== s);
    }
    function applyHidden() {
      const off = (d) => G.hidden.has(rootOf(d.type));
      node.classed('off', off);
      link.classed('off', (d) => off(d.source) || off(d.target));
    }
    G.api = { highlight };
    applyHidden();
  }
  function selectNode(d) {
    G.sel = d.id;
    if (G.api) G.api.highlight();
    openEntity($('#g-detail'), d.id, 'graph');
  }

  // ---- emerging terms --------------------------------------------------------------------
  const T = { kind: '', uncovered: false };
  async function renderTerms() {
    const panel = $('#panel-terms');
    const cands = (S.summary && S.summary.candidates) || [];
    const listBox = h('div'), draftBox = h('div', null, h('p', { class: 'muted small', text: 'Loading drafts.' }));
    const kinds = [...new Set(cands.map((c) => c.kind))].sort();
    const kindSel = h('select', { id: 'tm-kind', 'aria-label': 'Kind of term' }, h('option', { value: '', text: 'All kinds' }), kinds.map((k) => h('option', { value: k, selected: k === T.kind, text: k })));
    const unc = h('input', { type: 'checkbox', id: 'tm-unc', checked: T.uncovered });
    const draw = () => {
      const rows = cands.filter((c) => (!T.kind || c.kind === T.kind) && (!T.uncovered || !c.covered_by));
      clear(listBox, rows.length ? rows.map(termCard) : h('p', { class: 'empty', text: cands.length ? 'No terms match these filters.' : 'No candidate terms recorded yet.' }));
    };
    kindSel.addEventListener('change', () => { T.kind = kindSel.value; draw(); });
    unc.addEventListener('change', () => { T.uncovered = unc.checked; draw(); });
    clear(panel,
      h('div', { class: 'notice' },
        h('p', { text: 'While extracting, the lab notes terms the documents use that the ontology does not name. Terms seen across several documents become candidates for the next ontology version.' }),
        h('p', { text: 'Nothing here changes the graph by itself. A revision draft collects the candidates, and a person reviews it and decides whether to publish a new version. Only then does extraction use the new terms.' })),
      h('h2', { text: `Candidate terms (${n(cands.length)})` }),
      S.summary ? h('div', { class: 'toolbar' }, kindSel, h('label', { class: 'row small' }, unc, 'Only terms the ontology does not cover')) : notBuilt(),
      listBox,
      h('h2', { text: 'Drafts awaiting curation' }), draftBox);
    draw();
    try {
      const { drafts } = await api('/drafts');
      clear(draftBox, drafts.length ? drafts.map(draftCard) : h('p', { class: 'empty', text: 'No drafts are waiting.' }));
    } catch (e) { clear(draftBox, h('p', { class: 'error', text: e.message })); }
  }
  function termCard(c) {
    return h('div', { class: 'card' },
      h('div', { class: 'term-head' }, h('span', { class: 't', text: c.term }),
        h('span', { class: 'row' }, h('span', { class: `badge k-${c.kind}`, text: c.kind }), h('span', { class: 'pill', text: plural(c.docs, 'document') }))),
      (c.also || []).length ? h('p', { class: 'small muted', text: 'Also written: ' + c.also.join(', ') }) : null,
      h('p', { class: 'small' }, c.covered_by ? ['Already covered by ', h('span', { class: 'mono', text: classOrPropLabel(c.covered_by) }), '.'] :
        ['Not in the ontology yet.', c.nearest ? [' Nearest existing term: ', h('span', { class: 'mono', text: classOrPropLabel(c.nearest) }), '.'] : null]),
      (c.definitions || []).length ? h('ul', { class: 'small' }, c.definitions.map((d) => h('li', { text: d }))) : null,
      (c.evidence || []).length ? h('details', null, h('summary', { text: `Evidence (${c.evidence.length})` }),
        c.evidence.map((ev) => h('div', null, h('div', { class: 'small muted mono', text: ev.doc_id || '' }), h('div', { class: 'quote', text: ev.text || '' })))) : null);
  }
  const classOrPropLabel = (x) => { const v = nameOf(x); return S.classes.has(v) ? `${classLabel(v)} (${v})` : S.props.has(v) ? `${propLabel(v)} (${v})` : v; };

  // ---- chat ------------------------------------------------------------------------------
  const C = { history: [], busy: false };
  function askFromElsewhere(text) { go('chat'); $('#chat-q').value = text; ask(); }
  function renderInline(s, cite) {
    const out = [], re = /\[p:([^\]\s]+)\]|\*\*([^*]+)\*\*|`([^`]+)`/g;
    let last = 0, m;
    while ((m = re.exec(s))) {
      if (m.index > last) out.push(s.slice(last, m.index));
      if (m[1]) out.push(cite ? cite(m[1]) : m[0]); else if (m[2]) out.push(h('strong', { text: m[2] })); else out.push(h('code', { text: m[3] }));
      last = re.lastIndex;
    }
    if (last < s.length) out.push(s.slice(last));
    return out;
  }
  function renderAnswer(text, citations) {
    const byId = new Map((citations || []).map((c) => [c.id, c])), order = new Map();
    const panel = h('div');
    let open = null;
    const cite = (pid) => {
      if (!order.has(pid)) order.set(pid, order.size + 1);
      const b = h('button', { class: 'cite', type: 'button', 'aria-expanded': 'false', 'aria-label': `Source ${order.get(pid)}`, title: 'Show the cited passage' }, String(order.get(pid)));
      b.addEventListener('click', async () => {
        if (open && open.btn === b) { open.btn.setAttribute('aria-expanded', 'false'); clear(panel); open = null; return; }
        if (open) open.btn.setAttribute('aria-expanded', 'false');
        b.setAttribute('aria-expanded', 'true'); open = { btn: b };
        let p = byId.get(pid);
        if (!p) { clear(panel, h('p', { class: 'small muted', text: 'Loading passage.' })); try { p = await api('/passage?' + q({ id: pid })); byId.set(pid, p); } catch (e) { return clear(panel, h('p', { class: 'small error', text: `Passage ${pid}: ${e.message}` })); } }
        clear(panel, passageBlock(pid, p, order.get(pid), null));
      });
      return b;
    };
    const md = renderMarkdown(text, cite);
    return { md, panel, count: () => order.size };
  }
  // A safe markdown subset (headings, rules, lists, paragraphs, bold and code), built from DOM
  // nodes only: text from documents and models never reaches innerHTML. cite is optional.
  function renderMarkdown(text, cite) {
    const md = h('div', { class: 'md' });
    const bullet = /^\s*(?:[-*•]|\d+[.)])\s+/;
    let para = null, list = null;
    for (const raw of String(text || '').split('\n')) {
      const l = raw.trimEnd();
      if (!l.trim()) { para = list = null; continue; }
      if (/^\s*(?:[-*_]\s*){3,}$/.test(l)) { para = list = null; md.append(h('hr')); continue; }
      if (/^#{1,6}\s/.test(l)) { para = list = null; md.append(h('h4', null, renderInline(l.replace(/^#+\s*/, ''), cite))); continue; }
      if (bullet.test(l)) {
        const tag = /^\s*\d/.test(l) ? 'OL' : 'UL';
        if (!list || list.tagName !== tag) { para = null; list = h(tag.toLowerCase()); md.append(list); }
        list.append(h('li', null, renderInline(l.replace(bullet, ''), cite)));
        continue;
      }
      list = null;
      if (!para) { para = h('p'); md.append(para); } else para.append(h('br'));
      para.append(...renderInline(l, cite));
    }
    return md;
  }
  function traceBlock(trace, usage) {
    if (!(trace || []).length) return null;
    return h('details', { class: 'trace' }, h('summary', { text: `How it answered: ${plural(trace.length, 'tool call')}` }),
      h('ol', null, trace.map((t) => h('li', null, h('span', { class: 'mono', text: t.tool }), ' ', h('code', { text: JSON.stringify(t.input || {}) })))),
      usage ? h('p', { class: 'small muted', text: `Tokens: ${n(usage.inputTokens)} in, ${n(usage.outputTokens)} out.` }) : null);
  }
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  async function ask() {
    const ta = $('#chat-q'), question = ta.value.trim();
    if (!question || C.busy) return;
    if (!S.built) { $('#chat-hint').textContent = 'The knowledge graph is not built yet, so there is nothing to ask about.'; return; }
    C.busy = true; $('#chat-send').disabled = true; $('#chat-hint').textContent = '';
    const gen = COLL.gen;
    const log = $('#chat-log');
    log.append(h('div', { class: 'msg user', text: question }));
    const started = Date.now();
    const status = h('span', { text: 'Thinking.' });
    const bot = h('div', { class: 'msg bot', 'aria-busy': 'true' }, h('div', { class: 'thinking' }, h('span', { class: 'spinner', 'aria-hidden': 'true' }), status));
    log.append(bot); bot.scrollIntoView({ block: 'nearest' });
    ta.value = '';
    try {
      const { id } = await api('/chat', { method: 'POST', body: { question, history: C.history.slice(-6) } });
      let r;
      for (;;) {
        await sleep(1500);
        if (Date.now() - started > 180000) throw new Error('No answer after three minutes. The question may still finish; try asking again later.');
        if (gen !== COLL.gen) return;
        r = await api('/chat?' + q({ id }));
        status.textContent = `Thinking (${Math.round((Date.now() - started) / 1000)}s).`;
        if (r.status === 'done' || r.status === 'failed') break;
      }
      if (gen !== COLL.gen) return; // the collection changed while this was answered
      if (r.status === 'failed') throw new Error(r.error || 'The answer failed.');
      const { md, panel, count } = renderAnswer(r.answer, r.citations);
      clear(bot, md, panel, h('p', { class: 'small muted', text: count() ? `${plural(count(), 'source')} cited.` : 'No passages cited.' }), traceBlock(r.trace, r.usage));
      C.history.push({ q: question, a: r.answer || '' });
    } catch (e) {
      bot.classList.add('failed');
      const msg = e.status === 429 ? ((e.body && e.body.error) || 'You have reached today\'s question limit.') + ' The limit resets tomorrow.' : e.message;
      clear(bot, h('p', { class: 'error', text: msg }));
      if (!ta.value) ta.value = question;
    } finally {
      bot.removeAttribute('aria-busy');
      if (gen === COLL.gen) { C.busy = false; $('#chat-send').disabled = false; }
    }
  }
  function wireChat() {
    $('#chat-form').addEventListener('submit', (e) => { e.preventDefault(); ask(); });
    $('#chat-q').addEventListener('keydown', (e) => { if (e.key === 'Enter' && !e.shiftKey && !e.isComposing) { e.preventDefault(); ask(); } });
    $('#chat-new').addEventListener('click', () => { C.history = []; clear($('#chat-log')); $('#chat-q').focus(); });
    $('#chat-hint').textContent = 'Enter to send, Shift and Enter for a new line.';
  }
  function renderChatExamples() {
    const ex = (S.summary && S.summary.profile && S.summary.profile.example_questions) || [];
    clear($('#chat-examples'), ex.length ? [h('h4', { text: 'Examples' }), h('div', { class: 'chips' },
      ex.map((x) => h('button', { class: 'chip', type: 'button', onclick: () => { $('#chat-q').value = x; ask(); } }, x)))] : null);
  }

  // ---- boot ------------------------------------------------------------------------------
  function header() {
    const s = S.status || {}, pill = $('#stage-pill');
    pill.hidden = false; clear(pill, 'pipeline ', h('b', { text: stageText(s).name }));
    const v = (S.summary && S.summary.version) || s.active_version;
    $('#version-pill').hidden = !v; if (v) clear($('#version-pill'), 'ontology ', h('b', { text: v }));
    const co = collection(), name = (S.summary && S.summary.profile && S.summary.profile.name) || co.name || co.id || 'Knowledge Store';
    $('#coll-name').textContent = name; document.title = `${name} · Knowledge Store`;
    if (co.id && s.stage) co.stage = s.stage;
    const sel = $('#coll-select');
    sel.parentElement.hidden = COLL.list.length < 2;
    clear(sel, COLL.list.map((c) => h('option', { value: c.id, selected: c.id === COLL.id }, `${c.name || c.id} (${stageText(c).name})`)));
  }
  async function loadAll() {
    const gen = COLL.gen;
    const status = await api('/status');
    let summary = null, ontology = null;
    try {
      summary = await api('/summary');
      ontology = await api('/ontology');
    } catch (e) {
      if (e.status !== 409) throw e;
      summary = ontology = null;
    }
    if (gen !== COLL.gen) return; // superseded by a collection switch
    S.status = status; S.summary = summary; S.built = !!ontology;
    colourCache.clear();
    if (ontology) indexOntology(ontology);
    header();
    renderOverview();
    renderOntology();
    for (const [sel, cur] of [[$('#ex-type'), E.type], [$('#g-type'), G.type]]) {
      if (S.built) typeOptions(sel, cur); else clear(sel, h('option', { value: '', text: 'All types' }));
    }
    renderChatExamples();
  }
  function resetViews() {
    Object.assign(S, { status: null, summary: null, ontology: null, classes: new Map(), props: new Map(), children: new Map(), roots: [], built: false });
    Object.assign(E, freshE()); Object.assign(G, freshG()); Object.assign(T, { kind: '', uncovered: false });
    C.history = []; C.busy = false; $('#chat-send').disabled = false;
    colourCache.clear();
    $('#ex-q').value = '';
    for (const id of ['#ex-results', '#ex-detail', '#chat-log', '#g-legend', '#panel-overview', '#panel-ontology', '#panel-terms']) clear($(id));
    $('#ex-count').textContent = ''; $('#g-meta').textContent = ''; $('#g-focus').hidden = true; $('#ex-more').hidden = true;
    $('#g-box').querySelectorAll('svg').forEach((x) => x.remove());
    clear($('#g-detail'), h('div', { class: 'card' }, h('p', { class: 'muted small', text: 'Click a node to see its entity. Double-click, or use Refocus, to centre the graph on its neighbourhood.' })));
    current = null;
  }
  async function switchCollection(id, rewriteHash = true) {
    COLL.id = id; COLL.gen++;
    lstore.set('kl.collection', id);
    resetViews();
    $('#coll-select').value = id;
    clear($('#panel-overview'), h('p', { class: 'muted', text: 'Loading the collection.' }));
    try { await loadAll(); } catch (e) { clear($('#panel-overview'), h('p', { class: 'error', text: e.message })); }
    if (rewriteHash) { const { tab } = parseHash(); location.hash = hashFor(TABS.includes(tab) ? tab : 'overview'); }
    route();
  }
  function chooser() { // first visit with several collections: a card per collection
    return new Promise((resolve) => {
      bootMessage(h('h3', { text: 'Choose a collection' }),
        h('p', { class: 'muted', text: 'Each collection is its own set of documents with its own ontology.' }),
        h('div', { class: 'coll-grid' }, COLL.list.map((c) => h('button', { class: 'card coll-card', type: 'button', onclick: () => resolve(c.id) },
          h('span', { class: 't', text: c.name || c.id }), c.description ? h('span', { class: 'small muted', text: trunc(c.description, 220) }) : null,
          h('span', { class: 'row small' }, h('span', { class: 'pill', text: stageText(c).name }), c.active_version ? h('span', { class: 'pill', text: `ontology ${c.active_version}` }) : null)))));
    });
  }
  function bootMessage(...kids) { const b = $('#boot'); b.hidden = false; clear(b, kids); }
  async function loadConfig() {
    for (const url of ['./config.json', './config.local.json']) {
      try { const r = await fetch(url, { cache: 'no-store' }); if (r.ok) return r.json(); } catch { /* try the next */ }
    }
    return { mode: 'local', apiBase: '/api' };
  }
  async function boot() {
    $('#dlg-close').addEventListener('click', () => $('#dlg').close());
    cfg = { apiBase: '/api', ...(await loadConfig()) };
    cfg.apiBase = String(cfg.apiBase || '/api').replace(/\/$/, '');
    if (cfg.brand && cfg.brand.name) $('#brand-name').textContent = String(cfg.brand.name);
    if (cfg.mode === 'hosted') {
      if (cfg.cognito && cfg.cognito.domain) { // Cognito's hosted UI: its endpoints follow from the domain
        const d = cfg.cognito.domain.replace(/\/$/, '');
        cfg.oidc = { authorize: `${d}/oauth2/authorize`, token: `${d}/oauth2/token`, logout: `${d}/logout`,
          logoutStyle: 'cognito', clientId: cfg.cognito.clientId, scope: cfg.cognito.scope, useAccessToken: false };
      }
      if (!cfg.oidc || !cfg.oidc.authorize || !cfg.oidc.token || !cfg.oidc.clientId) return bootMessage(h('p', { class: 'error', text: 'config.json sets hosted mode without a sign-in configuration (cognito or oidc).' }));
      const err = await auth.handleRedirect();
      if (err) return bootMessage(h('h3', { text: 'Sign-in did not complete' }), h('p', { class: 'muted', text: err }),
        h('button', { class: 'btn primary', type: 'button', onclick: () => auth.login() }, 'Sign in'));
      if (!auth.tokens) return auth.login();
      const c = jwtClaims(auth.tokens.id_token || '');
      $('#user').textContent = c.email || c.preferred_username || c.name || c['cognito:username'] || '';
      $('#signout').hidden = false;
      $('#signout').addEventListener('click', () => auth.logout());
    }
    wireTabs(); wireExplore(); wireGraph(); wireChat();
    $('#coll-select').addEventListener('change', (e) => switchCollection(e.target.value));
    try {
      const r = await api('/collections');
      COLL.list = r.collections || []; COLL.private = !!r.private;
      if (!COLL.list.length) return bootMessage(h('h3', { text: 'No collections yet' }), h('p', { class: 'muted', text: 'The lab has no collections configured.' }));
      const known = (id) => id && COLL.list.some((c) => c.id === id);
      const fromHash = parseHash().c, remembered = lstore.get('kl.collection');
      COLL.id = known(fromHash) ? fromHash : known(remembered) ? remembered : COLL.list.length === 1 ? COLL.list[0].id : await chooser();
      lstore.set('kl.collection', COLL.id);
      if (parseHash().c !== COLL.id) { const { tab, arg } = parseHash(); history.replaceState(null, '', '#' + hashFor(TABS.includes(tab) ? tab : 'overview', arg)); }
      bootMessage(h('p', { class: 'muted', text: 'Loading the collection.' }));
      await loadAll();
    } catch (e) {
      return bootMessage(h('h3', { text: 'The lab could not be reached' }), h('p', { class: 'muted', text: e.message }),
        h('button', { class: 'btn', type: 'button', onclick: () => location.reload() }, 'Try again'));
    }
    $('#boot').hidden = true; $('#tabs').hidden = false;
    route();
    // While the pipeline is working, check on it every minute.
    setInterval(async () => {
      if (!S.status || !['discovering', 'extracting', 'waiting_for_documents', 'awaiting_curation'].includes((S.status || {}).stage)) return;
      const gen = COLL.gen;
      try {
        const before = S.status.stage, s = await api('/status');
        if (gen !== COLL.gen) return;
        S.status = s;
        if (s.stage !== before || (s.stage === 'ready' && !S.built)) { await loadAll(); E.dirty = G.dirty = true; if (current === 'explore' || current === 'graph') route(); }
        else { header(); if (current === 'overview') renderOverview(); }
      } catch { /* try again next time */ }
    }, 60000);
  }
  boot();
})();
