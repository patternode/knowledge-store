# Azure reference architecture

Built: [`deploy/azure/modules/knowledge-store`](../../deploy/azure/modules/knowledge-store) is the
module, [`deploy/azure/stack`](../../deploy/azure/stack) the reference root, and
[azure-setup.md](azure-setup.md) the way to deploy it from scratch. The Copilot Studio agent and
the Foundry task agent (below) are designed and not yet built.

One Terraform apply creates everything in one resource group, with two profiles that differ only
in which MongoDB and which graph database they use. Every service authenticates to every other
with a managed identity and Entra ID; storage account keys are disabled everywhere, and the only
secrets are the MongoDB and Neo4j credentials, in Key Vault.

```
                          ┌──────────── Microsoft Entra ID (people, apps, roles) ───────────┐
                          ▼                                                                 ▼
Blob landing/ ─Event Grid─▶ uploads queue ─KEDA─▶ Container Apps job ─▶ Blob lake     Storage static website
  (uploads)                 (BlobCreated)          pipeline: ingest,     bronze/ silver/   (the portal page)
                                                   refine, extract,      gold/ ontology/          │
                  Container Apps job (cron) ──────▶ project, load ───────────┐                  ▼
                                                        │                    ▼          Function App (Flex)
                                                        │         graph: PostgreSQL + AGE | Neo4j   /api/...
                                                        │         docs:  Cosmos DB for MongoDB | your MongoDB
                                                        ▼                    ▲          chat queue worker
                                               Microsoft Foundry (Claude) ◀──┼──────────── │
                                                                             │             │
Copilot Studio agent ──MCP──▶ API Management ──────────────────────▶ Function App /mcp ────┘
Foundry task agent   ──MCP──▶ (token check, rate limit)
```

## Component mapping

| Job | AWS | Azure |
|---|---|---|
| Lake | S3: versioning, encryption, TLS only, lifecycle | Storage account (ZRS): blob versioning, 14-day soft delete, old versions expire after 30 days, TLS 1.2, keys off, and a delete lock unless `force_destroy_lake` |
| Upload trigger | S3 event, EventBridge, SQS, EventBridge Pipe | Event Grid system topic, `BlobCreated` under `landing/`, delivered to the `uploads` queue with a managed identity; dead letters to a container |
| Pipeline | ECS Fargate task | Container Apps job with an event trigger: KEDA watches the `uploads` queue as the pipeline's identity and starts a run, which empties the queue and sweeps |
| The sweep | EventBridge Scheduler | a second Container Apps job with a schedule trigger (a job has one trigger type) |
| Pipeline lock | `put_if_absent` on S3 | `put_if_absent` on Blob (`If-None-Match: *`) |
| Image build | CodeBuild, ECR | ACR Tasks (`az acr build`) from this repository's source, Azure Container Registry, tagged by a hash of the source |
| Models | Bedrock | Claude in Microsoft Foundry, called with Entra ID (`LLM_PROVIDER=foundry`) |
| People | Cognito user pool, groups | Entra ID. The API's app registration exposes `access_as_user` and the app role `private-reader` |
| Applications | Cognito client credentials | App roles `tools.public` and `tools.private` on the same API |
| Portal page | S3, CloudFront | A storage account's static website (HTTPS, no server); Front Door in front for a custom domain or WAF |
| Portal sign-in | Cognito hosted UI, PKCE | Entra ID, PKCE, from a single-page app registration pre-authorised for the API; the page sends the access token |
| Portal API | API Gateway JWT authorizer, Lambda | Function App on Flex Consumption. The code verifies the Entra token itself (`knowledge_store.authn`) |
| Async chat | Lambda invokes itself | POST stores the question and enqueues it on `chat`; a queue-triggered function answers |
| Chat and quota | DynamoDB | MongoDB (`CHAT_STATE=mongodb`) |
| Tools for agents | AgentCore Gateway, interceptor, Cedar, Lambda | API Management (token check, rate limit per caller) in front of the Function App's `/mcp`, which checks the token again and sets the caller's scope |
| Secrets | Secrets Manager | Key Vault (RBAC), read by managed identities and Key Vault references |
| Logs and traces | CloudWatch, X-Ray | Log Analytics, Application Insights |
| State | S3 (bootstrap) | a storage account with Entra auth and versioning (`deploy/azure/bootstrap`) |

Choices where the design had options:

- Tokens are verified in code, not by the Function App's built-in authentication. The same code
  serves Cloud Run, it works on Flex Consumption without depending on that feature, and it keeps
  the claim rules in one tested place.
- The upload trigger is KEDA on the queue, with a managed identity, the documented pattern for
  event-driven Container Apps jobs. No function stands between the queue and the job.
- The portal page is a storage static website, not Static Web Apps: Terraform deploys it without
  another CLI, and it costs nothing beyond storage.
- App roles, not group claims: a role can be assigned to a person (or, with Entra ID P1, a
  group), arrives in the `roles` claim of user and application tokens alike, and avoids the
  group overage large tenants hit.
- API Management passes MCP through as an ordinary HTTP API, because the Function App is an MCP
  server already. API Management's own MCP features can be layered on later.

Entra does not email temporary passwords, so `admin_email` becomes `admin_principal_ids`:
existing users (or groups) that get `private-reader` and may upload to the lake.

## Profile native

| Backend | Service | Why |
|---|---|---|
| Documents | Azure Cosmos DB for MongoDB (RU), serverless, with server-side retry | MongoDB wire protocol, so the same code as Atlas; billed per request, so it idles at close to nothing |
| Graph (`graph = true`) | Azure Database for PostgreSQL flexible server (burstable B1ms, PostgreSQL 16) with Apache AGE | GA, openCypher, and the cheapest graph floor on either cloud |

AGE is allow-listed and preloaded by two server parameters. The server accepts Entra sign-in
only: the pipeline's identity is its administrator (it creates the extension and each graph) and
grants the API's identity read access to each graph it loads, so no database password exists.

## Profile common

| Backend | Service | Notes |
|---|---|---|
| Documents | your MongoDB (`mongodb_uri`): MongoDB Atlas on Azure, same region | Stored in Key Vault |
| Graph (`graph = true`) | your Neo4j (`neo4j`, `neo4j_password`): AuraDB on Azure, same region | Bolt over TLS (`neo4j+s://`); the password in Key Vault |

Both are brought, not created: Atlas and Aura have their own accounts and billing, and the
module takes their connection details. Moving between profiles is a tfvars change; the next
sweep loads the new backends, and the lake is untouched because they are projections of it.

## Tools and the gateway

- The Function App's `/mcp` is an MCP server over Streamable HTTP (`knowledge_store.tools.mcp`):
  stateless JSON-RPC, the same `TOOLS` and functions as the AgentCore Gateway target and the
  portal chat.
- API Management validates the Entra token (`validate-azure-ad-token`: tenant, audiences) and
  limits each caller (`rate-limit-by-key` on the token's `oid`) before a request reaches it.
- The Function App verifies the token again and sets `caller_private` from its roles on every
  call, overwriting anything the model sent. On AWS the tool Lambda cannot see the caller; here
  it can, so the check that matters is in the code that serves the data.

## Copilot Studio agent (people)

A Copilot Studio agent with generative orchestration, published to Teams and Microsoft 365
Copilot. It replaces nothing in the portal; it puts the same answers where people already work.

- Tools: the MCP server, added as a Model Context Protocol tool through a custom connector,
  with OAuth 2.0 against Entra. Each person signs in once and calls the tools as themselves, so
  private content reaches exactly the people with `private-reader`, as in the portal.
- Instructions tell it to call `describe_ontology` before anything else and to cite passage ids.
  They do not embed an ontology, because the active version changes without the agent changing.
- Citations render as links to the portal's passage view.
- For structured jobs (a dossier, a comparison) it calls the Foundry task agent as a connected
  agent and renders the typed result as an Adaptive Card.
- The lake is not added as a Copilot Studio knowledge source. That would bypass the ontology,
  the grounding checks and scope.
- It lives in the repository as an unmanaged Power Platform solution (`agents/copilot-studio/`),
  imported with `pac solution import`. Terraform creates the Entra app registration and the API
  Management endpoint it needs, and outputs the values for the connector. It needs a Power
  Platform environment with Dataverse and Copilot Studio capacity (licence or pay-as-you-go).

## Foundry task agent (software)

The AgentCore agent, moved with as little change as possible. `agent/app.py` keeps its request
and result types, its citation read-back and its Strands loop; only the services around it change.

| AgentCore service | Foundry equivalent | Change in `agent/app.py` |
|---|---|---|
| Runtime | Foundry Agent Service hosted agent: the container from ACR, versioned; a pinned version for production | the entrypoint adapter; Strands model becomes the Anthropic model against the Foundry endpoint |
| Identity, inbound | Entra tokens for people and applications | claim names |
| Identity, outbound (`"as": "service"`) | the agent's managed identity, granted only `tools.public` | `service_token()` gets a managed identity token |
| Gateway | API Management MCP | the MCP URL |
| Memory | sessions and long-term notes in the document backend, keyed by caller; Foundry memory as an option | a small session manager over MongoDB |
| Code Interpreter | Container Apps dynamic sessions, code interpreter pool, egress off | the tool wrapper |
| Browser | Foundry browser automation tool, optional | the tool wrapper; results still go to `external` only |
| Observability | Application Insights through OpenTelemetry | exporter configuration |
| Evaluations | Foundry evaluations (groundedness, tool call accuracy, task adherence) and a custom grader for citation grounding, over sampled traces | none |
| Registry | Azure API Center, listing the MCP server and the agent | none |
| Harness | a Foundry prompt agent with the same instructions and the MCP tool, no container | none |

Keeping Strands, rather than rewriting on Microsoft Agent Framework, keeps one agent codebase
across clouds. A hosted agent accepts any framework in its container.

## Preview at the time of writing

Check before relying on: Foundry hosted agents, Foundry memory and the browser automation tool
(the task agent), and Copilot Studio's MCP tool support in your environment.

## What it costs idle

Profile native with no graph: storage, Key Vault, a Basic container registry, Log Analytics and
API Management Basic v2; the jobs, the Function App and Cosmos DB bill only while used. API
Management is the largest floor. `graph = true` adds a burstable PostgreSQL server. Profile
common adds what Atlas and Aura charge. Model calls remain the cost that matters.
