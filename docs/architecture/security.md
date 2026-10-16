# Security design

How Knowledge Store keeps people, data and spend safe, and why it is built the way it is. This
note is the design. What to restrict in your own account before deploying, and how to report a
vulnerability, is [SECURITY.md](../../SECURITY.md). Each component's Terraform and the IAM roles
are in [components](../deploy/aws/components.md#security-model). The reference architecture is
[Knowledge Store on AWS](aws/aws.md).

## Six rules

1. The person's identity goes all the way down. The chat page, the API, the agent and the tools
   all see the same verified token, and each reads who is asking from it. Nothing between the
   browser and the data acts as a service with more rights than the person has.
2. Nothing unchecked is shown. The model's answer is a list of claims with citations, and code
   checks every citation against a source the caller may read before anything reaches the page.
3. Documents and questions are untrusted input. They reach the models, and they are read as
   data: nothing in them changes the ontology, grants access or runs.
4. Nothing listens without a verified token, and nothing is pulled from outside the account
   except pinned base images. Images are built inside the account from the source you deployed.
5. Every role does one job. The pipeline alone writes the graph; the tools only read it; the
   portal writes one prefix of the lake.
6. Spend has valves. Each question, each person and each day has a limit, and the account can
   have a budget.

## Trust boundaries

```
 browser (the chat page)            the account
 ───────────────────────  ──────────────────────────────────────────────────────────────
  Cognito sign-in (PKCE)   CloudFront ── S3 site bucket (private; origin access control)
  token in sessionStorage      │ /api/*  + x-origin-verify
                               ▼
                           API Gateway: Cognito JWT authorizer (or the site grant, below)
                               │
                               ▼
                           portal Lambda: reads sub and groups from the verified claims
                             quota (DynamoDB), input limits, scope filter on every view
                               │ the person's own token, in the invoke payload only
                               ▼
                           AgentCore Runtime: JWT authorizer, allowed clients = the portal's
                             the agent: valves, its own daily count, guardrail, grounding
                               │ the same token
                               ▼
                           AgentCore Gateway: JWT authorizer ── interceptor writes caller_private
                               │                                 from the verified claims
                      ┌────────┴─────────┐
                      ▼                  ▼
           graph tools Lambda     passage tools Lambda
           in the VPC, read-only  outside the VPC, bedrock:Retrieve
                      │                  │
                      ▼                  ▼
              Neptune (IAM auth,   Knowledge Base ── lake (S3): silver, gold, ontology
              private subnets)
                                  pipeline task (ECS Fargate): the only writer of Neptune,
                                  started by uploads and a schedule; egress only
                                  CodeBuild: builds both images from the uploaded source
```

Four boundaries matter:

| Boundary | Crossed by | Checked by |
|---|---|---|
| The internet to the portal | a browser | CloudFront, then API Gateway's JWT authorizer; a web ACL if you attach one |
| The portal to the agent | the person's token | the Runtime's JWT authorizer (issuer, signature, allowed client) |
| The agent to the tools | the same token | the Gateway's JWT authorizer, then the interceptor, which sets the caller's scope |
| Documents to the models | the pipeline | nothing stops a document's text reaching a prompt; grounding and curation stop it changing anything |

## Identity and sign-in

People sign in with the stack's Cognito user pool, or with a host website.

Cognito ([`modules/identity`](../../infra/modules/identity/main.tf)):

- Only an administrator creates users. There is no self sign-up, so an account exists only when
  someone made it. The first user is `admin_email`, who gets a temporary password by email.
- The password policy is 12 characters with upper and lower case and a digit. An authenticator
  app can be added as a second factor; it is optional, because the portal has no set-up flow for
  it and requiring it would lock out existing users at their next sign-in.
- The page signs in with the authorisation code flow and PKCE through one public client, which
  has no secret. Access and id tokens last 60 minutes, the refresh token 12 hours, and
  revocation is on. The page keeps the tokens in `sessionStorage`, so they go when the tab closes,
  and refreshes them shortly before they expire.
- The pool's deletion protection is off by default so that destroying works; turn it on for a
  long-lived deployment.

Sign-in through a host website (`site_sign_in`, [`site_grant.py`](../../src/knowledge_store/site_grant.py)):

- The website signs people in and frames the portal. It hands each page a short grant, an ES256
  JWT whose audience names this lab, and renews it before it expires. The page sends it as
  `X-Site-Grant` on every request.
- The portal verifies the grant on every request against the website's public keys, which are
  configuration, so a request never waits on the website: signature, issuer, audience and
  expiry. The portal can verify a grant and never mint one. The verification is written against
  the standard library and tested against another implementation's signatures.
- The portal, not the website, decides what a role may do. A role in `roles` may read, one in
  `private_roles` may also read private-scope content, and a person with neither is refused.
- The portal then asks the agent as one of two service clients, public or private, whose Gateway
  scopes match what the person may read. Their credentials live in Secrets Manager, readable by
  the portal's role alone.

## Authorisation: scope follows the token

Every piece of content is public or private. A source is `scope = "private"`, and the facts and
passages from it are shown only to callers who may read private content: a person in the
`private-readers` group, a person with a private role of the website, or an application with the
`tools.private` scope. The rule is one function ([`claims.py`](../../src/knowledge_store/claims.py)),
and it is applied at each hop:

| Hop | Who checks | What it reads |
|---|---|---|
| The portal API | API Gateway, then the Lambda | the Cognito token's `sub` and `cognito:groups`, or the site grant's roles |
| The agent | the Runtime's authorizer | the same token; the agent's daily count uses its `sub` |
| The tools | the Gateway's authorizer, then the interceptor | the token's groups or scopes, written into every tool call as `caller_private` |

The interceptor ([`tools/interceptor.py`](../../src/knowledge_store/tools/interceptor.py)) runs
after the Gateway has verified the token. It overwrites whatever the model or the caller put in
`caller_private`, so the model cannot ask for more than the person may read. The tools trust only
that argument, and only a real boolean true: a call that arrives without the interceptor, such as
a local run, serves public content.

Two more rules on the portal API: ontology drafts and ontology requests are for curators, which
is to say private readers, because a draft's samples can quote private documents. A link to a
source document or a bound table is signed only after the scope check, and lasts ten minutes.

The agent acts only as its caller. The portal passes the person's own token to the Runtime in
the invoke payload of its asynchronous half and nowhere else: it is not written to the chat state
or the logs. The agent presents the same token to the Gateway. There is no service identity in
the chat path that could read more than the person asking, apart from the two service clients
of site sign-in, each scoped to what its people may read.

## The chat page

The page is static HTML, CSS and JavaScript with no build step and no external scripts or fonts
([`chat/README.md`](../../chat/README.md)). Its Content-Security-Policy allows scripts and styles
from its own origin only, no inline code, images from its origin or data URIs, connections to its
own origin and Cognito, no objects, no base element, and no frames. No server text reaches
`innerHTML`: the DOM is built from nodes and `textContent`, so a document title or an answer
cannot inject markup.

CloudFront adds the managed security headers (`X-Content-Type-Options`, `Referrer-Policy`,
`Strict-Transport-Security`, `X-Frame-Options`). With site sign-in, a policy of the stack's own
replaces `X-Frame-Options` with `frame-ancestors` naming the website and the portal, so only
they can frame the pages.

The API's cache policy keys on the `Authorization` and `X-Site-Grant` headers with a zero default
TTL, and the API sends `cache-control: no-store`, so no answer is ever served to another person.

## The portal API

The path is CloudFront, then API Gateway, then the Lambda
([`modules/portal`](../../infra/modules/portal/main.tf),
[`portal_api/handler.py`](../../src/knowledge_store/portal_api/handler.py)).

- API Gateway checks the Cognito token before the Lambda runs. With site sign-in the route is
  open at API Gateway and the Lambda verifies the grant instead, on every request.
- CloudFront sends a secret `x-origin-verify` header to the API origin, and the Lambda refuses a
  request without it. API Gateway's own `execute-api` endpoint is public, so without this a caller
  could go round CloudFront and a web ACL attached to it; with it, going round gains nothing.
- The API is throttled for the whole stage (`api_throttle`, 20 a second and a burst of 50 by
  default), and a `CLOUDFRONT`-scope web ACL can be attached (`portal_web_acl_arn`).
- Inputs are bounded before any work: a question is at most 2000 characters, a search 200, an
  earlier answer passed back as history 4000, and limits and offsets are clamped.
- Each person's daily questions are counted with a conditional write in DynamoDB, so the limit
  holds across concurrent requests. A refused question costs no model call.
- A question is answered asynchronously, because API Gateway allows an integration 30 seconds.
  The Lambda invokes itself with the job, and the page polls. Its reserved concurrency
  (`valves.chat_concurrency`) caps how many answers run at once, and setting it to 0 turns the
  chat off.
- The Lambda's role reads the lake's served layers, writes one prefix (ontology requests kept
  from the workbench), reads and writes the chat table, invokes the chat model and itself, and
  nothing else.
- Each request is one line in the access log, with the caller's `sub`. Errors go back to the
  caller as a generic message and to the log in full.

## The agent

The agent on AgentCore Runtime ([`modules/agent`](../../infra/modules/agent/main.tf),
[`agent/app.py`](../../src/knowledge_store/agent/app.py)) accepts only tokens from the portal's
client and the service clients. Its only incoming header is `Authorization`. A session idles out
after `agent.idle_session_minutes`.

Grounding ([`agent/grounding.py`](../../src/knowledge_store/agent/grounding.py)) is the control
that makes the answer safe to show. The model's answer is never shown as written. It is a list of
claims, each citing a passage with a verbatim quote, or a cell or a figure of a mapped table, and
code checks each citation:

| Check | Fails when |
|---|---|
| The passage exists and the caller may read it | the id was invented, or it is private and the caller is not |
| The quote is in the passage | the words are not there, after normalising case, spacing, quotes and dashes |
| The quote says something | it is shorter than 12 characters |
| A cited figure matches its own computation | the total, filter or group does not recompute from the snapshot |
| The claim follows from its source | the guardrail's contextual grounding scores it under `guardrail.grounding_threshold` |

A failed citation goes back to the agent once with the reason. What still fails is removed, a
claim with no citation left is removed, and when nothing is left the agent says the sources
cannot answer. The checks are plain functions and are tested without a model.

The Bedrock Guardrail screens each question for prompt attacks (high strength) and harmful
content (medium), and checks each remaining claim's grounding. Its refusal messages name no
internals.

The valves ([`agent/valves.py`](../../src/knowledge_store/agent/valves.py)) bound every
question: tool calls, model calls, output tokens per call, repair turns, question length and
history. Past the tool limit, tools refuse and the agent answers from what it has.

Because a person can call the Runtime directly with the token the portal forwards, the agent
counts each person's invocations per day itself ([`agent/quota.py`](../../src/knowledge_store/agent/quota.py)),
in the portal's state table under its own key space, set a little above the portal's limit so a
retry through the portal is not refused. The service clients are exempt, because only the portal
holds their credentials and the portal has already counted the person.

## Documents and the ontology are untrusted input

Document text reaches the models during discovery, extraction and chat, and a question reaches
them during chat. The design assumes both can carry instructions, and limits what instructions
can do rather than trying to detect them:

- Nothing changes the ontology without a person publishing a version. Discovery writes a draft.
  Extraction records the terms it lacked as candidates, which stay out of the graph. A proposed
  next version is a draft until someone publishes it. With `ontology_mode = "auto"` the first
  discovered draft is published unreviewed, which is a choice to make knowingly.
- An example a model proposes during discovery is dropped unless it appears in the passage it
  cites. An extracted fact is checked for grounding (names and values must appear in the cited
  passages) and against SHACL, and repaired or dropped item by item.
- The tools are fixed and read-only. The model chooses which to call and with what arguments; it
  cannot run a query of its own, write anything, or widen its scope (above).
- The answer the person sees is built from checked claims only, so an instruction in a document
  can at most waste a question, not put unsupported text in front of a person.

What remains is the risk that a planted document steers which passages are read or which facts
are stated, within what the sources support. Weigh it for your corpus; it is why private
documents sit behind the scope filter rather than in a shared prompt.

Ingestion is bounded as well ([`adapters/http_urls.py`](../../src/knowledge_store/adapters/http_urls.py),
[`refine/parsers.py`](../../src/knowledge_store/refine/parsers.py)):

- The URL adapter fetches HTTPS only, initially and across redirects, and only from hosts that
  resolve to public addresses, so a listed page cannot send the fetcher onto the account's own
  network. The name is resolved again when connecting, so a host that changes its answer in
  between is not caught; that is a stated limit.
- A response is capped at 50 MB, and a document is refused before parsing over 20 MB (100 MB for
  PDF). Uploads land in the lake as they are; what the pipeline does with them is bounded.
- Bronze keeps one immutable, content-addressed copy of each distinct file with where it came
  from, so what was extracted from can always be read back.

## Data at rest and in transit

| Store | Protection |
|---|---|
| The lake (S3) | SSE-S3; versioning on, with old versions kept 30 days, so an overwrite or delete in any layer is recoverable; public access blocked; a bucket policy denies anything but TLS |
| The site bucket (S3) | public access blocked; only the stack's CloudFront distribution may read it, through origin access control |
| The build bucket (S3) | public access blocked; TLS required; writing under `source/` starts a build, so writes belong to the applying identity only (below) |
| Neptune | encrypted at rest; no public endpoint; IAM database authentication, so a client's role says what it may do; reachable only from its two client security groups, on one port; backups one day, because it is a projection the next sweep rebuilds |
| The vector index (S3 Vectors) | encrypted with AWS-managed keys; its Knowledge Base role reads one prefix of the lake and calls one embedding model |
| The chat table (DynamoDB) | encrypted; on demand; a TTL expires answers and quotas, while the ontology use totals stay |
| Queues (SQS) | SQS-managed encryption |
| Secrets Manager | the Anthropic API key when `llm_provider = "anthropic"` (the stack takes the secret's ARN, never the key), and the service clients' credentials under site sign-in |
| Logs | CloudWatch, kept `log_retention_days` (30 by default) |

Every connection between components is TLS: the browser to CloudFront, CloudFront to the API,
the Lambda to AWS services, the agent to the Gateway, the tools to Neptune and the Knowledge
Base. Model calls stay inside AWS with the default `llm_provider = "bedrock"`.

## Network

Nothing listens on a public IP. CloudFront, API Gateway, the Runtime and the Gateway are managed
endpoints that require a token. The module's own VPC has public subnets for the pipeline's tasks
and private subnets with no route out for Neptune and the graph tools, which reach S3 through a
gateway endpoint. The pipeline's task security group allows egress only; the tasks hold a public
IP to reach Bedrock, ECR and S3 without a NAT gateway, which is the cheaper default. With
`network.enable_nat` they move to the private subnets, and with `network.existing` the stack uses
subnets of yours.

The passage tools' Lambda runs outside the VPC, since it calls only Bedrock and S3. The Runtime's
network mode is public, which is what lets the portal reach it; its authorizer is the control.

## Least privilege: the roles

Each role may do only its job. The full table is in
[components](../deploy/aws/components.md#iam-roles); the separations that matter:

- The pipeline's task role is the only principal that writes Neptune and the lake's layers. It
  invokes the extraction model only, reads the source buckets you configured, and starts
  Knowledge Base ingestion.
- The graph tools' role connects to Neptune and reads; it cannot write or delete. The passage
  tools' role may only `Retrieve` from the Knowledge Base and read silver and gold.
- The portal's role reads the served layers, writes ontology requests, and invokes the chat
  model named in `chat_model_id` and nothing broader. A model given as an inference profile is
  resolved to its foundation model, so the grant names one model.
- The Gateway's role may invoke the three Lambdas and read the tool schemas. The Runtime's role
  pulls its image, invokes models, applies the guardrail, counts its quota and writes telemetry.
- CodeBuild's role reads the source bundle and pushes to the two repositories. The build trigger
  may only start those two projects.

Every role carries `permissions_boundary` when you set one, for an organisation that requires it.

## Supply chain and deployment

- Both container images are built by CodeBuild inside the account from the repository you
  deployed: Terraform zips the source into the build bucket, and the upload starts the build.
  Nothing runs on the machine that applies Terraform, and nothing is pulled from a registry you
  do not own except the Python base image from ECR Public, pinned by digest in both Dockerfiles.
  Dependabot proposes updates to it, to the Python dependencies, to the Actions and to the
  Terraform providers, each a few days after its release so that a hijacked version is usually
  pulled before it is proposed.
- The repositories' tags are mutable, because the pipeline and the agent run `:latest` and the
  build finishes after the apply that names it. The consequence is that anyone who can write
  under `source/` in the build bucket changes the code the pipeline and the agent run. Only the
  identity that applies Terraform should hold `s3:PutObject` there; the bucket policy cannot name
  it without breaking applies by other principals, so restrict it in IAM.
- CI pins every Action to a commit, validates the module and the deployment template and runs
  the Terraform tests with mocked providers, lints the launch stack, and runs the Python tests
  offline against a fake model.
- The launch stack runs Terraform in a CodeBuild project whose role has `AdministratorAccess`,
  because Terraform creates and deletes IAM roles and a dozen services, and a narrower policy has
  not been validated. Whoever may start or change that project, or invoke its Starter function,
  is an administrator. [SECURITY.md](../../SECURITY.md#the-launch-stack-cloudformation) gives the
  policy to apply. Set `SourceSha256`, or the build runs whatever `SourceUrl` serves at the time.
- The deployment template's CI plans with a read-only role on every pull request and applies
  with a second role that only a protected environment can assume
  ([examples/deployment](../../examples/deployment/README.md#ci)).

## Spend

A runaway question, a runaway person and a runaway day each meet a limit before the bill does:

| Limit | Where |
|---|---|
| Per question | the valves: tool calls, model calls, output tokens, repair turns |
| Per person per day | `daily_questions` in the portal, and the agent's own count |
| At once | the chat API's reserved concurrency; the API's throttle; a web ACL, which a CloudFront flat-rate plan brings |
| Per month | `budget.monthly_usd`, mailed at 80% and when forecast to pass 100% |

Discovery reads a sample, so its cost does not grow with the collection. Extraction reads each
document once per full ontology version, and publishing refuses a version number that
understates its change, so a re-extraction is never accidental.

## Logging and audit

| What | Where |
|---|---|
| Every API request, with method, path, status, source IP and the caller's `sub` | `/aws/vendedlogs/apigateway/<name>-portal` |
| The portal Lambda's log, including every failed request in full | `/aws/lambda/<name>-portal-api` |
| The agent's log, traces and metrics | the Runtime's CloudWatch log group and X-Ray |
| Each tool call, by the Gateway and the tools' Lambdas | their log groups |
| Each sweep, document by document | the pipeline's log group (`pipeline_logs`) |
| Each image build | the two CodeBuild projects' logs |
| Every change to the stack | CloudTrail, which is the account's |

The lake also keeps a ledger of every model call with its tokens and list-price cost, under
`usage/ledger/`, and its versioning keeps what each layer held before.

## Known limitations

These are the places where the design accepts a risk or leaves a decision to you:

| Limitation | Why | What you can do |
|---|---|---|
| The launch stack's deploy role is an administrator | a narrower policy is not validated against a real deploy and destroy | restrict who may start the project; or deploy with Terraform under your own role |
| Image tags are mutable | the build finishes after the apply that names the tag | restrict writes to the build bucket's `source/` prefix |
| A second factor is optional | the portal has no set-up flow, and requiring it locks out existing users | add it per user; or sign people in through a website that requires one |
| The `execute-api` endpoint is reachable | API Gateway's HTTP API has no private mode behind CloudFront | the origin header makes it useless; `api_throttle` still bounds it |
| Private scope is a filter, not separate storage | one lake, one graph, one index per stack | put content that needs a hard boundary in its own stack or account |
| Prompt injection through documents | document text must reach the models to be extracted | curated mode; grounding; weigh the corpus |
| DNS rebinding on the URL adapter | the connection resolves the name again | list only hosts you trust |
| The Runtime is reachable with a valid token | that is how the portal calls it | the agent's own daily count; the valves |
| Deletion protection is off on Cognito and Neptune | so that destroy and the launch stack's delete work | turn both on for a long-lived deployment |
| The pipeline's tasks hold a public IP | no NAT gateway by default | `network.enable_nat`, or your own subnets |
| The interceptor decodes claims without re-verifying | the Gateway verified the token a moment before | none needed; noted so it is not mistaken for a gap |

## Where each control lives

| Control | File |
|---|---|
| Who may read private content | [`src/knowledge_store/claims.py`](../../src/knowledge_store/claims.py) |
| The caller's scope on every tool call | [`src/knowledge_store/tools/interceptor.py`](../../src/knowledge_store/tools/interceptor.py) |
| The site grant | [`src/knowledge_store/site_grant.py`](../../src/knowledge_store/site_grant.py) |
| Citation checks | [`src/knowledge_store/agent/grounding.py`](../../src/knowledge_store/agent/grounding.py) |
| Limits per question | [`src/knowledge_store/agent/valves.py`](../../src/knowledge_store/agent/valves.py) |
| The agent's daily count | [`src/knowledge_store/agent/quota.py`](../../src/knowledge_store/agent/quota.py) |
| The portal's routes, quota, origin check and input limits | [`src/knowledge_store/portal_api/handler.py`](../../src/knowledge_store/portal_api/handler.py) |
| URL fetching | [`src/knowledge_store/adapters/http_urls.py`](../../src/knowledge_store/adapters/http_urls.py) |
| Size limits on documents | [`src/knowledge_store/refine/parsers.py`](../../src/knowledge_store/refine/parsers.py) |
| The page's policy and DOM rules | [`chat/index.html`](../../chat/index.html), [`chat/common.js`](../../chat/common.js) |
| Sign-in | [`infra/modules/identity/main.tf`](../../infra/modules/identity/main.tf) |
| CloudFront, the API and its role | [`infra/modules/portal/main.tf`](../../infra/modules/portal/main.tf) |
| The Gateway, tools, guardrail and Runtime | [`infra/modules/agent/main.tf`](../../infra/modules/agent/main.tf) |
| The lake | [`infra/modules/lake/main.tf`](../../infra/modules/lake/main.tf) |
| Neptune | [`infra/modules/knowledge-graph/main.tf`](../../infra/modules/knowledge-graph/main.tf) |
| Image builds | [`infra/modules/image-build/main.tf`](../../infra/modules/image-build/main.tf), [`Dockerfile`](../../Dockerfile), [`Dockerfile.agent`](../../Dockerfile.agent) |
| The launch stack | [`infra/launch/knowledge-store.yaml`](../../infra/launch/knowledge-store.yaml) |
