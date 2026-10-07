# Google Cloud reference architecture

One Terraform stack (`google` and `google-beta`, plus `mongodbatlas` if Atlas is chosen) in one
project. Every service runs as its own service account with the roles it needs and nothing else;
there are no service account keys.

```
GCS landing/ ─Pub/Sub─▶ Eventarc ─▶ Workflows ─▶ Cloud Run job ─▶ GCS lake
  (uploads)  (finalize)                          pipeline: ingest,  bronze/ silver/
                         Cloud Scheduler ──────▶ refine, extract,   gold/ ontology/
                         (the sweep)             project, load ─────────┐
                                                      │                 ▼
                                                      │      graph:  Spanner Graph | Neo4j
                                                      │      docs:   Firestore (MongoDB compatible) | MongoDB Atlas
                                                      ▼                 ▲
                                          Vertex AI (Claude)            │
                                                      ▲                 │
Firebase Hosting (portal) ─▶ Cloud Run (portal API) ──┴─────────────────┤
                                  │ Cloud Tasks (async chat)            │
Gemini Enterprise ──▶ Agent Engine (ADK agent) ──MCP──▶ Cloud Run (MCP tools)
```

## Component mapping

| Job | AWS today | Google Cloud |
|---|---|---|
| Lake | S3 | Cloud Storage bucket: object versioning, uniform bucket-level access, public access prevention, lifecycle rules |
| Upload trigger | S3 event, EventBridge, SQS, Pipe | object finalize notification to Pub/Sub, Eventarc trigger, a Workflows workflow that runs the Cloud Run job (Eventarc cannot start a job directly) |
| Pipeline compute | ECS Fargate | Cloud Run job |
| The sweep | EventBridge Scheduler | Cloud Scheduler calling the Cloud Run job's run endpoint |
| Pipeline lock | `put_if_absent` on S3 | `put_if_absent` on GCS (`if_generation_match=0`); duplicate runs from bursts of uploads exit at the lock, as now |
| Image build | CodeBuild, ECR | Cloud Build, Artifact Registry |
| Models | Bedrock | Claude on Vertex AI (Model Garden), regional or global endpoint; check the partner model data terms as for Foundry |
| People | Cognito | Identity Platform; `private-reader` as a custom claim set by an admin command. It can federate to an Entra tenant over OIDC, so one directory can serve both clouds |
| Applications | Cognito client credentials | Google-signed ID tokens for service accounts, with the scope held as configuration per service account |
| Portal site | S3, CloudFront | Firebase Hosting, rewriting `/api/**` to the Cloud Run service (one origin, no load balancer floor) |
| Portal API | API Gateway, Lambda | Cloud Run service, minimum instances 0, validating the Identity Platform token in the handler |
| Async chat | Lambda invokes itself | POST stores the question and creates a Cloud Tasks task; the task calls a private route on the same service |
| Chat and quota | DynamoDB | the document backend |
| Secrets | Secrets Manager | Secret Manager |
| Logs and traces | CloudWatch, X-Ray | Cloud Logging, Cloud Trace (OpenTelemetry) |
| One-click deploy | CloudFormation runs Terraform | Infrastructure Manager runs the same Terraform; an Open in Cloud Shell link for the manual route |

## Backends

| Setting | Native | Common components |
|---|---|---|
| `GRAPH_BACKEND` | `spanner`: Spanner Graph, ISO GQL over Spanner tables, from the `spanner/` rendition (the adapter is built with this stack) | `neo4j`: AuraDB on Google Cloud, same region |
| `PROJECTION_STORE` and `CHAT_STATE` (`mongodb`) | Firestore with MongoDB compatibility, serverless | MongoDB Atlas on Google Cloud |

Spanner's smallest instance (100 processing units) is a real monthly floor, higher than a small
PostgreSQL server, so on Google Cloud `memory` matters even more as the default. At the time of
writing neither Cloud SQL nor AlloyDB lists Apache AGE; if one does, the Azure `age` backend works
unchanged and is the cheaper native graph.

## Tools

`tools/gateway.py` becomes a Cloud Run service exposing the same tools over MCP (streamable HTTP).
It validates the caller's token and derives scope itself, as on Azure. Cloud Run's own IAM
admits only the agent's service account and the Identity Platform audience. Apigee can go in
front for API products and quotas, but it has a large floor and the design does not need it.

## Agents

### Task agent: Vertex AI Agent Engine

| AgentCore service | Agent Engine equivalent |
|---|---|
| Runtime | Agent Engine. The agent can stay Strands in a custom container, or become an ADK agent; ADK is the better fit here because Sessions, Memory Bank and Gemini Enterprise registration assume it |
| Identity | inbound: Identity Platform tokens; acting as itself: its service account, public scope only |
| Gateway | the Cloud Run MCP server, through ADK's MCP toolset |
| Memory | Agent Engine Sessions (this session's requests) and Memory Bank (long-term, per caller) |
| Code Interpreter | Agent Engine Code Execution sandbox |
| Browser | Grounding with Google Search for `corroborate`, results in `external` only. It is search grounding, not a browser, so it corroborates less |
| Observability | Cloud Trace |
| Evaluations | Gen AI evaluation service, with a custom metric for citation grounding |

The request and result types, the citation read-back and the prompts carry over. The loop is
rewritten from Strands to ADK, so this is the one place the clouds would have two agent
codebases. Keeping Strands in a container avoids that and gives up the managed memory and the
Gemini Enterprise registration.

### Agent for people: Gemini Enterprise

Gemini Enterprise is the nearest equivalent of Copilot Studio, and the decision is to reach people
there by registering the Agent Engine agent in it, with a conversational mode beside its task
mode. That keeps one agent codebase for people and software, and it calls the tools with the
person's own identity, so scope works as in the portal. Agent Designer (no-code) stays optional
until it can call an MCP server as the signed-in person. Conversational Agents (the Dialogflow CX
line) was the other option; it calls OpenAPI tools, so it would need a REST twin of the MCP tools.

## Preview at the time of writing

Check before relying on: Memory Bank, Agent Engine Code Execution, Gemini Enterprise agent
registration and Agent Designer tool support, and the Firestore MongoDB compatibility features the
contract suite uses (TTL in particular).

## What it costs idle

With no graph backend and Firestore: storage, Artifact Registry and Firebase Hosting; everything
that computes scales to zero. Spanner or AuraDB, and Atlas, add their floors. Gemini Enterprise
is licensed per person.
