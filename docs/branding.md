# Substituting the branding

Knowledge Store is a kit you deploy under your own name. This guide lists everything a person
sees that carries a name, a mark or a colour, where each comes from, and how to replace it. The
name, the address, the mark, the colours and the typeface are inputs to the module, so a
deployment carries its brand in its own configuration and never copies the page. The sentences
on the page are the one thing that still takes a fork, and the sign-in page and the emails are
settings of the AWS account rather than of the kit.

## What people see, and where it comes from

| Where it appears | Comes from | Change it by |
|---|---|---|
| The name in the header of both pages, the browser tab, and the signed-out notice | `portal_title`, which Terraform writes into `config.json` as `brand.name` | the input |
| The tab icon | `branding.icon`, served as `brand/icon.<ext>` and named in `config.json` | the input |
| A logo before the name in the header | `branding.logo`, served as `brand/logo.<ext>` | the input |
| Colours, in light and dark mode | the tokens on `:root` in [`chat/styles.css`](../chat/styles.css), overridden by `branding.colors` and `branding.colors_dark`, which Terraform writes to `brand.css` | the input |
| The typeface | the `--font` token: the system font stack | `branding.stylesheet` with an `@font-face`, and the font file in `branding.files` |
| Anything else in CSS, such as the ontology stage's `--st-*` tokens in [`chat/ontology.css`](../chat/ontology.css) | the page's stylesheets | `branding.stylesheet`, served after them |
| The portal's address | CloudFront's `*.cloudfront.net` domain by default | `portal_domain`: your own name and certificate |
| The name before the script runs: the static `<title>` and header text, shown for an instant | [`chat/index.html`](../chat/index.html), [`chat/ontology.html`](../chat/ontology.html) | a fork, if the instant matters |
| The page's copy: the question box's placeholder, the hint under it, the panel headings, the buttons | the HTML, and the strings in [`chat/app.js`](../chat/app.js) and [`chat/ontology.js`](../chat/ontology.js) | a fork |
| The agent's refusal, and the guardrail's two messages | `ABSTAIN` in [`agent/grounding.py`](../src/knowledge_store/agent/grounding.py); `blocked_input_messaging` and `blocked_outputs_messaging` in [`modules/agent`](../infra/modules/agent/main.tf) | a fork |
| The sign-in page and its address | Cognito's hosted sign-in at `<name>-<account>.auth.<region>.amazoncognito.com`, unstyled | a Cognito customisation in the account (below) |
| The invitation and recovery emails | Cognito's default sender and wording | a Cognito email configuration (below) |
| The names of the AWS resources | `name`, which prefixes every resource | the input, before the first apply |
| The ontology's namespace | `profile.ontology_base`, by default `https://example.org/<name>/<collection>/ontology#` | the input, before the first ontology is published |
| Each collection's name, description and sample questions | the collection's `profile` | the input |

With sign-in through a host website (`site_sign_in`) the website frames the portal and carries
its own chrome. The pages still show the name and the logo in their header, and the signed-out
notice names the portal when a page is opened outside the frame.

## 1. The name

Set `portal_title` in your root's `terraform.tfvars` (the reference root) or in the module call
(the deployment template):

```hcl
portal_title = "Policy Assistant"
```

Terraform rewrites `config.json` in the site bucket on apply, and the page reads it on load:
the header, the document title and the signed-out notice take the name from it. The
CloudFormation launch stack has no parameter for it, nor for the rest of the brand; a deployment
that sets either uses Terraform directly.

## 2. The address

Serve the portal on a domain of your own with `portal_domain`: the name and an ACM certificate
for it in `us-east-1`, which CloudFront requires whatever the stack's region. After apply, point
a CNAME or an alias at the `portal_cloudfront_domain` output. The steps are in the installation
guide ([a certificate](deploy/aws/README.md#33-optional-a-certificate-for-the-portals-domain),
[DNS](deploy/aws/README.md#9-optional-point-your-domain-at-the-portal)).

The sign-in page keeps Cognito's address. A custom domain for it is a Cognito feature
(`aws_cognito_user_pool_domain` with a certificate) that the identity module does not expose.

## 3. The mark, the colours and the typeface

The `branding` input names files and tokens of your own, and Terraform serves them beside the
page. Paths are relative to where you run Terraform, like `ontology_dir`:

```hcl
branding = {
  logo        = "brand/logo.svg"            # before the name in the header
  icon        = "brand/icon.png"            # the browser tab
  colors      = { action = "#0a5a3c", link = "#0a5a3c", focus = "#0a5a3c" }
  colors_dark = { action = "#7fd1b0", link = "#7fd1b0", focus = "#7fd1b0" }
  stylesheet  = "brand/brand.css"           # anything the tokens do not cover
  files       = { "brand/brand.woff2" = "brand/brand.woff2" }
}
```

Every field is optional. What each becomes:

| Field | Served as | How the page uses it |
|---|---|---|
| `logo` | `brand/logo.<ext>` (svg, png, jpg, jpeg, webp or gif) | an image before the name in both headers, 28 pixels high |
| `icon` | `brand/icon.<ext>` (svg, png or ico) | the `<link rel="icon">` of both pages |
| `colors`, `colors_dark` | `:root` rules in `brand.css`, the dark ones under `prefers-color-scheme: dark` | the page's tokens are overridden; the rest keep their defaults |
| `stylesheet` | appended to `brand.css`, after the tokens | loaded after the page's own stylesheets, so its rules win |
| `files` | the path each key names, under `brand/` | whatever the stylesheet references: a font, a background |

`brand.css` exists in every deployment and is linked by both pages; with no branding it holds
no rule. The files are served with `cache-control: no-cache`, like the page's own, so the next
apply shows the change without a CloudFront invalidation. The page reads the logo's and the
icon's paths from `config.json` and uses them only when they are under `brand/`, so the
configuration cannot point it at another origin.

Two limits come from the page's security policy and stay. Images, fonts and stylesheets may come
only from the page's own origin, which is why the input takes files rather than URLs. And there
is no inline style, so a colour or a size goes in the tokens or the stylesheet, never in markup.

### Colours

Every colour is a token on `:root` in [`chat/styles.css`](../chat/styles.css), declared once for
light mode and again for dark. Name them without the leading `--`. The ones a brand usually sets:

| Token | Used for |
|---|---|
| `action`, `action-hover`, `action-text` | the Send button and the current page's underline |
| `link` | links and citation numbers |
| `focus` | the keyboard focus ring |
| `bg`, `surface`, `surface-2`, `border` | the page, panels and their borders |
| `text`, `muted` | text and secondary text |
| `user` | the person's own turns in the conversation |
| `mark`, `mark-text` | the quoted words highlighted in a passage |
| `calm`, `refuse`, `danger` | an answer that abstains, a refused question, an error |
| `q-graph`, `q-vector`, `q-keyword`, `q-read`, `q-ontology` | the workbench's step types |

A token in `colors` alone applies to both modes, since the dark block only sets the tokens it
names. Keep the contrast between text and its surface in both: a light brand colour is darkened
for `action` and `link` rather than used as it is. A value is one CSS value; a `;` or a brace in
it is refused, so a value cannot write rules of its own.

The ontology page's graph stage is always dark and has its own tokens at the top of
[`chat/ontology.css`](../chat/ontology.css) (`--st-bg`, `--st-text`, `--st-muted`,
`--st-border`, `--st-arc`); set those in the stylesheet. The classes' sphere colours are chosen by
the script from their root class; leave those.

### The typeface

`--font` is a system font stack, so the page loads no font file. For a typeface of your own, put
the file in `files` and declare it in the stylesheet, with the path the file is served at:

```css
@font-face { font-family: "Brand"; src: url("brand/brand.woff2") format("woff2"); font-display: swap; }
:root { --font: "Brand", system-ui, sans-serif; }
```

Fonts are served with their own content type (woff, woff2, ttf and otf), as are the image
formats above; anything else in `files` is served as a plain download.

## 4. The copy: a fork

The sentences a person reads are in the HTML (the placeholder, the hint under the question box,
the workbench's empty states, the button labels) and in the two scripts, as plain strings passed
to `h(...)`. The agent's one sentence when it cannot answer is `ABSTAIN` in
[`agent/grounding.py`](../src/knowledge_store/agent/grounding.py), and the guardrail's two
messages are in the agent module. None of these is an input, and the pages are English with the
strings not collected for translation. Changing them is a fork of the repository, deployed by
pointing the deployment template's module `source` at the fork:

```hcl
source = "git::https://github.com/<you>/knowledge-store.git//infra/modules/knowledge-store?ref=<commit>"
```

The static name in the `<title>` and the header of both pages is in the same category: the
script replaces it with `portal_title` as soon as the page loads, so it shows for an instant.

## 5. Sign-in and email

The identity module creates the user pool and the hosted sign-in domain and leaves their look to
Cognito. Two things in the account change that:

- The sign-in page. The pool uses Cognito's classic hosted UI, whose logo and CSS are set with
  `aws_cognito_user_pool_ui_customization` (or in the console, under App integration). The
  module manages no customisation resource, so one you add beside it, or make in the console, is
  kept across applies.
- Emails. Cognito sends the temporary password and recovery codes from its own address with its
  default wording. A sender of your own needs an SES identity in the account and an
  `email_configuration` block on the pool, and the wording an `invite_message_template` under
  `admin_create_user_config` and a `verification_message_template`. Those are pool settings, so
  they are a fork of [`modules/identity`](../infra/modules/identity/main.tf).

With `site_sign_in`, people sign in on your website and none of this is shown.

## 6. Names in the data

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

## 7. Check it

Try the colours locally before you apply: put the same rules in `chat/brand.css` (a placeholder
that Terraform does not upload) and open the page with a `config.local.json` as the
[chat README](../chat/README.md#configuration) describes; `brand.logo` and `brand.icon` in it
can name files you place under `chat/brand/`. Look at both pages in light and dark mode, and at
the signed-out notice. Then `terraform validate` and `terraform plan` in your root: a missing
file, a wrong image format, a file outside `brand/` or a colour value that is not one value is
refused before the plan. The stack's tests cover what the input becomes
([`branding.tftest.hcl`](../infra/stack/tests/branding.tftest.hcl)); how it looks is checked by eye.

## What to keep

The project is licensed under the Apache License 2.0. A deployment under your name changes none
of its files, so nothing is owed beyond the licence's terms. A fork that carries your name keeps
the [LICENSE](../LICENSE) and [NOTICE](../NOTICE) files and the notices in the source files, and
adds its own notice rather than replacing them (section 4 of the licence). Third-party components
and their licences are in [THIRD_PARTY_NOTICES.md](../THIRD_PARTY_NOTICES.md); the one the page
ships is D3, in `chat/vendor/`.
