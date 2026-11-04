---
sidebar_label: Changes since 0.4
last_modified: 2026-10-26
---

# What has changed since 0.4.0, and why

Release 0.4.0 was cut on 17 October 2026. This note lists what has changed in Knowledge Store since then, release by release and then what is on `main` unreleased, with the reason for each change. The lines come from the changelog and the pull request descriptions; the reasons come from the decisions and the handovers they cite. For the design as it stands now, read [Answering, as built](answering-as-built.md).

## In one table

| Release | Date | Change | Why |
|---|---|---|---|
| 0.4.1 | 18 Oct | architecture diagrams and cards; the documentation made agnostic of any consuming deployment (#98, #101) | the lab that consumes Knowledge Store had leaked into its documentation; the reference architecture had no pictures |
| 0.5.0 | 20 Oct | the code cut into eight bounded contexts with slices, ports and adapters; an Evaluation context; tests at every level with coverage floors; a target-state view by subdomain (#108, #103, #104) | the engineering standard (patternode-architecture ADR-046, ADR-047, ADR-048): one model per context, one contract, boundaries checked on every test run |
| 0.6.0 | 24 Oct | DeepEval as the evaluation framework, a runner and a model grader beside the deterministic score; grading another system's recorded answers; judging completeness; the EnterpriseRAG-Bench slice and its 490 questions (#110, #113, #109) | to compare Knowledge Store with other systems on the same questions and the same judge, which the deterministic score alone could not do (ADR-013) |
| 0.7.0 | 24 Oct | literals conformed before chunking; the value kinds and measures ontologies (#111) | numbers, dates, periods and sizes written many ways in the sources were reaching extraction unnormalised; the measures ontology gives the enterprise ontology a base to build on |
| 0.8.0 | 25 Oct | a passage-search arm with vectors over every silver passage; the local agent follows `LLM_PROVIDER`; the model client drops the sampling settings the Anthropic SDK no longer takes (#117, #115) | a baseline without the graph to compare the graph against; the local evaluation had been building a Bedrock model whatever the provider said |
| unreleased | 25 Oct | the stop rule: searches run out before tools before model calls, the last model calls reserved for the answer, the structured answer never refused as a tool call, output tokens 8,000 (#119) | eleven of 120 EnterpriseRAG questions ended in "budget spent"; the traces showed the agent's answer being refused as one more tool call |
| unreleased | 26 Oct | open facts and the walk: schema-free triples from every passage, a graph of phrases and passages, `related_passages`, a `walk` arm, a Terraform switch for the deployed passages target (#122) | the remaining gap to Onyx was multi-hop retrieval; the literature's best graph method at plain-retrieval cost keeps passages as the unit and uses the graph to connect them |
| in review | 26 Oct | prompt caching on both providers; hits returned with their neighbouring passages; the walk fused with the vector ranking (#123) | the walk arm spent 190,000 input tokens a question resending its context; Onyx's lead on completeness comes from handing the model each hit's neighbours |

## The releases in detail

### 0.4.1: the documentation stands alone

Two documentation changes. The architecture gained its diagrams (landscape, use cases, contexts) and a card per building block, with the reference architecture registered as RA-001. And every mention of the deployment that consumes Knowledge Store was removed from its documentation, so the repository describes a product, not one installation of it. Nothing in the code changed.

### 0.5.0: bounded contexts, slices, ports and tests

The one structural change of the period. The package was cut into eight contexts (ingestion, ontology, extraction, knowledge graph, answering, access, evaluation, platform services), each with a pure domain, feature slices over it, ports only where an adapter varies, adapters at the edge, and one contract other contexts import. import-linter holds the layers and the contracts; `tests/test_architecture.py` holds the rest; coverage floors per context and layer only rise. Evaluation became a context of its own rather than a script.

Why: patternode-architecture's engineering standard (ADR-046 contexts, slices and ports; ADR-047 knowledge contexts on Knowledge Store; ADR-048 evaluation) says how code is cut and tested in every Patternode repository, and this repository is where the standard was first applied in full. Every change since has had a named context and slice to go in, which is why the October additions below could be made quickly and checked by the same floors.

### 0.6.0: a judge, and a benchmark to use it on

DeepEval was adopted as the evaluation framework: a runner that turns a set into test cases, and a model grader that judges correctness against the gold answer, completeness against the answer facts and faithfulness against the cited passages. The grader's verdict is reported beside the deterministic score, never folded into it, so a model's opinion cannot move a release gate on its own (ADR-013). The evaluator also grades another system's recorded answers from a file, so a competitor can be scored by the same judge. EnterpriseRAG-Bench's slice (722 documents, 490 questions, with a 120-question stratified sample) came in as the testbed.

Why: the question Dermot put was whether Knowledge Store's pipeline is at least as good as Onyx. That needs the same questions, the same judge and a way to score Onyx's answers. The deterministic score cannot judge an answer's correctness; a model can, if its verdict is kept separate.

### 0.7.0: literals conformed, and a measures base

Numbers, dates, clocks, periods, sizes, identifiers and punctuation are normalised in the silver text before chunking, so extraction and search see one spelling of each value. Two small ontologies, value kinds and measures (Metric, Quantity, Instant, Period), give the enterprise ontology terms to build on rather than redeclare.

Why: the enterprise corpus writes the same value many ways, and the ontology derived from it was inventing value classes the measures ontology should supply.

### 0.8.0: a baseline without the graph

`knowledge-store embed` writes one Titan vector a passage to the lake, and passage search uses them wherever no Knowledge Base is configured. `--tools passages` runs the agent with search and read alone, no graph, no tables, no ontology in the prompt: the arm the graph is compared against. Two fixes came out of running it: the local agent now follows `LLM_PROVIDER`, and the model client sends `temperature` only when the SDK's signature still takes it.

Why: a graph's value can only be shown against the same agent without it. Running the arm on the EnterpriseRAG sample gave the first numbers: 105 of 120 correct, with 13 errors.

### Unreleased on `main`: the stop rule (#119)

The first comparison found Knowledge Store level with Onyx on lookups and behind on multi-hop, with 13 questions answered by nobody. The traces showed one cause: once the tool budget was spent, the agent's structured answer, which strands delivers as a tool call, was refused like any other tool, so the agent answered, was refused, and answered again until its model calls ran out. The answer tools are now exempt; searches are capped at 8, tools at 12, the last 4 model calls are reserved for the answer, and output tokens rose to 8,000 for list answers. Re-run on the 30 hard questions: no errors, all five unanswerable questions declined, the same 17 passes on the answerable ones. The gap left was retrieval.

### Unreleased on `main`: open facts and the walk (#122)

A schema-free layer under the typed graph, the HippoRAG 2 design. `knowledge-store facts` has a small model record every passage's facts as triples between named things, copied as written; `knowledge-store walk` embeds the facts and the distinct phrases, links close phrases as synonyms, and writes a graph of phrase and passage nodes. `related_passages` seeds Personalized PageRank from the facts closest to a question and returns the passages that activation reaches, with the facts that led there. A `walk` arm adds it to the passage tools; the deployed passages target serves it only when `agent.passage_toolset` says `walk`.

Why: the walk is the retrieval shape that finds the second passage of a multi-hop question without another search, and the published comparisons (GraphRAG-Bench, ICLR 2026) show it to be the strongest graph method at the query cost of plain retrieval. It needs no ontology, so a hop the ontology has no term for still exists. Measured on the sample's 23 multi-document questions: every expected document found for 11 of 23 against 7 for vector search; as an arm, 16 passes against the passage arm's 12 and Onyx's 19, with 11 of 12 multi-hop passes against 8 and 12. The typed graph stays the layer a precise question is answered from; this is the floor under it.

### In review: caching, neighbours and fusion (#123)

The agent's model carries strands' cache configuration on both providers, marking the system prompt, the tool definitions and the last user message as cache points. `related_passages` returns each hit with the passage before and after it, and fuses the walk's ranking with the vectors' own by reciprocal rank.

Why: the walk arm found the right documents but spent 190,000 input tokens a question resending its growing context, and trailed Onyx on completeness, which hands the model each hit's neighbouring chunks. Built without spend; the effect on cost and completeness is the next measurement.

## What the period changed for a deployment

A deployment runs a pinned release. The lab that consumes Knowledge Store is pinned at 0.8.0, so it has the passage arm's vectors and none of the unreleased work. The next release will carry the stop rule, which changes the agent's defaults (searches, tools, reserved calls, output tokens) and so the agent image, and the walk, which changes the tools Lambda and the image but reaches no deployment until `agent.passage_toolset` is set and `facts` and `walk` have run for its collections.

## Lessons the period left

- Read the step traces before changing a rule: the budget failures had one cause visible in every trace, and a pull request was spent reordering valves before it was read.
- Measure a competitor's cost from its own ledger, early, not from an estimate; the Onyx estimate was three and a half times low.
- The harness's score is for the agent's own output; a recorded answer has no abstention flag, so systems are compared on the grader's verdicts.
- A search cap turns errors into declines; declines of answerable questions must be counted beside errors.
- The walk's defaults from the paper (passage weight 0.05) were not the best here (1.0); a no-cost retrieval sweep before any paid run is the cheapest experiment there is.
- Formatting a Terraform file by hand without the binary left `main` red for a day; the fix is one line, the lesson is to run the formatter or say so in the pull request.
