# Knowledge Store on AWS

The reference implementation: a minimal GraphRAG system that anyone can deploy from Terraform
([`infra/modules/knowledge-store`](../../infra/modules/knowledge-store)). To install it, follow
the [AWS installation guide](../deploy/aws/README.md). It has two use cases.

1. **Ingestion.** A corpus goes in. An ontology is applied to it: one you bring, or one discovered
   from the documents and reviewed. Extraction against the ontology fills a knowledge graph.
2. **Chat.** A person asks a question in a chat page. An agent answers it by querying the
   knowledge graph in the ontology's terms. Every statement in the answer links to the passage it
   comes from, and nothing unchecked is shown.

```
 Ingestion                                                       Chat

 S3 landing/<collection>/                                        person
      │ upload event, or the schedule                              │  Cognito sign-in
      ▼                                                            ▼
 ECS Fargate: the sweep                                          CloudFront ── chat page (S3)
   ingest ─ refine ─ [discover ─ review] ─ publish                 │  /api/*
   or the ontology you provide (ontology_dir)                      ▼
   ─ extract (SHACL) ─ project                                   API Gateway (JWT) ── Lambda
      │                         │                                  │  quota, concurrency cap
      │ gold RDF                │ every passage                    │  the person's own token
      ▼                         ▼                                  ▼
 Amazon Neptune            Bedrock Knowledge Base              AgentCore Runtime: the chat agent
 (SPARQL, private          (S3 Vectors, one vector               │ ontology in its prompt
  subnets, IAM auth)        per passage)                         │ answers as claims + quotes
      ▲                         ▲                                  │ grounding check, guardrail
      │ read-only SPARQL        │ Retrieve                         ▼
 tools Lambda (graph) ──── AgentCore Gateway (MCP, as the person) ── tools Lambda (passages)
 in the VPC                    interceptor: the caller's scope      outside the VPC
```

## Components

| Component | AWS service | Job |
|---|---|---|
| Lake | S3 | The record: uploads, parsed text and passages, the gold RDF per document and ontology version, the ontology's versions |
| Pipeline | ECS Fargate, EventBridge, SQS, EventBridge Pipes and Scheduler | The idempotent sweep, started by uploads and on a schedule |
| Ontology | in the lake | Provided (`ontology_dir`) or discovered and reviewed (`ontology_mode`); versions are immutable and classified |
| Knowledge graph | Amazon Neptune Database (`db.t3.medium`, or Serverless) | The gold RDF as it is: one named graph per document, and the ontology itself |
| Passage index | Bedrock Knowledge Base on S3 Vectors | Search by meaning; one vector per passage, so a hit is a passage id |
| Tools | AgentCore Gateway (MCP) with two Lambda targets | Fixed, read-only tools: entities, facts, neighbourhoods, paths, passage search and reading |
| Agent | AgentCore Runtime (a container built in your account) | Answers questions, grounded in cited passages |
| Guardrail | Amazon Bedrock Guardrails | Screens questions; checks each claim against its passages |
| Chat page and API | CloudFront, S3, API Gateway, Lambda, DynamoDB | Sign-in, the conversation, quotas, links to source documents |
| Sign-in | Cognito | People; members of `private-readers` may read private sources |
| Images | CodeBuild, ECR | The pipeline and agent images, built from this repository inside the account |

By default there is no NAT gateway. The pipeline's tasks run in public subnets to reach Bedrock. Neptune
and the graph tools' Lambda sit in private subnets with no route out, and reach S3 through a
gateway endpoint. A NAT gateway (`network.enable_nat`), the VPC's range and zones, or a VPC of your own
(`network.existing`) are inputs; see the [installation guide](../deploy/aws/parameters.md#network).

## How a question is answered

1. The chat API checks the person's daily quota and passes the question to the agent with the
   person's own access token. The token is used for that call and never stored.
2. The agent's system prompt holds the collection's released ontology (its agent rendition), so
   it plans each query in the ontology's types, relations and attributes.
3. The agent calls tools through AgentCore Gateway with the same token. The Gateway's interceptor
   writes the caller's scope into every call from the verified token. A person outside
   `private-readers` never sees private sources, whatever the model asks for.
4. Graph tools run fixed SPARQL against Neptune, built from the ontology. A search for a type
   follows `rdfs:subClassOf` in the ontology graph, so it finds subtypes too. Every fact returns
   the ids of the passages it was extracted from. The Lambda's IAM role can only read.
5. Passage tools search the Knowledge Base by meaning, filtered to the collection and the
   caller's scope, and read passages from the lake.
6. The agent answers as claims. Each claim cites passages with a quote copied from them.
7. Code checks every citation (see below). The answer shown is built only from the claims that
   pass, with numbered links to their passages and documents.

The agent streams each of these steps to the portal as it happens, and the chat page's workbench
shows them while the person waits ([docs/workbench.md](../workbench.md)).

## Grounding: no statement without a source

The model's answer is never shown as written. It is a list of claims, each with citations
(a passage id and a verbatim quote), and code checks each one:

| Check | Fails when |
|---|---|
| The passage exists and the caller may read it | The id was invented, or the passage is private and the caller is not |
| The quote is in the passage | The words are not there (case, spacing, quotes and dashes are normalised) |
| The quote says something | It is shorter than 12 characters |
| The claim follows from its quotes (the guardrail's contextual grounding) | The guardrail scores it below `grounding_threshold` |

A failed citation goes back to the agent once (`grounding_repairs`), with the reason. What still
fails is removed. A claim left without a citation is removed. When no claim is left, the answer
says the sources cannot answer the question, and lists what was missing. The checks are in
[`agent/grounding.py`](../../src/knowledge_store/agent/grounding.py) and are tested without a model.

## Valves

| Valve | Default | Where |
|---|---|---|
| Questions per person per day | 30 | `daily_questions` (the chat API, DynamoDB) |
| Questions answered at once | 20 | `valves.chat_concurrency` (the chat API Lambda's reserved concurrency; 0 turns chat off) |
| Tool calls per question | 16 | `valves.max_tool_calls`; past it, tools refuse and the agent answers from what it has read |
| Model calls per question | 14 | `valves.max_model_calls` |
| Output tokens per model call | 4000 | `valves.max_output_tokens` |
| Repair turns | 1 | `valves.grounding_repairs` |
| Question length, history | 2000 characters, 6 turns | the agent |
| Guardrail | on | `guardrail`: prompt attacks and harmful content in questions, grounding of claims |
| Monthly budget alert | off | `budget.monthly_usd` |

## Do we need a vector store?

Yes, for a reason specific to how people ask. The graph is reached through names and ontology
terms: "Which rocket launched Juno?" finds Juno by name and follows a relation. Many questions,
frontline questions above all, describe a situation instead ("the customer's card was kept by
the machine abroad"), and share no words with the article that answers them. Searching passages
by meaning finds the article, and because each vector is one passage, the hit's id leads straight
to the facts in the graph that cite it.

The Knowledge Base on S3 Vectors costs cents a month at rest, against hundreds of dollars a month
for an OpenSearch Serverless index. Turn it off (`knowledge_base.enabled = false`) for a
collection where questions name things; passage search then falls back to keywords.

## Structured data

CSV and JSON are parsed as text and extracted like any other document. Filters, totals, and
values that must match a cell need a source that keeps its schema. The draft for that lookup,
including where AWS Context Ontology Accelerator fits and where this stack stays as it is, is
[Structured lookup](structured.md).

## Evaluation

An evaluation set is a YAML file of questions, each with the facts a right answer states, a
near miss it must not state, the documents it should cite, and whether the sources can answer it
at all ([format](../../src/knowledge_store/evals/score.py); an example for the space-missions
corpus is in [`examples/evals`](../../examples/evals/space-missions.yaml)). Scoring is
deterministic, with no model as judge:

| Measure | Meaning |
|---|---|
| Correct | Every fact stated, no near miss, comparisons in the right order; for an unanswerable question, the agent declined |
| Grounded | The share of the agent's proposed claims that passed the citation checks |
| Cited an expected source | An expected document is among the sources shown |
| False abstentions, missed abstentions | Declined an answerable question; answered an unanswerable one |

```bash
# the agent in-process against a lake (your AWS credentials call Bedrock)
python -m knowledge_store.evals examples/evals/space-missions.yaml --lake s3://<lake> --model <model id> --yes
# the deployed chat, as a signed-in person (an access token in KS_TOKEN)
python -m knowledge_store.evals examples/evals/space-missions.yaml --api https://<portal> --yes
```

Every question is a model run, so a run costs money; without `--yes` the command prints its
estimate and stops. Reports go to `build/eval/`.

## Costs

| Item | Cost |
|---|---|
| Neptune `db.t3.medium` | about 60 USD a month while it runs, plus storage and I/O; the main fixed cost. `knowledge_graph.enabled = false` removes it (the graph tools then answer from memory) |
| Knowledge Base on S3 Vectors | cents a month at rest; embedding each passage once is a few cents per thousand passages |
| AgentCore Runtime, Gateway, Lambda, API Gateway, CloudFront, DynamoDB, S3 | pay per use; close to nothing idle |
| Model calls | the cost that matters: discovery reads `discovery.sample` x `discovery.resamples` documents, extraction reads every document once per full version, and each question is several calls (roughly 0.10 to 0.30 USD with a Sonnet-class model) |
| Guardrail | per text unit checked: well under a cent a question |

## Two applies

The agent's Runtime needs its container image, which CodeBuild builds after the first apply. So:
apply; wait for the agent image build (a few minutes; `outputs.agent.image_project`); set
`agent = { runtime = true }`; apply again. Until then the chat API answers with the portal's own
tool loop over the lake's projection.
