# Architecture

These notes describe how Knowledge Store is put together. How to install it on AWS is the [deployment guide](../deploy/aws/README.md). A short film of the same ideas is the [briefing](../explainer/README.md).

## AWS

| Note | What it covers |
|---|---|
| [Knowledge Store on AWS](aws/aws.md) | The reference architecture: ingestion, chat, grounding, valves, and evaluation |
| [Graph and document backends](aws/backends.md) | Optional Neo4j, Apache AGE, and MongoDB projections behind the same API |
| [Structured lookup](aws/structured.md) | Keeping a mapped table beside the documents, so an answer can cite a cell |
| [Diagram](aws/architecture.png) | The reference architecture. Also [SVG](aws/architecture.svg), [draw.io](aws/architecture.drawio), and the generator [architecture.py](aws/architecture.py) |

The shared vocabulary is [core vocabulary](../core-vocabulary.md). The chat page's trace of a question is [the workbench](../workbench.md).
