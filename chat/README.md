# Chat page

A minimal page for asking questions of a collection. Every answer is built from the documents
in that collection, and every statement links to the passage it came from.

Plain HTML, CSS and JavaScript: no framework, no build step, no external scripts or fonts.

## Files

- `index.html`: the page. Its Content-Security-Policy allows only same-origin scripts and styles
  (no inline scripts or styles) and HTTPS connections, which covers the API and Cognito's token
  endpoint.
- `app.js`: sign-in, the collection picker, asking and polling, and rendering answers and
  sources. No server text reaches `innerHTML`; the DOM is built from nodes and `textContent`.
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

For local development, add a `config.local.json` such as
`{"mode": "local", "apiBase": "http://localhost:8765/api"}`: local mode skips sign-in.

## API

All routes are on the same origin under `/api`, and every route but `/collections` takes
`?c=<collection id>`.

- `GET /api/collections`: the collections to pick from, and whether the person has private access.
- `POST /api/chat?c=<id>` with `{"question", "history"}`: starts an answer and returns its `id`.
  `history` holds the last 6 completed turns as `{"q", "a"}`. 429 when the daily quota is spent.
- `GET /api/chat?c=<id>&id=<id>`: the answer's status, polled every 2 seconds for up to 5 minutes.
  A finished answer carries `claims`, `sources`, `abstained`, `blocked` and `gaps`.
- `GET /api/document?c=<id>&doc=<doc id>`: a link to open the source document in a new tab.
