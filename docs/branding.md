# Substituting the branding

Knowledge Store is a kit you deploy under your own name. This guide lists everything a person
sees that carries a name, a mark or a colour, where each comes from, and how to replace it. One
thing is an input to the module. The rest is a small set of files in a fork, and two things are
settings of the AWS account rather than of the kit.

## What people see, and where it comes from

| Where it appears | Comes from | Change it by |
|---|---|---|
| The name in the header of both pages, the browser tab, and the signed-out notice | `portal_title`, which Terraform writes into `config.json` as `brand.name` | the input alone |
| The name before the script runs: the static `<title>` and the header text in the HTML | [`chat/index.html`](../chat/index.html), [`chat/ontology.html`](../chat/ontology.html) | editing the files in a fork |
| The tab icon | an inline SVG data URI in the `<link rel="icon">` of both pages | editing the files |
| A logo beside the name | nothing yet: the header has only the name | adding an image file and an `<img>` to both pages |
| Colours, in light and dark mode | the tokens on `:root` in [`chat/styles.css`](../chat/styles.css), and the `--st-*` tokens of the ontology stage in [`chat/ontology.css`](../chat/ontology.css) | editing the tokens |
| The typeface | the `--font` token: the system font stack | editing the token, and bundling a font file if you want one |
| The page's copy: the question box's placeholder, the hint under it, the panel headings, the sign-in buttons | [`chat/index.html`](../chat/index.html) and the strings in [`chat/app.js`](../chat/app.js) and [`chat/ontology.js`](../chat/ontology.js) | editing the files |
| The agent's refusal, and the guardrail's two messages | `ABSTAIN` in [`agent/grounding.py`](../src/knowledge_store/agent/grounding.py); `blocked_input_messaging` and `blocked_outputs_messaging` in [`modules/agent`](../infra/modules/agent/main.tf) | editing them |
| The portal's address | CloudFront's `*.cloudfront.net` domain by default | `portal_domain`: your own name and certificate |
| The sign-in page and its address | Cognito's hosted sign-in at `<name>-<account>.auth.<region>.amazoncognito.com`, unstyled | a Cognito customisation in the account, or a fork of the identity module (below) |
| The invitation and recovery emails | Cognito's default sender and wording | a Cognito email configuration (below) |
| The names of the AWS resources | `name`, which prefixes every resource | the input, before the first apply |
| The ontology's namespace | `profile.ontology_base`, by default `https://example.org/<name>/<collection>/ontology#` | the input, before the first ontology is published |
| Each collection's name, description and sample questions | the collection's `profile` | the input |

With sign-in through a host website (`site_sign_in`) the website frames the portal and carries
its own chrome. The pages still show `portal_title` in the header, and the signed-out notice
names it when a page is opened outside the frame.

## 1. The name

Set `portal_title` in your root's `terraform.tfvars` (the reference root) or in the module call
(the deployment template):

```hcl
portal_title = "Policy Assistant"
```

Terraform rewrites `config.json` in the site bucket on apply, and the page reads it on load:
the header, the document title, and the signed-out notice take the name from it, so most
deployments need nothing else. The CloudFormation launch stack has no parameter for it; a
deployment that needs the name set uses Terraform directly.

## 2. The address

Serve the portal on a domain of your own with `portal_domain`: the name and an ACM certificate
for it in `us-east-1`, which CloudFront requires whatever the stack's region. After apply, point
a CNAME or an alias at the `portal_cloudfront_domain` output. The steps are in the installation
guide ([a certificate](deploy/aws/README.md#33-optional-a-certificate-for-the-portals-domain),
[DNS](deploy/aws/README.md#9-optional-point-your-domain-at-the-portal)).

The sign-in page keeps Cognito's address. A custom domain for it is a Cognito feature
(`aws_cognito_user_pool_domain` with a certificate) that the identity module does not expose;
add it in a fork if the address matters.

## 3. Everything else: a fork of the page

Terraform uploads the [`chat/`](../chat/) folder of the module's own source to the site bucket
(`portal_dir` in [`modules/knowledge-store/main.tf`](../infra/modules/knowledge-store/main.tf)),
so a change to the files is a change to the repository you deploy from. Fork the repository, make
the changes below on a branch, and point your deployment at that fork. In the deployment
template that is the module's `source`:

```hcl
source = "git::https://github.com/<you>/knowledge-store.git//infra/modules/knowledge-store?ref=<commit>"
```

A clone of the fork works the same way with the reference root, `infra/stack`.

The files upload with `cache-control: no-cache`, so the next apply shows the change without a
CloudFront invalidation. Markdown files and anything named `config.*` are not uploaded.

### The mark

Both pages have a `<link rel="icon">` holding a small SVG as a data URI, and a header that
starts with the name:

```html
<p class="brand" id="brand-name">Knowledge Store</p>
```

Put your icon in the same place as a data URI, or as a file: `chat/favicon.svg` (or `.png`,
`.ico`) uploads with the right content type, and the link becomes `href="favicon.svg"`. For a
logo beside the name, add `chat/logo.svg` and an image before the name in both headers:

```html
<nav class="nav" aria-label="Pages">
  <img class="logo" src="logo.svg" alt="" width="28" height="28">
  <p class="brand" id="brand-name">Knowledge Store</p>
```

with a rule for it in `styles.css` (the header is a flex row, so a height is enough):

```css
.logo { height: 28px; width: auto; }
```

Change the static name in the `<title>` and the `brand` paragraph of both pages too, so the
page is right in the instant before the script replaces them with `portal_title`.

Two limits come from the page's security policy and should stay. Images may come only from the
page's own origin or a data URI, not from another host, so the logo is a file in the folder. And
there is no inline style or script, so a colour or a size goes in `styles.css`, never in a
`style=` attribute.

### Colours

Every colour is a token on `:root` in `styles.css`, declared once for light mode and again for
dark mode under `prefers-color-scheme: dark`. The ones a brand usually sets:

| Token | Used for |
|---|---|
| `--action`, `--action-hover`, `--action-text` | the Send button and the current page's underline |
| `--link` | links and citation numbers |
| `--focus` | the keyboard focus ring |
| `--bg`, `--surface`, `--surface-2`, `--border` | the page, panels and their borders |
| `--text`, `--muted` | text and secondary text |
| `--user` | the person's own turns in the conversation |
| `--mark`, `--mark-text` | the quoted words highlighted in a passage |
| `--calm`, `--refuse`, `--danger` | an answer that abstains, a refused question, an error |
| `--q-graph`, `--q-vector`, `--q-keyword`, `--q-read`, `--q-ontology` | the workbench's step types |

Set both modes, or set `color-scheme: light` alone and remove the dark block. Keep the contrast
between text and its surface in both: a light brand colour is darkened for `--action` and
`--link` rather than used as it is.

The ontology page's graph stage is always dark and has its own tokens at the top of
`ontology.css` (`--st-bg`, `--st-text`, `--st-muted`, `--st-border`, `--st-arc`). The classes'
sphere colours are chosen by the script from their root class; leave those.

### The typeface

`--font` is a system font stack, so the page loads no font file. To use a brand typeface, put
the file in `chat/` and declare it in `styles.css`:

```css
@font-face { font-family: "Brand"; src: url("brand.woff2") format("woff2"); font-display: swap; }
:root { --font: "Brand", system-ui, sans-serif; }
```

The policy allows fonts from the page's own origin, so this needs no change to it. Terraform
sets content types by extension from a short list (html, js, css, json, svg, png, ico); a font is
uploaded as `application/octet-stream`, which browsers accept for `@font-face`, and the list in
[`modules/portal/main.tf`](../infra/modules/portal/main.tf) (`local.mime`) takes a `woff2`
entry if you would rather it were right.

### The copy

The sentences a person reads are in the HTML (the placeholder, the hint under the question box,
the workbench's empty states, the button labels) and in the two scripts, as plain strings passed
to `h(...)`. The agent's one sentence when it cannot answer is `ABSTAIN` in
[`agent/grounding.py`](../src/knowledge_store/agent/grounding.py), and the guardrail's two
messages are in the agent module. The pages are English; the strings are not collected for
translation.

## 4. Sign-in and email

The identity module creates the user pool and the hosted sign-in domain and leaves their look to
Cognito. Two things in the account change that:

- The sign-in page. The pool uses Cognito's classic hosted UI, whose logo and CSS are set with
  `aws_cognito_user_pool_ui_customization` (or in the console, under App integration). Add the
  resource to a fork of [`modules/identity`](../infra/modules/identity/main.tf), with the pool
  and the web client it creates. A change made in the console is kept, since Terraform manages
  no customisation resource to overwrite it.
- Emails. Cognito sends the temporary password and recovery codes from its own address with its
  default wording. A sender of your own needs an SES identity in the account and an
  `email_configuration` block on the pool, and the wording an `invite_message_template` under
  `admin_create_user_config` and a `verification_message_template`. Both are pool settings, so
  they belong in the same fork of the identity module.

With `site_sign_in`, people sign in on your website and none of this is shown.

## 5. Names in the data

Two names end up inside the data, so set them before the first apply and the first published
ontology:

- `name` prefixes every resource (the buckets, the pool, the Lambdas, the Neptune cluster), and
  changing it later recreates them. It is 3 to 25 characters: lower-case letters, digits and
  hyphens, starting with a letter.
- Each collection's `profile.ontology_base` is the namespace of its ontology's terms and so of
  every fact in gold. The default is under `example.org`, which is fine for a trial and not for a
  record you will keep. Set it to a domain of yours, with the trailing `#` or `/`, before the
  collection's first version is published. A change afterwards changes every term's IRI, so it
  is a new ontology and a full re-extraction.

The core vocabulary (`ks:`) is shared by every deployment and is not renamed.

## 6. Check it

Run the page locally before you apply, with a `config.local.json` in `chat/` as the
[chat README](../chat/README.md#configuration) describes, against a local API or none. Look at
both pages in light and dark mode, and at the signed-out notice. Then `terraform validate` in your
root, `terraform plan`, and apply. The portal module's tests do not cover the page's files, so
the check is by eye.

## What to keep

The project is licensed under the Apache License 2.0. A fork that carries your name keeps the
[LICENSE](../LICENSE) and [NOTICE](../NOTICE) files, and the notices in the source files, and
adds its own notice rather than replacing them (section 4 of the licence). Third-party components
and their licences are in [THIRD_PARTY_NOTICES.md](../THIRD_PARTY_NOTICES.md); the one the page
ships is D3, in `chat/vendor/`.
