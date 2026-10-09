# Chat page

A minimal page for asking questions of a collection. Every answer is built from the documents
in that collection, and every statement links to the passage it came from. A second page,
`ontology.html`, shows the collection's active ontology as a graph, with its statistics.

Plain HTML, CSS and JavaScript: no framework, no build step, no external scripts or fonts. The
ontology page's one library, D3, is served from this folder (`vendor/`).

## Files

- `index.html`: the page. Its Content-Security-Policy allows only same-origin scripts and styles
  (no inline scripts or styles) and HTTPS connections, which covers the API and Cognito's token
  endpoint.
- `common.js`: what both pages share: sign-in, the API client and the DOM helpers. Cognito
  returns to one address (the chat page), so a sign-in started on the ontology page remembers it
  and goes back there.
- `app.js`: the collection picker, asking and polling, and rendering answers and sources. No
  server text reaches `innerHTML`; the DOM is built from nodes and `textContent`. A `?ask=`
  parameter fills the question box without sending it. The workbench beside the chat shows the
  selected question's steps as they happen, the ontology terms its answer used and this session's
  totals; "What would it take?" asks the analyst and renders its report
  ([docs/workbench.md](../docs/workbench.md)). Below 1100 pixels the workbench is a drawer.
- `ontology.html`, `ontology.js`, `ontology.css`: the ontology page. Classes are spheres
  coloured by their root class, with a pill counting their entities and an arc showing how
  populated each is against the largest; subclass links,
  declared relations (domain to range) and relations the data uses between classes the ontology
  does not declare them for (dashed, weighted by use). The most connected classes are the core:
  gold and central. Beside it are the counts, every class with its entities, every property with
  its facts, and the selected class or property in detail. `?class=` or `?prop=` opens with one
  selected. Data: `GET /api/ontology` and `GET /api/summary`. The question overlay
  (`?overlay=all|month|session`) rings each class by how many questions used it, from
  `GET /api/usage` or this session's totals; curators also get a Requests tab.
- `vendor/d3.min.js`: D3 7.9.0, unmodified (see `vendor/README.md`).
- `styles.css`: colour tokens on `:root`, light and dark themes from `prefers-color-scheme`.
- `config.json`: not in this folder. Terraform generates it when it uploads the folder.

## Configuration

The page reads `./config.json`, then `./config.local.json` if the first is missing. Terraform
uploads this folder to the site bucket and writes `config.json` in the same shape as the
portal's:

```json
{
  "mode": "hosted",
  "brand": { "name": "Knowledge Store" },
  "apiBase": "/api",
  "redirectUri": "https://<distribution>/",
  "cognito": { "domain": "https://<prefix>.auth.<region>.amazoncognito.com", "clientId": "<app client id>", "scope": "openid email" }
}
```

`cognito.scope` is optional and defaults to `openid email`. In hosted mode the page signs in with
Cognito's hosted UI (authorization code with PKCE) and sends the Cognito access token as
`Authorization: Bearer <token>` on every `/api` call, refreshing it shortly before it expires.

With `site_sign_in` set, Terraform writes site mode instead:

```json
{ "mode": "site", "brand": { "name": "Knowledge Store" }, "apiBase": "/api",
  "site": { "origin": "https://www.example.org", "lab": "knowledge" } }
```

In site mode a host website signs people in and frames the pages. Over the embed protocol
(postMessage `pn:hello`, `pn:init`, `pn:ready`, then `pn:grant`) it hands the page a short grant
for the lab and renews it before it expires. The page listens to the configured origin only, sends
the grant as `X-Site-Grant` on every `/api` call, and keeps it in sessionStorage so the other page
in the frame can use it at once. Opened on its own, the page links to the website instead.

For local development, add a `config.local.json` such as
`{"mode": "local", "apiBase": "http://localhost:8765/api"}`: local mode skips sign-in.

## API

All routes are on the same origin under `/api`, and every route but `/collections` takes
`?c=<collection id>`.

- `GET /api/collections`: the collections to pick from, whether the person has private access, and each collection's `example_questions` (`{text, level}`, level `low`, `medium` or `high`). The chat shows them to the left of the conversation. Choosing one fills the question box and does not send it. A question in the profile may start with `[low]`, `[medium]` or `[high]`. Without any, the page shows three general questions.
- `POST /api/chat?c=<id>` with `{"question", "history", "mode", "about"}`: starts an answer and
  returns its `id`. `history` holds the last 6 completed turns as `{"q", "a"}`. `mode` is `ask` or
  `gaps` (what would it take). 429 when the daily quota is spent.
- `GET /api/chat?c=<id>&id=<id>`: the answer's status (`pending`, `running` with the `steps` so
  far, `done` or `failed`), polled every 1.5 seconds for up to 10 minutes. A finished answer
  carries `claims`, `sources`, `abstained`, `blocked`, `gaps`, `steps`, `ontology_hits` and `cost`
  (list price, split by token kind and by model call); a `gaps` run carries `report` and the same `cost`.
- `GET /api/usage?c=<id>&window=all|month`: how many questions used each class and property.
- `GET`, `POST /api/requests?c=<id>`: ontology requests kept from gap reports (curators only).
- `GET /api/document?c=<id>&doc=<doc id>`: a link to open the source document in a new tab.
- `GET /api/ontology?c=<id>`: the active ontology's classes, relations and attributes with their
  counts, and `observed`: how often each relation links one class to another in the data.
- `GET /api/summary?c=<id>`: the collection's counts of documents, entities and facts.
