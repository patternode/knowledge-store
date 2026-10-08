/* Knowledge Store ontology page: the active ontology of a collection as a force-directed graph,
 * with its statistics. Plain ES2020 and D3 (vendor/d3.min.js), no build step.
 *
 * Classes are spheres coloured by their root class; subclass links are solid and pale, declared
 * relations run from domain to range, and relations the data uses between classes the ontology
 * does not declare for them are dashed, weighted by use. Three tiers, by place in the ontology rather than by size:
 *   core        the most connected classes (by declared and seen links): larger, gold, pulled to
 *               the centre (the most connected of all most strongly), links between two of them
 *               drawn heavier
 *   supporting  every other class with entities: the standard sphere
 *   empty       a class with no entities: a small dashed ring, pushed out to ring the edge
 * Population is shown separately: the pill counts a class's entities (subtypes included), and a
 * thin arc round the node says how populated it is against the largest class, on a log scale so
 * small classes still show.
 *
 * Every name and definition comes from the ontology, which a model may have proposed, so text
 * reaches the page through textContent only (h() and D3's .text()), never innerHTML.
 */
function main() {
  'use strict';
  const { $, h, clear, lstore, str, auth, api, COLL_KEY } = window.KS;

  // The portal's palette without its golds, which would read as the core classes' gold.
  const PALETTE = ['#0099c0', '#7077ff', '#e8457c', '#009e73', '#d55e00', '#56b4e9', '#b07cd8', '#7e8aa7', '#2fa59a', '#c25bb0'];
  const n = (x) => Number(x || 0).toLocaleString();
  const plural = (k, one, many) => `${n(k)} ${k === 1 ? one : (many || one + 's')}`;
  const reduced = () => matchMedia('(prefers-reduced-motion: reduce)').matches;
  const announce = (text) => { const a = $('#announce'); a.textContent = ''; setTimeout(() => { a.textContent = text; }, 50); };
  function notice(...kids) { const el = $('#notice'); el.hidden = !kids.length; clear(el, kids); }

  // ---- state ------------------------------------------------------------------------------
  const S = { collections: [], id: null, private: false, gen: 0, onto: null, summary: null, view: null };

  // ---- the ontology, indexed ------------------------------------------------------------
  function model(o) {
    const classes = new Map((o.classes || []).map((c) => [c.name, c]));
    const parentsOf = (c) => ((classes.get(c) || {}).parents || []).filter((p) => classes.has(p));
    const ancestors = (c) => { // c itself and every class above it
      const out = new Set(), todo = [c];
      while (todo.length) { const x = todo.pop(); if (out.has(x) || !classes.has(x)) continue; out.add(x); todo.push(...parentsOf(x)); }
      return out;
    };
    const rootOf = (c) => {
      const seen = new Set();
      while (classes.has(c) && !seen.has(c)) { seen.add(c); const ps = parentsOf(c); if (!ps.length) break; c = ps.slice().sort()[0]; }
      return c;
    };
    const roots = [...classes.keys()].filter((c) => !parentsOf(c).length).sort();
    const colour = (c) => PALETTE[(roots.indexOf(rootOf(c)) >>> 0) % PALETTE.length];
    const label = (c) => (classes.get(c) && classes.get(c).label) || c || '';
    const relations = o.relations || [], attributes = o.attributes || [];
    // A relation seen between two classes counts as declared when a declared relation of that
    // name covers them: its domain and range are the classes or classes above them (or open).
    const covers = (xs, c) => !xs || !xs.length || [...ancestors(c)].some((a) => xs.includes(a));
    const declares = (p, d, r) => relations.some((x) => x.name === p && covers(x.domain, d) && covers(x.range, r));
    const observed = (o.observed || []).filter((e) => classes.has(e.domain) && classes.has(e.range));
    return { o, classes, parentsOf, ancestors, roots, colour, label, relations, attributes, declares, observed };
  }

  // ---- the graph ------------------------------------------------------------------------
  const CLASS_R = 30, CORE_R = 36, HUB_R = 44, EMPTY_R = 18;
  // The layout's room: link lengths, repulsion and the gap kept round each class.
  const SPREAD = 1.25;

  function buildView(M) {
    const box = $('#onto-graph');
    box.querySelectorAll('svg.onto-svg').forEach((s) => s.remove());
    const tipEl = $('#onto-tip');
    const onodes = [], olinks = [], oById = new Map();
    for (const c of M.classes.values()) {
      const d = { id: c.name, ...c, n: c.count || 0 };
      onodes.push(d); oById.set(d.id, d);
    }
    for (const c of M.classes.values()) for (const p of M.parentsOf(c.name)) olinks.push({ source: c.name, target: p, kind: 'sub' });
    for (const r of M.relations) {
      for (const d of r.domain || []) for (const t of r.range || []) {
        if (oById.has(d) && oById.has(t)) olinks.push({ source: d, target: t, kind: 'obj', label: r.label || r.name, prop: r.name });
      }
    }
    // What the data shows: class-to-class links through a relation where the ontology does not
    // declare it for those classes (drawn dashed, weighted by use).
    for (const e of M.observed) {
      if (e.domain === e.range || M.declares(e.p, e.domain, e.range)) continue;
      const r = M.relations.find((x) => x.name === e.p);
      olinks.push({ source: e.domain, target: e.range, kind: 'seen', label: (r && r.label) || e.p, prop: e.p, count: e.count });
    }
    // parallel links between the same pair are bent apart
    const pairCount = new Map();
    for (const l of olinks) { const k = [l.source, l.target].sort().join('|'); l.rank = pairCount.get(k) || 0; pairCount.set(k, l.rank + 1); }

    // Core: the most connected populated classes, by distinct classes they link to through
    // declared or seen relations; the first of them is the hub, held at the centre.
    const degree = new Map();
    for (const l of olinks) {
      if (l.kind === 'sub' || l.source === l.target) continue;
      for (const [a, b] of [[l.source, l.target], [l.target, l.source]]) { if (!degree.has(a)) degree.set(a, new Set()); degree.get(a).add(b); }
    }
    const deg = (id) => (degree.get(id) || new Set()).size;
    const coreCount = Math.max(1, Math.min(6, Math.round(onodes.length / 6)));
    const core = onodes.filter((d) => d.n > 0 && deg(d.id) > 0)
      .sort((a, b) => deg(b.id) - deg(a.id) || b.n - a.n || a.id.localeCompare(b.id)).slice(0, coreCount);
    const CORE = new Set(core.map((d) => d.id)), HUB = core.length ? core[0].id : null;
    const isCore = (d) => CORE.has(d.id);
    const tierOf = (d) => (isCore(d) ? 'core' : d.n > 0 ? 'supporting' : 'empty');
    const radius = (d) => (d.id === HUB ? HUB_R : isCore(d) ? CORE_R : d.n > 0 ? CLASS_R : EMPTY_R);
    const maxN = Math.max(1, ...onodes.map((d) => d.n));
    const popShare = (d) => (d.n > 0 ? Math.max(0.03, Math.log1p(d.n) / Math.log1p(maxN)) : 0);

    const w = Math.max(320, box.clientWidth), hgt = Math.max(320, box.clientHeight);
    const svg = d3.select(box).insert('svg', ':first-child').attr('class', 'onto-svg').attr('viewBox', [0, 0, w, hgt])
      .attr('role', 'img').attr('aria-label', `Graph of ${plural(onodes.length, 'class', 'classes')} and the links between them. The Classes and Properties lists hold the same information.`);
    const defs = svg.append('defs');
    for (const [id, fill] of [['oarrow-sub', '#d5dbe9'], ['oarrow-obj', '#909cff'], ['oarrow-seen', '#e8457c']]) {
      defs.append('marker').attr('id', id).attr('viewBox', '0 -4 8 8').attr('refX', 8).attr('refY', 0)
        .attr('markerWidth', 6).attr('markerHeight', 6).attr('orient', 'auto').append('path').attr('d', 'M0,-4L8,0L0,4').attr('fill', fill);
    }
    // A slight 3D look: each class colour as a sphere lit from the top left, a soft sheen and a
    // shadow below. One gradient per colour; the sheen and shadow are shared.
    const shade = (c) => `oshade-${String(c).replace(/[^a-z0-9]/gi, '')}`;
    for (const c of new Set(onodes.map((d) => M.colour(d.id)))) {
      const base = d3.color(c), grad = defs.append('radialGradient').attr('id', shade(c)).attr('cx', '35%').attr('cy', '30%').attr('r', '75%');
      grad.append('stop').attr('offset', '0%').attr('stop-color', base.brighter(0.9).formatHex());
      grad.append('stop').attr('offset', '50%').attr('stop-color', base.formatHex());
      grad.append('stop').attr('offset', '100%').attr('stop-color', base.darker(1.4).formatHex());
    }
    const gold = defs.append('radialGradient').attr('id', 'oshade-core').attr('cx', '35%').attr('cy', '30%').attr('r', '75%');
    for (const [o, c] of [['0%', '#ffd27a'], ['50%', '#c88a1e'], ['100%', '#5e3e08']]) gold.append('stop').attr('offset', o).attr('stop-color', c);
    const sheen = defs.append('radialGradient').attr('id', 'osheen').attr('cx', '50%').attr('cy', '50%').attr('r', '50%');
    sheen.append('stop').attr('offset', '0%').attr('stop-color', '#ffffff').attr('stop-opacity', 0.35);
    sheen.append('stop').attr('offset', '100%').attr('stop-color', '#ffffff').attr('stop-opacity', 0);
    defs.append('filter').attr('id', 'oshadow').attr('x', '-50%').attr('y', '-50%').attr('width', '200%').attr('height', '200%')
      .append('feDropShadow').attr('dx', 0).attr('dy', 4).attr('stdDeviation', 4).attr('flood-color', '#000').attr('flood-opacity', 0.55);

    const g = svg.append('g');
    const zoom = d3.zoom().scaleExtent([0.2, 5]).on('zoom', (ev) => g.attr('transform', ev.transform));
    svg.call(zoom);
    svg.on('click', (ev) => { if (ev.target === svg.node()) { reset(); route({}); } });

    function tip(ev, ...kids) {
      if (!kids.length) { tipEl.hidden = true; return; }
      clear(tipEl, kids);
      tipEl.hidden = false;
      const r = box.getBoundingClientRect();
      const x = ev.clientX - r.left, y = ev.clientY - r.top, tw = tipEl.offsetWidth, th = tipEl.offsetHeight;
      tipEl.style.left = Math.max(4, x + 12 + tw > r.width ? x - 12 - tw : x + 12) + 'px';
      tipEl.style.top = Math.max(4, y + 12 + th > r.height ? y - 12 - th : y + 12) + 'px';
    }

    // The pull to the centre by tier: the hub most, then the other core classes; classes no link
    // reaches would drift to the rim, so a gentle pull keeps the rest together. The empty classes
    // are pushed out instead, to a ring past the populated ontology.
    const PULL = { hub: 0.3, core: 0.07, supporting: 0.04, empty: 0.01 };
    const pull = (d) => (d.id === HUB ? PULL.hub : PULL[tierOf(d)]);
    const RIM = SPREAD * Math.max(260, 58 * Math.sqrt(onodes.length));
    const sim = d3.forceSimulation(onodes)
      .force('link', d3.forceLink(olinks).id((d) => d.id)
        .distance((l) => SPREAD * (l.kind === 'sub' ? 110 : 160))
        .strength((l) => (l.kind === 'sub' ? 0.6 : 0.12)))
      .force('charge', d3.forceManyBody().strength(-300 * SPREAD).distanceMax(400 * SPREAD))
      .force('center', d3.forceCenter(w / 2, hgt / 2))
      .force('x', d3.forceX(w / 2).strength(pull)).force('y', d3.forceY(hgt / 2).strength(pull))
      .force('rim', d3.forceRadial(RIM, w / 2, hgt / 2).strength((d) => (tierOf(d) === 'empty' ? 0.05 : 0)))
      .force('collision', d3.forceCollide().radius((d) => radius(d) + 26 * SPREAD + 8));
    const idOf = (x) => (x && x.id) || x;
    const coreLink = (l) => CORE.has(idOf(l.source)) && CORE.has(idOf(l.target));

    const olink = g.append('g').selectAll('path').data(olinks).join('path')
      .attr('class', (d) => `olink ${d.kind}${coreLink(d) ? ' core' : ''}`)
      .attr('marker-end', (d) => `url(#oarrow-${d.kind})`)
      .attr('stroke-width', (d) => (d.kind === 'seen' ? Math.min(4, 0.8 + Math.log2(1 + d.count) * 0.5) : null))
      .on('mouseover', (ev, d) => tip(ev, d.kind === 'sub'
        ? [h('b', { text: M.label(d.source.id) }), ' is a kind of ', h('b', { text: M.label(d.target.id) })]
        : [h('b', { text: d.label }), ` ${M.label(d.source.id)} → ${M.label(d.target.id)}`,
          d.kind === 'seen' ? ` · seen ${plural(d.count, 'time')}, not declared` : ' · declared']))
      .on('mouseout', () => tip())
      .on('click', (ev, d) => { ev.stopPropagation(); if (d.prop) selectProperty(d.prop); });
    const olabel = g.append('g').selectAll('text').data(olinks.filter((l) => l.kind !== 'sub')).join('text')
      .attr('class', 'olabel').attr('text-anchor', 'middle').text((d) => d.label);
    const drag = d3.drag().on('drag', (ev, d) => { d.x = ev.x; d.y = ev.y; draw(); });
    const onode = g.append('g').selectAll('g').data(onodes).join('g')
      .attr('class', (d) => `onode ${tierOf(d)}`)
      .on('mouseover', (ev, d) => tip(ev, h('b', { text: M.label(d.id) }), ` · ${plural(d.n, 'entity', 'entities')}`, isCore(d) ? ' · core' : ''))
      .on('mouseout', () => tip())
      .on('click', (ev, d) => { ev.stopPropagation(); select(d.id); })
      .call(drag);
    // the halo a found class wears (the find box): drawn first, so it sits behind
    onode.append('circle').attr('class', 'ohalo').attr('r', (d) => radius(d) + 14);
    const solid = (d) => isCore(d) || d.n > 0;
    onode.append('circle').attr('class', 'obody').attr('r', radius)
      .attr('fill', (d) => (isCore(d) ? 'url(#oshade-core)' : d.n ? `url(#${shade(M.colour(d.id))})` : 'none'))
      .attr('filter', (d) => (solid(d) ? 'url(#oshadow)' : null))
      // a core class has a gold outline; a class with no entities is a small hollow dashed ring
      .style('stroke', (d) => (isCore(d) ? '#ffcf66' : !d.n ? M.colour(d.id) : null))
      .style('stroke-width', (d) => (isCore(d) ? '2px' : !d.n ? '1.5px' : null))
      .style('stroke-dasharray', (d) => (!solid(d) ? '4,3' : null))
      .style('fill', (d) => (!solid(d) ? 'rgba(255, 255, 255, .04)' : null));
    // the sheen: a soft light spot towards the top left (an ellipse, so the circle rules skip it)
    onode.filter(solid).append('ellipse').attr('class', 'osheen')
      .attr('cx', (d) => -radius(d) * 0.3).attr('cy', (d) => -radius(d) * 0.38).attr('rx', (d) => radius(d) * 0.55).attr('ry', (d) => radius(d) * 0.42);
    // how populated: a faint full track round the node, and the arc of its share on top
    const popd = onode.filter((d) => d.n > 0);
    popd.append('circle').attr('class', 'otrack').attr('r', (d) => radius(d) + 6);
    popd.append('path').attr('class', 'oarc')
      .attr('d', (d) => d3.arc()({ innerRadius: radius(d) + 4.5, outerRadius: radius(d) + 7.5, startAngle: 0, endAngle: 2 * Math.PI * popShare(d) }));
    onode.append('text').attr('class', (d) => `oname ${tierOf(d)}`)
      .attr('dy', (d) => -radius(d) - (d.n > 0 ? 14 : 7)).attr('text-anchor', 'middle').text((d) => M.label(d.id));
    // the entity count on a pill across the node, a little below centre, as if resting on the sphere
    const count = (k) => (k < 1000 ? String(k) : k < 10000 ? `${(k / 1000).toFixed(1).replace(/\.0$/, '')}k` : `${Math.round(k / 1000)}k`);
    const pillW = (d) => 12 + 8 * count(d.n).length;
    const pill = popd.append('g').attr('class', 'ocount').attr('transform', 'translate(0,3)');
    pill.append('rect').attr('height', 19).attr('y', -9.5).attr('rx', 9.5).attr('width', pillW).attr('x', (d) => -pillW(d) / 2);
    pill.append('text').attr('dy', '0.35em').attr('text-anchor', 'middle').text((d) => count(d.n));

    const path = (d) => {
      const sx = d.source.x, sy = d.source.y, tx = d.target.x, ty = d.target.y;
      const dx = tx - sx, dy = ty - sy, len = Math.hypot(dx, dy) || 1;
      const r = radius(d.target) + 3, ex = tx - (dx / len) * r, ey = ty - (dy / len) * r;
      if (!d.rank && d.kind !== 'obj') { d.mx = d.my = undefined; return `M${sx},${sy}L${ex},${ey}`; }
      const bend = (d.rank + 1) * 18 * (d.rank % 2 ? -1 : 1);
      const mx = (sx + ex) / 2 - (dy / len) * bend, my = (sy + ey) / 2 + (dx / len) * bend;
      d.mx = mx; d.my = my;
      return `M${sx},${sy}Q${mx},${my} ${ex},${ey}`;
    };
    function draw() {
      olink.attr('d', path);
      olabel.attr('x', (d) => d.mx ?? (d.source.x + d.target.x) / 2).attr('y', (d) => d.my ?? (d.source.y + d.target.y) / 2);
      onode.attr('transform', (d) => `translate(${d.x},${d.y})`);
    }
    // Fill the panel: zoom so the whole ontology fits with a margin.
    function fit(animate) {
      if (!onodes.length) return;
      const xs = onodes.map((d) => d.x), ys = onodes.map((d) => d.y), pad = HUB_R + 40;
      const x0 = Math.min(...xs) - pad, x1 = Math.max(...xs) + pad, y0 = Math.min(...ys) - pad, y1 = Math.max(...ys) + pad;
      const k = Math.max(0.2, Math.min(1.6, Math.min(w / (x1 - x0), hgt / (y1 - y0))));
      const t = d3.zoomIdentity.translate(w / 2 - k * (x0 + x1) / 2, hgt / 2 - k * (y0 + y1) / 2).scale(k);
      (animate && !reduced() ? svg.transition().duration(450) : svg).call(zoom.transform, t);
    }
    // The layout settles roughly round; a wide panel would leave its sides empty. Stretch the
    // classes sideways towards the panel's shape (at most twice), so the width is used.
    function stretch() {
      if (onodes.length < 2) return;
      const xs = onodes.map((d) => d.x), ys = onodes.map((d) => d.y);
      const cx = (Math.min(...xs) + Math.max(...xs)) / 2;
      const bw = Math.max(...xs) - Math.min(...xs) || 1, bh = Math.max(...ys) - Math.min(...ys) || 1;
      const s = Math.max(1, Math.min(2, ((w / hgt) * bh) / bw));
      for (const d of onodes) d.x = cx + (d.x - cx) * s;
    }
    // Lay the graph out once, then hold it still: the simulation ticks in short chunks without
    // drawing in between, and draws when it cools or its time budget runs out. Dragging moves one node.
    sim.stop();
    box.classList.add('laying-out');
    let spent = 0;
    const gen = S.gen;
    (function chunk() {
      if (gen !== S.gen) return;
      const start = performance.now(), until = start + 30;
      while (sim.alpha() > sim.alphaMin() && performance.now() < until) sim.tick();
      spent += performance.now() - start;
      if (sim.alpha() > sim.alphaMin() && spent < 4000) setTimeout(chunk);
      else { stretch(); draw(); fit(false); box.classList.remove('laying-out'); }
    })();

    function reset() {
      onode.classed('dim', false).classed('hit', false).classed('found', false);
      olink.classed('dim', false).classed('hot', false);
      olabel.classed('dim', false);
    }
    function focus(keep, hot) {
      onode.classed('dim', (d) => !keep.has(d.id));
      olink.classed('dim', (l) => !(keep.has(l.source.id) && keep.has(l.target.id)) && !hot(l)).classed('hot', hot);
      olabel.classed('dim', (l) => !hot(l) && !(keep.has(l.source.id) && keep.has(l.target.id)));
    }
    function flyTo(d) {
      if (!Number.isFinite(d.x)) return;
      const k = Math.max(1.1, d3.zoomTransform(svg.node()).k);
      const t = d3.zoomIdentity.translate(w / 2 - k * d.x, hgt / 2 - k * d.y).scale(k);
      (reduced() ? svg : svg.transition().duration(450)).call(zoom.transform, t);
    }
    function highlightClass(id) {
      const keep = new Set([id]);
      for (const l of olinks) { if (l.source.id === id) keep.add(l.target.id); if (l.target.id === id) keep.add(l.source.id); }
      focus(keep, (l) => l.source.id === id || l.target.id === id);
      onode.classed('hit', (d) => d.id === id);
    }
    function highlightProperty(name) {
      const ls = olinks.filter((l) => l.prop === name);
      const p = M.relations.find((r) => r.name === name) || M.attributes.find((a) => a.name === name) || {};
      const keep = new Set([...ls.flatMap((l) => [l.source.id, l.target.id]), ...(p.domain || []), ...(p.range || [])].filter((x) => oById.has(x)));
      focus(keep, (l) => l.prop === name);
      onode.classed('hit', (d) => keep.has(d.id));
    }
    // The find box: names (labels first) that start with the text, then that contain it.
    let found = null;
    function find(q) {
      q = str(q).trim().toLowerCase();
      const names = (d) => [M.label(d.id).toLowerCase(), d.id.toLowerCase()];
      found = !q ? null : onodes.find((d) => names(d).some((s) => s.startsWith(q))) || onodes.find((d) => names(d).some((s) => s.includes(q))) || null;
      onode.classed('found', (d) => d === found);
      if (found) flyTo(found);
      return found;
    }
    return { highlightClass, highlightProperty, reset, find, fit: () => fit(true), flyTo: (id) => oById.has(id) && flyTo(oById.get(id)),
      tiers: { core: CORE, hub: HUB, tierOf: (id) => tierOf(oById.get(id)) }, links: olinks };
  }

  // ---- statistics and lists -----------------------------------------------------------
  const chip = (M, c) => h('button', { class: 'chip', type: 'button', onclick: () => select(c), title: c },
    h('span', { class: 'dot', 'aria-hidden': 'true', style: null }), M.label(c));
  function dotted(el, colour) { el.firstChild.style.background = colour; return el; }
  const classChip = (M, c) => dotted(chip(M, c), M.colour(c));
  const sig = (M, xs) => (xs && xs.length ? xs.flatMap((x, i) => [i ? ' or ' : null, M.classes.has(x) ? classChip(M, x) : x]) : ['any']);

  function renderStats(M, V) {
    const o = M.o, sm = S.summary || {}, counts = sm.counts || {};
    const populated = [...M.classes.values()].filter((c) => c.count > 0).length;
    const seen = V.links.filter((l) => l.kind === 'seen').length;
    const usedProps = [...M.relations, ...M.attributes].filter((p) => p.count > 0).length;
    const tile = (value, labelText, title) => h('div', { class: 'tile', title }, h('span', { class: 'v', text: value }), h('span', { class: 'k', text: labelText }));
    clear($('#onto-stats'),
      h('p', { class: 'onto-title' }, h('span', { text: `${str(o.label || 'Ontology')} ` }), h('span', { class: 'pill', text: `version ${str(o.version)}` })),
      o.namespace ? h('p', { class: 'mono small muted', text: o.namespace }) : null,
      h('div', { class: 'tiles' },
        tile(n(M.classes.size), 'classes', `${n(populated)} of them have entities`),
        tile(n(M.relations.length), 'relations', 'Links between entities the ontology declares'),
        tile(n(M.attributes.length), 'attributes', 'Values recorded about an entity'),
        tile(n(counts.entities), 'entities', 'Things found in the documents'),
        tile(n(counts.facts), 'facts', 'Relations and attributes asserted, each with its source passages'),
        tile(n(counts.documents), 'documents', 'Documents extracted with this ontology')),
      h('p', { class: 'small muted' },
        `${plural(populated, 'class', 'classes')} of ${n(M.classes.size)} have entities; ${n(usedProps)} of ${n(M.relations.length + M.attributes.length)} properties are used. `,
        seen ? `The data links classes ${plural(seen, 'way')} the ontology does not declare (dashed).` : 'Every link the data makes between classes is declared.'));
  }

  function renderClasses(M, V) {
    const rows = [...M.classes.values()].sort((a, b) => (b.count || 0) - (a.count || 0) || M.label(a.name).localeCompare(M.label(b.name)));
    const max = Math.max(1, ...rows.map((r) => r.count || 0));
    clear($('#panel-classes'),
      h('p', { class: 'small muted', text: 'Entities of each class, subtypes included. A class with none is part of the ontology that no document has populated yet. Select one to find it in the graph.' }),
      h('ul', { class: 'class-list' }, rows.map((r) => {
        const bar = h('div', { class: 'bar' }, h('div'));
        bar.firstChild.style.width = `${(100 * (r.count || 0) / max).toFixed(1)}%`;
        bar.firstChild.style.background = r.count ? M.colour(r.name) : 'var(--border)';
        const tier = V.tiers.tierOf(r.name);
        const card = h('li', null, h('button', { class: 'list-card', type: 'button', onclick: () => select(r.name), 'data-class': r.name },
          h('span', { class: 'lc-head' }, h('span', { text: M.label(r.name) }), h('span', { class: 'mono', text: n(r.count) })),
          h('span', { class: 'lc-body' },
            M.label(r.name) !== r.name ? h('span', { class: 'mono', text: r.name }) : null,
            M.parentsOf(r.name).length ? ` kind of ${M.parentsOf(r.name).map(M.label).join(', ')}` : null,
            tier === 'core' ? h('span', { class: 'tag core', text: 'core' }) : null,
            (r.synonyms || []).length ? h('span', { class: 'aka', text: `also: ${r.synonyms.join(', ')}` }) : null),
          bar));
        card.firstChild.style.borderLeftColor = r.count ? M.colour(r.name) : 'var(--border)';
        return card;
      })));
  }

  function renderProperties(M) {
    const props = [...M.relations.map((p) => ({ ...p, kind: 'relation' })), ...M.attributes.map((p) => ({ ...p, kind: 'attribute' }))]
      .sort((a, b) => (b.count || 0) - (a.count || 0) || (a.label || a.name).localeCompare(b.label || b.name));
    clear($('#panel-properties'),
      h('p', { class: 'small muted', text: 'How often each property was asserted. Relations link two entities; attributes record a value. Select one to see where it runs in the graph.' }),
      h('table', { class: 'kv' },
        h('thead', null, h('tr', null, ['Property', 'Facts', 'From → to'].map((t) => h('th', { scope: 'col', text: t })))),
        h('tbody', null, props.map((p) => h('tr', null,
          h('td', null, h('button', { class: 'linkish', type: 'button', onclick: () => selectProperty(p.name) }, p.label || p.name),
            h('span', { class: 'mono small muted', text: ` ${p.kind}` })),
          h('td', { class: 'num-cell' }, p.count ? n(p.count) : h('span', { class: 'muted', text: 'unused' })),
          h('td', { class: 'small' }, (p.domain || []).map(M.label).join(' or ') || 'any', ' → ',
            p.kind === 'relation' ? ((p.range || []).map(M.label).join(' or ') || 'any') : str(p.datatype)))))));
  }

  // ---- selection -----------------------------------------------------------------------
  function activate(tab) {
    for (const b of document.querySelectorAll('[role=tab]')) {
      const on = b.dataset.tab === tab;
      b.setAttribute('aria-selected', String(on)); b.tabIndex = on ? 0 : -1;
      $(`#panel-${b.dataset.tab}`).hidden = !on;
    }
  }
  function detail(...kids) { clear($('#panel-selected'), h('div', { class: 'node-detail' }, kids)); activate('selected'); }
  const section = (title, ...kids) => (kids.flat().filter(Boolean).length ? [h('h4', { text: title }), ...kids] : null);

  function select(name) {
    const M = S.model, V = S.view;
    const c = M && M.classes.get(name);
    if (!c) return;
    V.highlightClass(name); V.flyTo(name);
    route({ class: name });
    const subs = [...M.classes.values()].filter((x) => M.parentsOf(x.name).includes(name)).map((x) => x.name);
    const out = M.relations.filter((p) => (p.domain || []).includes(name));
    const inn = M.relations.filter((p) => (p.range || []).includes(name));
    const attrs = M.attributes.filter((p) => (p.domain || []).includes(name));
    const seenOut = M.observed.filter((e) => e.domain === name && !M.declares(e.p, e.domain, e.range));
    const seenIn = M.observed.filter((e) => e.range === name && e.domain !== name && !M.declares(e.p, e.domain, e.range));
    const propRow = (p, other) => h('tr', null,
      h('td', null, h('button', { class: 'linkish', type: 'button', onclick: () => selectProperty(p.name) }, p.label || p.name)),
      h('td', null, other, h('span', { class: 'muted', text: ` · ${plural(p.count || 0, 'fact')}` })));
    const tier = S.view.tiers.tierOf(name);
    const head = h('span', { class: 'chip static' }, h('span', { class: 'dot', 'aria-hidden': 'true' }), tier === 'core' ? 'core class' : 'class');
    head.firstChild.style.background = M.colour(name);
    detail(head,
      h('h3', { text: M.label(name) }),
      h('p', { class: 'mono small muted', text: c.iri || name }),
      M.parentsOf(name).length ? h('p', null, 'A kind of ', sig(M, M.parentsOf(name))) : null,
      c.definition ? h('p', { text: c.definition }) : null,
      (c.synonyms || []).length ? h('p', { class: 'muted', text: `Also called: ${c.synonyms.join(', ')}` }) : null,
      h('h4', { text: 'In the graph' }),
      h('p', null, plural(c.count || 0, 'entity', 'entities'), c.count ? ' (subtypes included). ' : '. ',
        c.count ? h('a', { href: `./?ask=${encodeURIComponent(`What ${M.label(name)} entities are there?`)}` }, 'Ask about them in the chat') : null),
      section('Subclasses', subs.length ? h('p', null, sig(M, subs)) : null),
      section('Relations from it', out.length ? h('table', { class: 'kv' }, out.map((p) => propRow(p, ['to ', sig(M, p.range)]))) : null),
      section('Relations to it', inn.length ? h('table', { class: 'kv' }, inn.map((p) => propRow(p, ['from ', sig(M, p.domain)]))) : null),
      section('Attributes', attrs.length ? h('table', { class: 'kv' }, attrs.map((p) => propRow(p, h('span', { class: 'mono', text: str(p.datatype) })))) : null),
      section('Seen in the data, not declared', (seenOut.length || seenIn.length) ? h('table', { class: 'kv' },
        seenOut.map((e) => h('tr', null, h('td', { text: e.p }), h('td', null, 'to ', classChip(M, e.range), h('span', { class: 'muted', text: ` · ${plural(e.count, 'fact')}` })))),
        seenIn.map((e) => h('tr', null, h('td', { text: e.p }), h('td', null, 'from ', classChip(M, e.domain), h('span', { class: 'muted', text: ` · ${plural(e.count, 'fact')}` }))))) : null));
    announce(`${M.label(name)} selected: ${plural(c.count || 0, 'entity', 'entities')}.`);
  }

  function selectProperty(name) {
    const M = S.model, V = S.view;
    const rel = M.relations.find((p) => p.name === name), att = M.attributes.find((p) => p.name === name);
    const p = rel || att;
    if (!p) return;
    V.highlightProperty(name);
    route({ prop: name });
    const seen = M.observed.filter((e) => e.p === name && !M.declares(e.p, e.domain, e.range));
    detail(h('span', { class: 'chip static', text: rel ? 'relation' : 'attribute' }),
      h('h3', { text: p.label || p.name }),
      p.label && p.label !== p.name ? h('p', { class: 'mono small muted', text: p.name }) : null,
      p.definition ? h('p', { text: p.definition }) : null,
      h('h4', { text: rel ? 'From → to' : 'Of → datatype' }),
      h('p', null, sig(M, p.domain), ' → ', rel ? sig(M, p.range) : h('span', { class: 'mono', text: str(p.datatype) })),
      h('h4', { text: 'In the graph' }),
      h('p', { text: `${plural(p.count || 0, 'fact')} asserted.` }),
      section('Also seen between', seen.length ? h('table', { class: 'kv' }, seen.map((e) => h('tr', null,
        h('td', null, classChip(M, e.domain), ' → ', classChip(M, e.range)), h('td', { class: 'num-cell', text: n(e.count) })))) : null));
    announce(`${p.label || p.name} selected: ${plural(p.count || 0, 'fact')}.`);
  }

  // The address keeps the collection and the selection, so a link opens the same view.
  function route(sel) {
    const q = new URLSearchParams();
    if (S.id && S.collections.length > 1) q.set('c', S.id);
    if (sel.class) q.set('class', sel.class);
    if (sel.prop) q.set('prop', sel.prop);
    const qs = q.toString();
    window.history.replaceState(null, '', location.pathname + (qs ? '?' + qs : ''));
  }

  // ---- loading a collection ------------------------------------------------------------
  async function load() {
    const gen = ++S.gen;
    $('#onto').hidden = true;
    notice(h('p', { class: 'muted', text: 'Loading the ontology.' }));
    let onto, summary;
    try {
      [onto, summary] = await Promise.all([api('/ontology', { c: S.id }), api('/summary', { c: S.id }).catch(() => null)]);
    } catch (e) {
      if (gen !== S.gen || e.status === 401) return;
      if (e.status === 409) {
        const st = (e.body && e.body.status) || {};
        return notice(h('h2', { text: 'No ontology yet' }),
          h('p', { text: `The knowledge graph for this collection is not built yet (pipeline stage: ${str(st.stage || 'never run').replace(/_/g, ' ')}). Once an ontology version is published and documents are extracted, it shows here.` }));
      }
      return notice(h('h2', { text: 'The ontology could not be loaded' }), h('p', { text: e.message }),
        h('button', { class: 'btn', type: 'button', onclick: () => load() }, 'Try again'));
    }
    if (gen !== S.gen) return;
    S.onto = onto; S.summary = summary; S.model = model(onto);
    notice();
    $('#onto').hidden = false;
    if (!S.model.classes.size) {
      $('#onto').hidden = true;
      return notice(h('h2', { text: 'The ontology is empty' }), h('p', { text: 'The active ontology version declares no classes.' }));
    }
    S.view = buildView(S.model);
    renderStats(S.model, S.view);
    renderClasses(S.model, S.view);
    renderProperties(S.model);
    activate('classes');
    const p = new URLSearchParams(location.search);
    if (p.get('class')) setTimeout(() => select(p.get('class')), 0);
    else if (p.get('prop')) setTimeout(() => selectProperty(p.get('prop')), 0);
  }

  // ---- boot ------------------------------------------------------------------------------
  function current() { return S.collections.find((c) => c.id === S.id) || {}; }
  function showCollection() {
    const c = current(), multi = S.collections.length > 1;
    $('#coll-wrap').hidden = !multi;
    $('#coll-name').hidden = multi;
    $('#coll-name').textContent = str(c.name || c.id);
    $('#coll-select').value = S.id;
    document.title = `Ontology · ${str(c.name || c.id)} · ${window.KS.brandName()}`;
  }
  function wire() {
    $('#coll-select').addEventListener('change', (e) => {
      S.id = e.target.value; lstore.set(COLL_KEY, S.id); route({}); showCollection(); load();
    });
    const findEl = $('#onto-find');
    findEl.addEventListener('input', () => { if (S.view) S.view.find(findEl.value); });
    findEl.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && S.view) { e.preventDefault(); const d = S.view.find(findEl.value); if (d) select(d.id); }
      if (e.key === 'Escape') { findEl.value = ''; if (S.view) { S.view.find(''); S.view.reset(); } }
    });
    $('#onto-fit').addEventListener('click', () => S.view && S.view.fit());
    const tabs = [...document.querySelectorAll('[role=tab]')];
    for (const b of tabs) {
      b.addEventListener('click', () => activate(b.dataset.tab));
      b.addEventListener('keydown', (e) => {
        const i = tabs.indexOf(b), j = e.key === 'ArrowRight' ? (i + 1) % tabs.length : e.key === 'ArrowLeft' ? (i + tabs.length - 1) % tabs.length : -1;
        if (j >= 0) { e.preventDefault(); activate(tabs[j].dataset.tab); tabs[j].focus(); }
      });
    }
    let t = null, size = innerWidth; // a new width lays the graph out again (a height change alone does not)
    window.addEventListener('resize', () => {
      clearTimeout(t);
      t = setTimeout(() => {
        if (innerWidth === size || !S.model || $('#onto').hidden) return;
        size = innerWidth; S.gen++; S.view = buildView(S.model); route({});
      }, 300);
    });
  }
  function signedOut(started) {
    $('#signin').hidden = started.cfg.mode === 'site';
    notice(window.KS.signedOutNotice(started, 'Sign in to see the ontology'));
  }
  async function boot() {
    const started = await window.KS.start();
    const { cfg, error, signedIn, claims } = started;
    $('#brand-name').textContent = window.KS.brandName();
    if (typeof d3 === 'undefined') return notice(h('p', { class: 'error', text: 'The graph library (vendor/d3.min.js) did not load.' }));
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
    if (!S.collections.length) return notice(h('h2', { text: 'No collections yet' }), h('p', { text: 'There are no collections yet.' }));
    $('#private-pill').hidden = !S.private;
    clear($('#coll-select'), S.collections.map((c) => h('option', { value: c.id }, str(c.name || c.id))));
    const wanted = new URLSearchParams(location.search).get('c') || lstore.get(COLL_KEY);
    S.id = S.collections.some((c) => c.id === wanted) ? wanted : S.collections[0].id;
    lstore.set(COLL_KEY, S.id);
    showCollection();
    await load();
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
