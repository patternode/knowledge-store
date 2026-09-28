# The example agent, and what each AgentCore service does in it

The portal's chat answers people. This agent does tasks for software: an application, a workflow or another agent sends one explicit request and gets one typed result back, with every citation checked. It is small on purpose, so that each AgentCore service it uses is doing a job you can see.

| Request | Result |
|---|---|
| `{"task": "dossier", "collection": "holmes", "entity": "Irene Adler"}` | What the entity is, its attributes, its connections, gaps; each fact with passage ids |
| `{"task": "compare", "collection": "missions", "entities": ["Cassini", "Juno"], "aspects": ["launch vehicle", "target"]}` | A value per entity per aspect, observations, gaps |
| `{"task": "query", "collection": "holmes", "question": "..."}` | An answer, its evidence, a confidence, gaps |

Every result records the ontology version it was produced against, and every cited item is marked `verified` only if its passages could be read back.

## What each service does here

| Service | Its job in this agent | Where |
|---|---|---|
| Runtime | Hosts the agent, one isolated microVM per session. DEFAULT follows the latest version; a `prod` endpoint pins a tested one (`agent.prod_version`) | `infra/modules/agent`, `Dockerfile.agent` |
| Identity, inbound | The Runtime and the Gateway accept Cognito access tokens: people (the portal's client) and applications (client credentials) | `infra/modules/identity` |
| Identity, outbound | With `"as": "service"` the agent acts as itself: it gets a client-credentials token from the token vault through an OAuth2 credential provider. That identity holds only `tools.public`, so the agent acting as itself sees public content only | `service_token()` in `src/knowledge_store/agent/app.py` |
| Gateway | The knowledge tools over MCP, as a Lambda target: the same functions the portal chat uses, so the two cannot drift | `src/knowledge_store/tools/gateway.py` |
| Gateway interceptor | Reads the caller's verified token and writes `caller_private` into every tool call, overwriting anything the model sent | `src/knowledge_store/tools/interceptor.py` |
| Policy (Cedar) | Default deny; permits the tools for authenticated callers; forbids a private call unless the token itself carries the group or scope. It checks the claims independently of the interceptor | `aws_bedrockagentcore_policy` in the module |
| Memory | Per caller: this session's requests (so a follow-up can say "now compare it with Juno"), and long-term facts, preferences and session summaries | `memory_manager()`; three strategies in the module |
| Code Interpreter | A custom interpreter in SANDBOX mode, with no network, for counting, sorting and date arithmetic over retrieved facts. The model is told never to do arithmetic itself | `builtin_tools()` |
| Browser | Optional (`agent.browser` and `"corroborate": true`): open-web checks, reported in a separate `external` list and never mixed with the graph's facts; sessions are recorded to the lake | `builtin_tools()`, `CORROBORATE` |
| Observability | OpenTelemetry traces of every model and tool call (`opentelemetry-instrument` in the image) | `Dockerfile.agent` |
| Evaluations | Optional (`agent.evaluations`): built-in Faithfulness, ToolSelectionAccuracy and GoalSuccessRate, plus a custom judge for citation grounding, over a sample of sessions | the module |
| Registry | Optional (`agent.registry`): an Agent Registry to publish the agent and its tools in, for other teams to find | the module; records are added after apply |
| Harness | Optional (`agent.harness`): the same job as pure configuration (model, prompt, the Gateway, the Code Interpreter), with no container, to compare a managed agent loop with this Strands agent | the module |

Not used, and why: Gateway rules and configuration bundles route and A/B-test HTTP targets and prompt configuration; this agent has one Lambda target and one prompt, so they would be decoration.

## Deploy

```hcl
# terraform.tfvars, first apply
agent = { enabled = true }
```

The first apply creates the Gateway, tools, interceptor, policies, Memory, Code Interpreter, Identity, and the agent's ECR repository, and CodeBuild starts building the arm64 image (`agent.image_project` in the outputs). Once it has pushed `:latest`:

```hcl
# second apply
agent = { enabled = true, runtime = true }
```

Account-wide switch, off by default: `agent.transaction_search` sends X-Ray spans to CloudWatch Logs for the whole account, which online evaluation needs. Turn it on only if nothing else in the account relies on the current setting, then set `agent.evaluations = true`.

After apply, if you enabled the registry, add records for the agent and the Gateway in the console or with the AWS CLI (`agent-registry`); Terraform has no resource for records yet.

## Call it

```bash
python examples/agent/invoke.py dossier holmes "Irene Adler"
python examples/agent/invoke.py --session research-1 compare missions Cassini Juno --aspects "launch vehicle" target
```

`invoke.py` gets a client-credentials token for the stack's caller client (its secret is read from Cognito with your AWS credentials and never stored) and posts to the Runtime over HTTPS. Give that client private scope with `agent.caller_private = true`.

## Limits

- The Runtime needs a second apply, after its image exists.
- Cedar cannot compare a value against a claim list, so private access is a single flag checked twice (interceptor and policy), not a per-collection entitlement. Per-collection access would take one policy per collection, or an interceptor that writes an allowed list.
- The interceptor decodes the caller's token without re-verifying it, because Gateway verified it first. It must never be attached anywhere that has not.
