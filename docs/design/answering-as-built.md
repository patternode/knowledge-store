---
sidebar_label: Answering, as built
last_modified: 2026-10-26
---

# How Knowledge Store answers a question, as built on 26 October 2026

This note describes the design as it is in `main` today, from a document arriving to an answer with its citations, including what was added in October 2026: the passage vectors, the open facts and the walk over them, the reordered valves, and prompt caching. It is the record of what runs; the reasoning behind the older parts is in [Knowledge Store on AWS](aws/aws.md) and the decisions it cites, and the measurements behind the new parts are in the handover `docs/_handover-2026-10-25-baselines.md`. Where this note and the catalogue disagree, the catalogue is corrected.

## One sentence

Documents become passages; passages become three kinds of index (vectors by meaning, open facts joined into a walk, and typed facts in an ontology-shaped graph); an agent answers a question by reading passages found through whichever of those its toolset carries, and shows only the claims whose quotes code can find in a passage the person may read.

## The data the pipeline builds

Every collection is a lake under one prefix, with the same layers whatever the store (local folder or S3). Each step reads the layer before it and writes its own; nothing is rewritten in place.

| Layer | Written by | Holds | Read by |
|---|---|---|---|
| `bronze/` | ingest | the source objects as received, immutable | refine |
| `silver/documents/`, `silver/passages/` | refine | one JSON a document; its passages, about 1,800 characters each, cut at headings then sentences, with ids that hash their text | everything below |
| `silver/vectors/passages.jsonl` | `knowledge-store embed` | one Titan vector a passage, with its scope | passage search without a Knowledge Base; the walk's passage seeds |
| `silver/facts/<doc>.json` | `knowledge-store facts` | the open facts of a document: subject, predicate, object as the passage writes them, the passage id, and whether the words were found in it | the walk |
| `silver/walk/graph.json`, `silver/walk/vectors.jsonl` | `knowledge-store walk` | phrase and passage nodes with weighted edges; the embedded facts and phrases | `related_passages` |
| `gold/<version>/...` | extract | the typed graph as RDF a document, at an ontology version | project |
| the projection | project | the in-memory index, and optionally Neptune, Neo4j, AGE or MongoDB | the graph tools, the portal |
| `ontology/` | discover, curate, publish | drafts, immutable versions, the active pointer, renditions | extract, the agent's prompt |

The open facts and the walk are new. They are schema-free and need no ontology, so they exist from the first sweep; the typed graph needs a released ontology and comes later. Both point at the same passages, which is what lets an answer cite the same thing whichever index found it.

## Three ways to find a passage

| Index | Unit | Finds | Misses | Cost to build |
|---|---|---|---|---|
| Vectors | a passage | what the question's words mean; the first passage of most questions | a second passage that shares no words with the question | one embedding a passage |
| The walk | phrases and passages | passages connected to the question's named things across documents: the second and third step of a multi-step question | nothing by type; it has no types | one small-model call a batch of four passages, then one embedding a fact and a phrase |
| The typed graph | entities with types, relations and attributes | exact answers to typed questions: filters, counts, paths between named entities, each fact with its passages | anything the ontology has no term for | one large-model call a document, at each ontology version |

The walk is the HippoRAG 2 design (Gutiérrez et al., 2025). Its graph joins the two phrases of every fact, joins each passage to every phrase read from it, and joins phrases whose embeddings are close (synonyms). A question is embedded; the twenty closest facts seed their phrases; every passage is seeded by its own similarity to the question; Personalized PageRank spreads the activation with damping 0.5; the passages rank by what reaches them. The walk's ranking is then fused with the vectors' own by reciprocal rank, and each hit comes back with the passage before and after it in its document. The code is `knowledge_graph/domain/walk.py` (pure) and `knowledge_graph/slices/walk.py`; the settings that were tuned, passage weight 1.0 and twenty seed facts, are recorded there with the sweep that chose them.

## The agent

One agent, `answering/adapters/agent_app.py`, runs in three arms. An arm is a toolset and the prompt that goes with it; the loop, the valves and the checks are the same.

| Arm | Tools | Prompt | Used for |
|---|---|---|---|
| `passages` | `search_passages`, `read_passages` | search, read, stop | the baseline without a graph |
| `walk` | the passage tools and `related_passages` | related first, then search, then read | multi-document questions without an ontology |
| `all` | the graph tools, the table tools and the walk toolset | plan in the ontology's terms; the walk when the graph lacks a term | the deployed agent, when its passages target serves the walk |

How one question runs:

1. The question is screened (length, and the guardrail's prompt-attack and content filters when configured) before any model call.
2. The system prompt is built: the collection, the ontology's agent rendition for the `all` arm, the catalogue questions its tables answer, and the search cap. The prompt names `related_passages` only when the toolset carries it.
3. The model calls tools; each result goes back as data. Facts from the graph carry the ids of their passages; the agent reads passages before it cites them.
4. The model ends by calling the answer tool: `answerable`, a list of claims each with citations (a passage id and a verbatim quote, or a cell and its value, or a figure and its id), and `gaps`.
5. Code checks every citation: the passage exists and is in the caller's scope, the quote is in it, a cell or figure recomputes to the value cited. Failed citations go back once for repair. What still fails is dropped, and a claim without a surviving citation is dropped with it. The optional Bedrock Guardrail then checks each remaining claim against its source.
6. The answer shown is built from the surviving claims, with numbered sources. With none, the answer says the sources cannot answer the question and lists the gaps.

### The valves, in the order they run out

`answering/domain/valves.py` holds every limit; each is a setting and a Terraform variable.

| Valve | Default | What happens past it |
|---|---|---|
| Searches a question (`MAX_SEARCHES`) | 8 | a search is refused with "answer now or decline"; reads still run |
| Tool calls a question (`MAX_TOOL_CALLS`) | 12 | every tool is refused with the same instruction |
| Model calls kept for the answer (`RESERVED_MODEL_CALLS`) | 4 | once only these remain, every tool is refused, so the agent answers in text, the structured answer is requested, and one repair still fits |
| Model calls a question (`MAX_MODEL_CALLS`) | 14 | the hard stop |
| Output tokens a call (`MAX_OUTPUT_TOKENS`) | 8,000 | the call is cut |
| Repairs (`GROUNDING_REPAIRS`) | 1 | failed citations are dropped |

The order is the point. The searches run out first, then the tools, and the model calls last, so a question that keeps searching still ends in an answer or a plain decline. The structured answer is itself a tool call in strands and is exempt from all of these; refusing it is what the first EnterpriseRAG run's "budget spent" errors were.

### Prompt caching

The agent's model is built with strands' cache configuration on both providers. Three cache points: the system prompt (so the ontology rendition is paid for once a window, not once a call), the tool definitions, and the last user message, which holds every tool result read so far. Bedrock receives them as `cachePoint` blocks and the Anthropic API as `cache_control`; one switch, `LLM_PROVIDER`, picks the provider, and `PROMPT_CACHE=0` turns caching off. Caching changes the price of repeated input, not the answer; both providers report cache reads and writes in the usage the ledger records.

### Scope

The person's token reaches the tools, and the Gateway's interceptor writes the caller's scope into every call. Every index filters on it: the vectors carry each passage's scope, the walk seeds and returns only visible passages, the graph tools filter entities and facts, and the citation check refuses a private passage to a public caller. A passage in a private source never reaches a public answer whichever way it was found.

## Evaluation

The Evaluation context runs a set of questions through an arm (in process against a lake, or through the deployed API) or grades another system's recorded answers, with the same judge. The deterministic score counts answers, declines, citations of the expected sources and claims the verifier accepted; DeepEval's grader judges correctness against the gold answer, completeness against the answer facts and faithfulness against the cited passages, reported beside the score and never folded into it. `--tools all|passages|walk` picks the arm. The EnterpriseRAG-Bench example holds the slice, the sample, the Onyx baseline scripts and the reports.

What the measurements say, on EnterpriseRAG's sample of 120 questions, same model and judge: the passage arm and Onyx are level on lookups; Onyx leads on multi-hop by 20 to 16 passes; the walk arm closes most of that on the 23 multi-document questions, 11 of 12 multi-hop against 8, and cites the expected source on 22 of 23; completeness and cost remain Onyx's. The tables are in the handover.

## Deployment switches

| Switch | Default | Effect |
|---|---|---|
| `agent.passage_toolset` | `passages` | `walk` makes the passages target serve `related_passages` too; needs `facts` and `walk` run for the collections |
| `agent.runtime` | off | the agent on AgentCore Runtime once its image is built |
| `PROMPT_CACHE` | on | prompt caching on the agent's model |
| `LLM_PROVIDER` | unset, meaning Bedrock | `anthropic` for the API; local runs and the evaluation use it |
| the valves | above | per question |

A deployment runs a pinned release, so nothing here reaches a lab until its pin moves. The walk is off until the switch is set; everything else in this note is on.

## What is not built

- The typed graph arm has not been measured against a question set that needs types; the benchmark's questions are passage-shaped. The open facts are the floor; the ontology's case is still to be made on typed, aggregating and cross-document questions.
- The recognition-memory filter on the walk's seed facts is written (`keep_with_model`) and off.
- Open facts are extracted once, schema-free; conforming them to the ontology where it reaches (typed where the ontology has a term, open elsewhere) is the next design step, not yet started.
- The cost and completeness effect of caching, neighbours and fusion is not yet measured.
