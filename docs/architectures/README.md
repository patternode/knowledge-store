# Reference architectures for Azure and Google Cloud

The AWS stack in [`infra/`](../../infra) is the reference implementation. These documents design
the same system for Azure and Google Cloud: each names the components, what replaces what, and the
changes the Python package needs. Azure is built, in [`deploy/azure/`](../../deploy/azure)
([azure-setup.md](azure-setup.md)). Google Cloud is a design; its storage and model provider are
built, its deployment is not.

| Architecture | Graph projection | Documents (chat, quota, read model) | Agent for people (low code) | Agent for software (high code) |
|---|---|---|---|---|
| [Azure, native](azure.md#profile-1-azure-native) | Azure Database for PostgreSQL with Apache AGE | Azure Cosmos DB for MongoDB, serverless | Copilot Studio | Foundry Agent Service |
| [Azure, with common components](azure.md#profile-2-azure-with-common-components) | Neo4j (AuraDB on Azure) | MongoDB Atlas on Azure | Copilot Studio | Foundry Agent Service |
| [Google Cloud](gcp.md) | Spanner Graph, or Neo4j | Firestore with MongoDB compatibility, or MongoDB Atlas | Gemini Enterprise | Vertex AI Agent Engine |

The two Azure architectures are one implementation. Which graph service and which MongoDB service
the stack points at is a setting (`GRAPH_BACKEND` and a connection string, from terraform.tfvars);
nothing else differs. Google Cloud takes the same settings.

## What does not change

- The lake layout (landing, bronze, silver, gold, ontology) and every key in it.
- The pipeline stages, the ontology lifecycle, versions and their classification.
- The RDF in gold is the record. The index, the graph database and the document store are
  projections, rebuilt from it and safe to drop.
- One master ontology, many renditions. New backends add renditions; they never add a second
  place to edit the ontology.
- The tool contract ([`tools/schema.json`](../../src/knowledge_store/tools/schema.json)) and the
  task agent's request and result types. Every agent on every cloud calls the same fixed tools.
  There is still no free-form query tool.
- Scope. A caller sees private content only if their verified token says so, and the tool code
  derives that from the token, never from the model's arguments.

## The ports, and what each cloud plugs in

Most of the package already sits behind ports. The rest are small.

| Port | Where | AWS today | Azure | Google Cloud |
|---|---|---|---|---|
| Object store | `store.py` (`Store`) | `S3Store` | `BlobStore`: `put_if_absent` is a put with `If-None-Match: *`; etags from blob properties | `GcsStore`: `put_if_absent` is `if_generation_match=0`; etag is the generation |
| Lake URI | `--lake`, `LAKE_URI` | `s3://` | `az://<account>/<container>` | `gs://` |
| Model provider | `llm.py` (`runtime_client`) | `bedrock`, `anthropic` | `foundry` (Claude in Microsoft Foundry) | `vertex` (Claude on Vertex AI) |
| Chat state and daily quota | `portal_api/handler.py` | DynamoDB, conditional update | MongoDB API | MongoDB API |
| Caller claims | `handler.py`, `tools/interceptor.py` | `cognito:groups`, `scope` | Entra ID `roles` | Identity Platform custom claims |
| Async chat | `handler.py` | Lambda invokes itself | Storage queue and a queue-triggered function | Cloud Tasks and a Cloud Run handler |
| Projection | `portal_api/index.py` | in memory, from gold | in memory, or graph and document backends | same as Azure |
| Tool host | `tools/gateway.py` | Lambda behind AgentCore Gateway | Function behind API Management | Cloud Run MCP server |
| Agent host | `agent/app.py` | AgentCore Runtime, Strands | Foundry hosted agent | Agent Engine, ADK |

The `foundry` and `vertex` providers are small because `AnthropicConverse` already translates
Converse requests to the Messages API. Only the client changes: the Anthropic SDK's Foundry and
Vertex clients take the same Messages request. A provider for non-Claude models (Azure OpenAI,
Gemini) would need a second translation for tool calls, and the extraction prompts are tuned and
tested on Claude, so it is deferred.

Cloud SDKs go in optional extras (`[aws]`, `[azure]`, `[gcp]`, `[neo4j]`, `[age]`, `[mongo]`), so no image
carries another cloud's libraries.

## New: the graph and document backends

The portal's projection is JSON under `gold/<version>/index/`, loaded into one process's memory.
That is right for tens of thousands of entities (see Limits in the README). Two optional backends
take it further, each filled by the pipeline's `load` stage after `project`, and each set
independently:

| Setting | Values | Holds |
|---|---|---|
| `GRAPH_BACKEND` | `none` (default), `neo4j`, `age` | entities and relations, for neighbourhoods and paths |
| `PROJECTION_STORE` | `memory` (default), `mongodb` | the entities, passages and documents the portal and tools read, and their search |
| `CHAT_STATE` | `dynamodb` (default), `mongodb`, `memory` | chat answers and the daily question quota |

With `PROJECTION_STORE=mongodb` the portal API holds nothing in memory and scales out. With a
graph backend, traversals run in the database. The MongoDB settings (`MONGODB_URI`,
`MONGODB_DB`) are shared by the projection and the chat state.

### Loading and switching

A load goes into a new graph, or a new set of documents, keyed by collection, version and build.
Its counts are checked against the projection before the lake's pointer (`gold/graph.json`,
`gold/documents.json`) moves to it. The portal uses a backend only while the pointer names the
index it is serving, and answers from memory otherwise, so a failed or half-finished load is
never served. The previous load is kept for rollback (point back at it) and older ones are
dropped. The load runs at the end of every sweep and does nothing when the pointer is current, so
turning a backend on needs no migration step: the next sweep fills it.

### Graph

- Each release renders the schema per backend: `neo4j/schema.cypher`, `age/schema.sql` (the graph,
  its labels, indexes) and `spanner/schema.sql` (tables and the `CREATE PROPERTY GRAPH`
  statement). The loader runs the rendition of the active version. The mapping in
  `neo4j/mapping.json` (node key, labels, properties, provenance) is shared by all three.
- Neo4j keeps several graphs in one database (an AuraDB instance has one), told apart by `g`; a
  node is unique on `(g, id)` and carries a label per class, ancestors included. AGE keeps each
  load as a graph of its own, and gives a vertex one label, so classes are in a `types` property.
- A backend answers two primitives: a node by id, and the relations of a set of nodes. The
  neighbourhood and path traversals (`graph/traverse.py`) run on those primitives, the same code
  for memory and every backend, and a contract test checks that Neo4j and AGE give the in-memory
  answer for every entity and every pair, in both scopes. A public caller never passes through a
  private entity or along a private relation.
- The tools gain `find_paths` (every shortest chain of relations between two entities, up to four
  long) and `neighbourhood` takes `hops`; the portal API gains `/api/neighbourhood` and
  `/api/paths`. They work without a graph backend too, from memory.
- Spanner Graph has its rendition but no adapter yet. It is built with the Google Cloud stack,
  against a Spanner instance, because the emulator is not a reliable stand-in for graph queries.

### Documents

All three document targets speak the MongoDB wire protocol, so one `pymongo` implementation serves
them and the switch is a connection string. The code keeps to the subset all three support: CRUD,
`find_one_and_update` with `$inc` and a filter (the quota), `$in` and `$regex`, compound and
multikey indexes. It avoids `$text`, Atlas Search, transactions and rich aggregation, and never
depends on TTL for correctness. Search uses token arrays with a multikey index, the same tokens
`index.py` uses, and ranks as `index.py` does; a contract test checks every route and view against
the in-memory index. The suite runs on MongoDB; Cosmos DB and Firestore get the same suite at
deployment, because "compatible" differs in detail between them.

### Cost

The AWS stack idles at close to nothing. The serverless document targets keep that. Every graph
backend has a monthly floor (a burstable PostgreSQL server, an Aura instance, 100 Spanner
processing units), which is why `memory` stays the default and the graph is for collections
that have outgrown it.

## Agents: low code for people, high code for software

The AWS stack has the portal's chat for people and the AgentCore task agent for software. On
Azure and Google Cloud a low-code agent takes the chat's role where people already work (Teams,
Microsoft 365 Copilot, Gemini Enterprise), and the task agent moves to each cloud's high-code
agent service. Both call the same MCP tools, so the tools are still one implementation.

| Job | AWS | Azure | Google Cloud |
|---|---|---|---|
| Conversational agent for people | portal chat | Copilot Studio agent (Teams, Microsoft 365 Copilot, web) | Gemini Enterprise |
| Task agent for software | AgentCore Runtime (Strands) | Foundry Agent Service, hosted agent | Vertex AI Agent Engine (ADK) |
| Configuration-only agent, for comparison | AgentCore Harness | Foundry prompt agent | Gemini Enterprise Agent Designer |
| Tools over MCP | AgentCore Gateway, Lambda target | API Management MCP server, Function | Cloud Run MCP server |
| Caller scope enforced | interceptor and Cedar | API Management policy, and the Function checks the token again | the MCP server checks the token |
| Acting as itself | token vault, client credentials | managed identity with the `tools.public` role only | service account with public scope only |
| Memory | AgentCore Memory | sessions in the document store; Foundry memory optional | Agent Engine Sessions and Memory Bank |
| Sandboxed computation | Code Interpreter | Container Apps dynamic sessions | Agent Engine Code Execution |
| Open-web corroboration | Browser | Foundry browser automation, optional | Grounding with Google Search, optional |
| Traces | OpenTelemetry to CloudWatch | Application Insights | Cloud Trace |
| Evaluations | AgentCore Evaluations | Foundry evaluations with a custom grounding grader | Gen AI evaluation service |
| Registry | Agent Registry | Azure API Center | Gemini Enterprise agent registration |

## Deployment, the same shape everywhere

| | AWS | Azure | Google Cloud |
|---|---|---|---|
| One-click route | CloudFormation stack runs Terraform in CodeBuild | Deploy to Azure button: a template whose deployment script runs the Terraform | Infrastructure Manager runs the Terraform |
| Terraform route | `infra/stack` | `deploy/azure/stack` | `deploy/gcp/stack` |
| Images built in your account from this source | CodeBuild, ECR | ACR Tasks, Azure Container Registry | Cloud Build, Artifact Registry |

The existing `infra/stack` and `infra/modules` stay where they are, so nobody's AWS paths move. Every
other cloud's deployment code goes under `deploy/<cloud>/`.

## Build order

Steps 1 and 2 are built, and the Azure infrastructure of step 3 ([azure-setup.md](azure-setup.md)).

1. Core ports, cloud-neutral: `BlobStore`, `GcsStore`, the `foundry` and `vertex` providers, the
   chat state port (`portal_api/state.py`) with a MongoDB adapter, configurable claim names
   (`claims.py`). Contract tests against local emulators ([`tests/emulators.yml`](../../tests/emulators.yml)).
2. The graph port, the `age` and `spanner` renditions, the document store and the `load`
   stage, with contract tests against Neo4j, AGE and MongoDB containers.
3. Azure infrastructure, both profiles, then the Copilot Studio agent and the Foundry task agent.
4. Google Cloud infrastructure and agents.

## Decisions

| Question | Decision | Consequence |
|---|---|---|
| The model on Azure native | Claude in Microsoft Foundry | One Messages API path on every cloud. Claude in Foundry is sold and operated by Anthropic, which is the data processor for prompts and outputs even on the Azure-hosted option, so "native" describes the infrastructure, not the processor |
| The tools gateway on Azure | API Management | Policy, quotas and one MCP endpoint for every agent, with a monthly floor. The Functions MCP extension is not built |
| Neo4j hosting | AuraDB, same region as the stack | No database server to run; Private Link needs Business Critical |
| The low-code surface on Google Cloud | Gemini Enterprise, with the Agent Engine agent registered in it | One agent codebase (ADK) for people and software; Agent Designer stays optional until it can call the tools as the person |

Features that were in preview when this was written are marked in each document. Check their
status before building on them.
