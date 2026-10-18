---
title: "Landscape: where Knowledge Store sits"
---

# Landscape: where Knowledge Store sits

A platform landscape is the layers of platforms, which exist and which depends on which. Knowledge Store is one platform, so its landscape is its position: what it consumes below it, and who consumes it above.

![Landscape: the consumers of Knowledge Store above it, reaching it through the module, the chat page and API, the tools over MCP and the CLI; PL-001 Knowledge Store with its eight bounded contexts in the middle; and below it the managed services it consumes, or their alternatives off AWS](./landscape.svg)

| Relationship | With | Through |
|---|---|---|
| Consumed by | A host deployment | The Terraform module pinned by tag, moved by the host's own release process |
| Consumed by | Any deployment | The same module, from `examples/deployment` |
| Consumed by | A person's assistant | The MCP tools, where a consuming application puts a front on them |
| Consumes | AWS managed services | Terraform resources in `infra/modules/*`; each is a deployment node in [runtime/nodes.csv](runtime/nodes.csv) |
| Consumes | Claude, through Bedrock or the Anthropic API | the model client, a component of ABB-024 and ABB-014; every call priced into the ledger |
| Consumes | Optional backends | ABB-024's projection port, filled by the sweep's load stage |

The store depends on nothing above it. A consumer that wants a feature raises it here; the module never reaches into a consumer's repository.
