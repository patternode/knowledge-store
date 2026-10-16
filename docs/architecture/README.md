# Architecture

These notes describe how Knowledge Store is put together. How to install it on AWS is the [deployment guide](../deploy/aws/README.md).

## AWS

| Note | What it covers |
|---|---|
| [Knowledge Store on AWS](aws/aws.md) | The reference architecture: ingestion, chat, grounding, valves, and evaluation |
| [Graph and document backends](aws/backends.md) | Optional Neo4j, Apache AGE, and MongoDB projections behind the same API |
| [Structured lookup](aws/structured.md) | Keeping a mapped table beside the documents, so an answer can cite a cell |
| [Security design](security.md) | How the design keeps people, data and spend safe: identity, scope, grounding, untrusted input, storage, network, roles, supply chain, and its known limitations |
| [Scalability](aws/scalability.md) | What limits each part as a collection grows, an organisation's curated data, and Neptune against Neo4j as the graph |
| [Diagram](aws/architecture.png) | The reference architecture. Also [SVG](aws/architecture.svg), [draw.io](aws/architecture.drawio), and the generator [architecture.py](aws/architecture.py) |

Deploying it under a name, mark and colours of your own is [branding](../branding.md). The shared vocabulary is [core vocabulary](../core-vocabulary.md). The chat page's trace of a question is [the workbench](../workbench.md).
