---
title: "Landscape: where Knowledge Store sits"
---

# Landscape: where Knowledge Store sits

A platform landscape is the layers of platforms, which exist and which depends on which. Knowledge Store is one platform, so its landscape is its position: what it consumes below it, and who consumes it above.

```
  consumers     Patternode's Knowledge Store lab (patternode-platform, deployments/knowledge-store, a pinned release)
                Any organisation's deployment from examples/deployment, pinned to a release
                A person's own AI assistant, over MCP, where the consumer exposes the tools (pna:PAT-005)
                      │ the module (CT-010), the chat page and API (CT-001), the tools (CT-002, CT-003), the CLI (CT-014)
                      ▼
  this platform  PL-001 Knowledge Store: BC-001 to BC-008
                      │
                      ▼ what it consumes, X-as-a-Service
  below           Amazon Bedrock: Claude models, the embedding model, Knowledge Bases, Guardrails, AgentCore Runtime and Gateway
                  Amazon Neptune (the graph), S3 and S3 Vectors (the record and the index), DynamoDB (chat state)
                  Cognito (sign-in), CloudFront and API Gateway (the edge), Lambda, ECS Fargate, CodeBuild and ECR (compute and builds)
                  Or, off AWS: the Anthropic API for models, a local folder as the lake, and optionally Neo4j, Apache AGE or MongoDB
```

| Relationship | With | Through |
|---|---|---|
| Consumed by | The Patternode lab | The Terraform module pinned by tag, moved by patternode-platform's master session; the lab's product is `pna:PRD-003` |
| Consumed by | Any deployment | The same module, from `examples/deployment` |
| Consumed by | A person's assistant | The MCP tools, where a consumer puts a front on them (`pna:PAT-005`, `pna:PAT-006` do this for the earnings lab) |
| Consumes | AWS managed services | Terraform resources in `infra/modules/*`; each is a deployment node in [runtime/nodes.csv](runtime/nodes.csv) |
| Consumes | Claude, through Bedrock or the Anthropic API | the model client, a component of ABB-024 and ABB-014; every call priced into the ledger |
| Consumes | Optional backends | ABB-024's projection port, filled by the sweep's load stage |

The store depends on nothing above it. A consumer that wants a feature raises it here; the module never reaches into a consumer's repository.
