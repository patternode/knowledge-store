/* Knowledge Store pages: what the chat page and the ontology page share. Plain ES2020, no build step.
 *
 * Sign-in is the portal's: Cognito's hosted UI, authorization code with PKCE, tokens in
 * sessionStorage, refreshed shortly before they expire. Every /api call carries the Cognito
 * ACCESS token, because the agent behind the API accepts access tokens only. Cognito returns to
 * one address (config.json's redirectUri, the chat page), so a sign-in started on another page
 * remembers that page and goes back to it once the code is exchanged.
 *
 * Sign-in through a host website (config.json mode "site"): the website signs people in and frames
 * these pages. Over the embed protocol (postMessage: pn:hello, pn:init, pn:ready, then pn:grant),
 * it hands the page a short grant for this lab, renewed before it expires, and every /api call
 * carries it as X-Site-Grant. Only the configured site origin is listened to. The grant is kept in
 * sessionStorage, so the other page in the same frame (chat, ontology) can use it at once rather
 * than wait for the next renewal. Opened on its own, the page sends people to the website.
 *
 * No server text ever reaches innerHTML: pages build nodes with h(), which sets textContent and
 * attributes only.
 */
window.KS = (() => {
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
  const sstore = { // sessionStorage can be unavailable (private windows, blocked storage)
    get(k) { try { return sessionStorage.getItem(k); } catch { return null; } },
    set(k, v) { try { sessionStorage.setItem(k, v); } catch { /* ignore */ } },
    del(k) { try { sessionStorage.removeItem(k); } catch { /* ignore */ } },
  };
  const lstore = { // remembers the chosen collection
    get(k) { try { return localStorage.getItem(k); } catch { return null; } },
    set(k, v) { try { localStorage.setItem(k, v); } catch { /* ignore */ } },
  };
  const safeUrl = (u) => (/^https?:\/\//i.test(String(u || '')) ? String(u) : null);
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  const str = (x) => (x == null ? '' : String(x));

  // ---- config and sign-in (OAuth authorization code with PKCE against Cognito) ----------
  let cfg = { mode: 'local', apiBase: '/api' };
  const TOK = 'ks.chat.tokens', PKCE = 'ks.chat.pkce', COLL_KEY = 'ks.chat.collection';
  const b64url = (buf) => btoa(String.fromCharCode(...new Uint8Array(buf))).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
  const randomB64 = (k) => b64url(crypto.getRandomValues(new Uint8Array(k)));
  const jwtClaims = (t) => { try { return JSON.parse(decodeURIComponent(escape(atob(t.split('.')[1].replace(/-/g, '+').replace(/_/g, '/'))))); } catch { return {}; } };

  const auth = {
    get tokens() { try { return JSON.parse(sstore.get(TOK) || 'null'); } catch { return null; } },
    save(t, old) {
      const claims = jwtClaims(t.access_token || '');
      sstore.set(TOK, JSON.stringify({ id_token: t.id_token || (old && old.id_token), access_token: t.access_token,
        refresh_token: t.refresh_token || (old && old.refresh_token),
        expires_at: claims.exp ? claims.exp * 1000 : Date.now() + (t.expires_in || 3600) * 1000 }));
    },
    redirectUri() { return cfg.redirectUri || (location.origin + location.pathname); },
    async login() {
      const verifier = randomB64(48), state = randomB64(16);
      const challenge = b64url(await crypto.subtle.digest('SHA-256', new TextEncoder().encode(verifier)));
      // back: the page (and its query) to return to; only a path on this site, never a URL
      sstore.set(PKCE, JSON.stringify({ verifier, state, back: location.pathname + location.search }));
      const q = new URLSearchParams({ response_type: 'code', client_id: cfg.oidc.clientId, redirect_uri: this.redirectUri(),
        scope: cfg.oidc.scope || 'openid email', state, code_challenge_method: 'S256', code_challenge: challenge });
      location.assign(`${cfg.oidc.authorize}?${q}`);
    },
    async tokenRequest(params) {
      const r = await fetch(cfg.oidc.token, { method: 'POST',
        headers: { 'content-type': 'application/x-www-form-urlencoded' },
        body: new URLSearchParams({ client_id: cfg.oidc.clientId, ...params }) });
      if (!r.ok) throw new Error(`Sign-in failed (${r.status}).`);
      return r.json();
    },
    async handleRedirect() { // returns an error message, or null
      const q = new URLSearchParams(location.search);
      if (!q.has('code') && !q.has('error')) return null;
      const saved = (() => { try { return JSON.parse(sstore.get(PKCE) || 'null'); } catch { return null; } })();
      sstore.del(PKCE);
      window.history.replaceState(null, '', location.pathname);
      if (q.has('error')) return q.get('error_description') || q.get('error');
      if (!saved || saved.state !== q.get('state')) return 'The sign-in response did not match this browser session. Please sign in again.';
      try {
        this.save(await this.tokenRequest({ grant_type: 'authorization_code', code: q.get('code'),
          redirect_uri: this.redirectUri(), code_verifier: saved.verifier }));
      } catch (e) { return e.message; }
      // Back to the page that started the sign-in: only a page of this site, resolved as a URL (a
      // string check alone misses tricks such as a tab inside "//", which browsers strip).
      let back = null;
      try { back = new URL(String(saved.back || ''), location.origin); } catch { /* none */ }
      if (back && back.origin === location.origin && back.pathname !== location.pathname) {
        location.replace(back.href); // absolute and same-origin, never protocol-relative
        return new Promise(() => {}); // the page is going away
      }
      return null;
    },
    refreshing: null,
    refresh() {
      const t = this.tokens;
      if (!t || !t.refresh_token) return Promise.resolve(false);
      this.refreshing = this.refreshing || this.tokenRequest({ grant_type: 'refresh_token', refresh_token: t.refresh_token })
        .then((r) => { this.save(r, t); return true; }).catch(() => { sstore.del(TOK); return false; })
        .finally(() => { this.refreshing = null; });
      return this.refreshing;
    },
    async accessToken() {
      let t = this.tokens;
      if (!t) return null;
      if (Date.now() > t.expires_at - 60000) { if (!(await this.refresh())) return null; t = this.tokens; }
      return t.access_token || null;
    },
    logout() {
      sstore.del(TOK);
      const q = new URLSearchParams({ client_id: cfg.oidc.clientId, logout_uri: this.redirectUri() });
      location.assign(`${cfg.oidc.logout}?${q}`);
    },
  };

  // ---- sign-in through a host website (mode "site") -------------------------------------
  const GRANT = 'ks.site.grant', PN = 1;
  const framed = window.parent !== window;
  // The grant is held in memory. sessionStorage is only a cache for the other page in the same
  // frame: a browser that blocks third-party storage (Chrome with third-party cookies blocked)
  // refuses it inside the website's frame, and the page must still work.
  const valid = (g) => (g && typeof g.grant === 'string' && typeof g.exp === 'number' && g.exp * 1000 > Date.now() + 5000 ? g : null);
  const site = {
    hostOrigin: null,
    held: null,
    waiters: [],
    get current() { // {grant, exp} while it is valid, else null
      if (valid(site.held)) return site.held;
      try { return valid(JSON.parse(sstore.get(GRANT) || 'null')); } catch { return null; }
    },
    drop() { site.held = null; sstore.del(GRANT); },
    listen() {
      if (!framed) return;
      window.addEventListener('message', (e) => {
        const d = e.data;
        if (e.source !== window.parent || !d || d.pn !== PN || e.origin !== cfg.site.origin) return;
        if (d.type === 'pn:init') {
          site.hostOrigin = e.origin;
          window.parent.postMessage({ pn: PN, type: 'pn:ready', title: document.title, route: '' }, e.origin);
        } else if (d.type === 'pn:grant' && e.origin === site.hostOrigin && typeof d.grant === 'string' && typeof d.exp === 'number') {
          site.held = { grant: d.grant, exp: d.exp };
          sstore.set(GRANT, JSON.stringify(site.held));
          site.waiters.splice(0).forEach((fn) => fn(true));
        }
      });
      window.parent.postMessage({ pn: PN, type: 'pn:hello' }, '*'); // the hello carries nothing
    },
    // Resolves true once a grant is held, or false after `ms` (signed out on the website, or a
    // role this lab does not take: the website then sends none).
    wait(ms) {
      if (site.current) return Promise.resolve(true);
      return new Promise((resolve) => {
        site.waiters.push(resolve);
        setTimeout(() => resolve(!!site.current), ms);
      });
    },
  };

  class ApiError extends Error { constructor(status, msg, body) { super(msg); this.status = status; this.body = body; } }
  async function api(path, params, { method = 'GET', body, retried = false } = {}) {
    const headers = {};
    if (body !== undefined) headers['content-type'] = 'application/json';
    if (cfg.mode === 'site') {
      const g = site.current || ((await site.wait(4000)) && site.current);
      if (!g) throw new ApiError(401, 'Your sign-in has expired. Reload the page on the website.');
      headers['x-site-grant'] = g.grant;
    }
    if (cfg.mode === 'hosted') {
      const t = await auth.accessToken();
      if (!t) { auth.login(); throw new ApiError(401, 'Signing in again.'); }
      headers.authorization = `Bearer ${t}`;
    }
    const qs = new URLSearchParams(Object.entries(params || {}).filter(([, v]) => v != null && v !== '')).toString();
    const r = await fetch(cfg.apiBase + path + (qs ? '?' + qs : ''), { method, headers, cache: 'no-store',
      body: body === undefined ? undefined : JSON.stringify(body) });
    if (r.status === 401 && cfg.mode === 'site') site.drop();
    if (r.status === 401 && cfg.mode === 'hosted') {
      if (!retried && await auth.refresh()) return api(path, params, { method, body, retried: true });
      sstore.del(TOK); auth.login(); throw new ApiError(401, 'Signing in again.');
    }
    let data = null;
    try { data = await r.json(); } catch { /* empty body */ }
    if (!r.ok) throw new ApiError(r.status, (data && data.error) || `The request failed (${r.status}).`, data);
    return data;
  }
  async function loadConfig() { // config.json is written by Terraform; config.local.json is for local development
    for (const url of ['./config.json', './config.local.json']) {
      try { const r = await fetch(url, { cache: 'no-store' }); if (r.ok) return r.json(); } catch { /* try the next */ }
    }
    return { mode: 'local', apiBase: '/api' };
  }

  // Reads config.json, works out Cognito's endpoints, and completes a sign-in that returned
  // here. Returns {cfg, error, signedIn, claims}; never resolves when the sign-in goes back to
  // the page that started it.
  async function start() {
    cfg = { apiBase: '/api', ...(await loadConfig()) };
    cfg.apiBase = String(cfg.apiBase || '/api').replace(/\/$/, '');
    if (cfg.mode === 'site') {
      if (!cfg.site || !/^https?:\/\/[^/]+$/.test(String(cfg.site.origin || ''))) { // https when deployed (Terraform checks)
        return { cfg, error: 'config.json sets site mode without the website\'s origin.', signedIn: false, claims: {} };
      }
      if (!framed) return { cfg, error: null, signedIn: false, claims: {}, standalone: true };
      site.listen();
      const g = (await site.wait(8000)) && site.current;
      return { cfg, error: null, signedIn: !!g, claims: g ? jwtClaims(g.grant) : {} };
    }
    if (cfg.mode !== 'hosted') return { cfg, error: null, signedIn: true, claims: {} };
    if (cfg.cognito && cfg.cognito.domain) { // Cognito's hosted UI: its endpoints follow from the domain
      const d = String(cfg.cognito.domain).replace(/\/$/, '');
      cfg.oidc = { authorize: `${d}/oauth2/authorize`, token: `${d}/oauth2/token`, logout: `${d}/logout`,
        clientId: cfg.cognito.clientId, scope: cfg.cognito.scope };
    }
    if (!cfg.oidc || !cfg.oidc.clientId) return { cfg, error: 'config.json sets hosted mode without a Cognito sign-in configuration.', signedIn: false, claims: {} };
    const error = await auth.handleRedirect();
    const t = auth.tokens;
    return { cfg, error, signedIn: !error && !!t, claims: t ? jwtClaims(t.id_token || '') : {} };
  }
  const brandName = () => str((cfg.brand && cfg.brand.name) || 'Knowledge Store');

  // What a page shows a person who is not signed in: in site mode, a way to the website (the page
  // cannot sign them in itself); otherwise the portal's own sign-in.
  function signedOutNotice(started, title) {
    if (cfg.mode === 'site') {
      const home = String(cfg.site && cfg.site.origin || '');
      return [h('h2', { text: started.standalone ? `Open ${brandName()} from the website` : 'Sign in on the website' }),
        h('p', { text: started.standalone
          ? `${brandName()} opens inside ${home.replace(/^https:\/\//, '')}, where you sign in.`
          : 'Sign in on the website with an account that includes this lab, then reload this page.' }),
        safeUrl(home) ? h('a', { class: 'btn primary', href: home, target: '_top', rel: 'noopener' }, 'Go to the website') : null];
    }
    return [h('h2', { text: started.error ? 'Sign-in did not complete' : title }),
      h('p', { text: started.error || 'This collection is private to its readers. Sign in to continue.' }),
      h('button', { class: 'btn primary', type: 'button', onclick: () => auth.login() }, 'Sign in')];
  }

  return { $, h, clear, sstore, lstore, safeUrl, sleep, str, jwtClaims, auth, api, ApiError, start, brandName, signedOutNotice,
    get cfg() { return cfg; }, COLL_KEY };
})();
