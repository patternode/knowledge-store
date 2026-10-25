# Handover: EnterpriseRAG baselines, the Knowledge Store passage arm against Onyx

Written 25 October 2026, afternoon NZDT, for the session that takes this work over.
In the knowledge-store repository this file is `docs/_handover-2026-10-25-baselines.md`.
The leading underscore keeps it off the documentation site.
It follows `docs/_handover-2026-10-24-enterprise-rag.md`, which covers the corpus, the literal conformance and the measures ontology.

## What the user asked for

Dermot wants the Knowledge Store pipeline to be at least as good as Onyx on the EnterpriseRAG-Bench slice, borrowing from Onyx where it helps.
The comparison runs in stages. This handover closes the first: Onyx (self-hosted community edition) against Knowledge Store with passage search only (the vector arm, no graph and no ontology), on the same 120 questions, graded by the same DeepEval judge.
The next stage adds the knowledge graph and the ontology and compares again.
A hard budget covered this stage: 50 dollars at first, raised by Dermot to 75, 90 and finally 110. The stage closed at about 110. It passed the 90 line once, because the guard priced an Onyx answer at 0.06 dollars and the real figure, read from Onyx's own usage table during the run, was 0.21 for lookups and 0.25 for the harder questions; the run was stopped at 60 answers as soon as that was known, and the other 60 ran on the 110 budget.

## Results

Both systems answered the same 120-question sample with Claude Sonnet 4.5 and were graded by the same judge (Claude Haiku 4.5, DeepEval: correctness against the gold answer, completeness against the answer facts, faithfulness against the cited documents).
Compare them on the grader's verdicts and metrics. The harness's own score is not comparable across the two: for Knowledge Store it folds in the agent's abstention flag and claim checks, which recorded answers do not carry, so for Onyx it counts any answer that cited an expected source as correct and counts every unanswerable question as a false answer. Read, all five of Onyx's answers to unanswerable questions do decline ("I cannot find a document that..."), with the related documents it searched cited beside the refusal. The grader passed four of them.

### Head to head, all 120 questions

| Measure | Knowledge Store, passage arm | Onyx 4.9.4 CE |
|---|---|---|
| Grader verdicts | pass 94, partial 10, fail 1, error 13, skipped 2 | pass 106, partial 10, fail 4 |
| Correctness (G-Eval mean) | 0.754 | 0.802 |
| Completeness (facts stated, mean) | 0.887 | 0.896 |
| Faithfulness (mean) | 0.973 | 0.962 |
| Cited an expected source | 0.99 (precision 0.912, recall 0.928) | 0.904 (precision 0.885, recall 0.88) |
| Grounded claims (the agent's own citation checks) | 0.996 | not measured for recorded answers |
| Unanswerable questions (5) | 2 declined, 3 errors (kept searching until the call budget ran out) | 5 declined in words, grader pass 4 and fail 1 |
| Errors | 13: eleven call budgets spent before an answer, two answers without structured output | 0 |
| Input tokens a question | about 120,000 (14,319,712 in, 186,028 out), no caching | about 72,000 (8,984,828 in, 112,952 out over 124 answers, from Onyx's `user_usage` table) |
| Model cost a question | about 0.25 dollars | about 0.23 dollars: 0.21 on the lookups, 0.25 on the rest |

### By kind, grader verdicts and metrics

| Kind (n) | Knowledge Store verdicts | Onyx verdicts | Correctness KS / Onyx | Completeness KS / Onyx | Faithfulness KS / Onyx |
|---|---|---|---|---|---|
| lookup (90) | pass 77, partial 6, fail 1, error 6 | pass 80, partial 8, fail 2 | 0.782 / 0.818 | 0.906 / 0.914 | 0.98 / 0.962 |
| multi-hop (20) | pass 16, partial 4 | pass 20 | 0.63 / 0.83 | 0.80 / 0.90 | 0.941 / 0.958 |
| list (5) | pass 1, error 4 | pass 2, partial 2, fail 1 | 0.9 / 0.4 (KS on its one answer) | 1.0 / 0.54 | 1.0 / 0.951 |
| unanswerable (5) | declined 2, error 3 | declined 5 | | | |

Reading. Onyx is ahead, and the gap is almost all Knowledge Store's own stop rule rather than retrieval. Thirteen of its 120 questions produced no answer because the agent spent its call budget searching (six lookups, four of the five list questions, three of the five unanswerable), and where it did answer its faithfulness and citation hit rate are the higher of the two. Onyx's lead on multi-hop (20 of 20 passed against 16, correctness 0.83 against 0.63) is real and is the part worth studying: its one-shot answer over about 40 retrieved sections sees the hops together, where the passage agent gathers them over several tool calls and its context grows with each. On lookups the two are within noise (80 against 77 passes of 90). On the list questions Onyx answered all five but completed about half the items; Knowledge Store answered one, fully. Knowledge Store never stated a fact for an unanswerable question; Onyx never did either, in words, though it cites documents while declining, which a citation-based scorer reads as an answer.
Onyx spends its tokens in several steps a question: `select_sections_for_expansion` (3.79 million input tokens over the run), `classify_section_relevance` (2.56 million), `chat_response` (2.37 million), with query rephrasing and time-filter extraction small. Knowledge Store's agent makes several tool calls and resends the growing context each time, which is where its 120,000 tokens go; its lookups cost 0.25 dollars and its multi-hop and list questions about 0.42.

The Knowledge Store report is `enterprise-rag-bench-sample120` run 2026-10-25T00:31:03Z, merged from four lanes and two retry lanes with `examples/enterprise-rag-bench/merge_reports.py`. The Onyx report is the merge of two graded halves (60 lookups on the first host, the other 60 on a second host that resumed from the saved answers).

## Where everything is

| Thing | Where |
|---|---|
| Passage arm code | knowledge-store `main` since pull request #117, released as v0.8.0 (the release pull request #116 is titled 0.7.1 but the tag is v0.8.0). `knowledge-store embed` writes `silver/vectors/passages.jsonl` with Titan Text Embeddings V2; `LocalVectorSearch` serves `search_passages`; `--tools passages` runs the agent with `search_passages` and `read_passages` only |
| Lab pin | patternode-platform `deployments/knowledge-store/main.tf` `ref=v0.8.0`, pull request #589, merged into `develop`. The phase-two pull request (`agent.runtime = true`, after the master session confirms the v0.8.0 agent image is in ECR) is not opened yet. Dermot applies |
| The slice and the sets | `examples/enterprise-rag-bench/fetch.py` writes the 722 documents, `documents.jsonl` and the 490-question set into `examples/enterprise-rag-bench/data/` (gitignored). The 120-question sample is `sample-120-ids.json` beside the README: 90 lookup, 20 multi-hop, 5 list, 5 unanswerable, drawn with seed 42 |
| Onyx baseline | `examples/enterprise-rag-bench/onyx/`: `launch.py` and `launch.json` start the host, `boot.sh` is its user data, `onyx_baseline.py` runs on it, `watch.py` follows it from here |
| Reports | `examples/enterprise-rag-bench/results/2026-10-25/`: the Knowledge Store report on the 120 (`ks-passages-120.md`), the Onyx report on the 120 (`onyx-120.md`) and Onyx's answers (`onyx-answers-120.jsonl`; the fictitious `redwood.com` and `redwood.ai` addresses in some answers were changed to `example.com` for the prepublish check). The full `results.json` files stayed on the session VM |
| Diagram of the two arms | Artifact https://claude.ai/artifact/Ap87KUg1V7wf6i3PWfSam7 |

## Procedure: the Knowledge Store passage arm

A local lake is enough; the live lab was not used.

1. Fetch the slice: `python examples/enterprise-rag-bench/fetch.py` (collection `enterprise-rag`).
2. Build a lake at `<lake>` and register the collection, which a local lake lacks until something writes it: `put_json(root, collections.CONFIG, [{"id": "enterprise-rag"}])`. Upload the 722 documents and run the sweep so the silver text exists.
3. Make a copy of the set whose sources carry the lake's document names (`dsid_<id>__<slug>.txt`), because the set names its sources by the benchmark's paths. The `--only` flag takes ids, so the sample is the 120 ids.
4. Embed: `knowledge-store -c enterprise-rag embed` with three workers. Titan throttles at eight; the embedder retries adaptively.
5. Evaluate in lanes of 30 ids each, every lane its own `--out`, as background jobs the session tracks (below):

   ```bash
   LLM_PROVIDER=anthropic ANTHROPIC_API_KEY=... python -m knowledge_store.apps.evaluate <set.lake.yaml> --lake <lake> \
     --model us.anthropic.claude-sonnet-4-5-20250929-v1:0 --tools passages --runner deepeval --grader deepeval \
     --judge-model us.anthropic.claude-haiku-4-5-20251001-v1:0 --only <ids> --out <dir> --yes
   ```

6. Merge the lanes and retries: `python examples/enterprise-rag-bench/merge_reports.py merge <lane dirs> --out <dir>` keeps one row an id, preferring a row without an error. `compare` prints the two systems side by side.

## Procedure: the Onyx baseline

Onyx runs on one EC2 host (m7i.2xlarge, 0.408 dollars an hour) in the labs account, with an instance role for S3 and Bedrock and no secret on the host.

1. `python launch.py` reads `launch.json` and starts the host with `boot.sh` as user data, the bucket substituted in. The committed `launch.json` holds placeholders: fill it from the labs account (its default VPC and a public subnet, a security group with no inbound rule, the current Amazon Linux 2023 AMI, the `onyx-erb-baseline` instance profile, which may read the bucket and call Bedrock, and the bucket with its `input/`, `runner/`, `control/` and `output/` prefixes). It writes `instance.json`.
2. `boot.sh` installs Onyx 4.9.4 with the official installer, then switches the deployment to Standard: the installer's non-interactive default is Lite, which has no vector index and cannot search. It sets `vm.max_map_count`, waits for health, adds the placeholder connector (below), pulls the slice and the sample from `s3://<bucket>/input/`, and runs `onyx_baseline.py` with Bedrock in us-west-2. Logs ship to `s3://<bucket>/output/` every minute.
3. `onyx_baseline.py` registers `admin@example.com`, adds a Bedrock provider by region only (so the instance role is used), ingests the 1,438 slice files through `/api/onyx-api/ingestion`, waits for indexing, finds the search tool in `/api/tool` and forces it on every question (`forced_tool_id`), probes the first question and stops with status `no-retrieval` if no document came back, then asks the 120 questions through `/api/chat/send-chat-message`. It writes `onyx-answers.jsonl` with `question_id`, `answer`, `document_ids` (the citations, else the top five retrieved), `cited_ids`, `retrieved_ids` and `tool_calls`, and uploads it every ten answers.
4. The control channel is `s3://<bucket>/control/command`: `stop` shuts the host down (it terminates on shutdown), `sh` runs `control/run.sh` as root. The host cannot delete objects, so it clears the command by writing an empty one. Everything on the host was diagnosed and fixed through this channel.
5. Grade the answers with the same judge, on the original sample set whose sources are the benchmark's paths:

   ```bash
   LLM_PROVIDER=anthropic ANTHROPIC_API_KEY=... python -m knowledge_store.apps.evaluate <set.sample.yaml> \
     --answers onyx-answers.jsonl --answers-index data/documents.jsonl --documents data/documents \
     --runner deepeval --grader deepeval --judge-model us.anthropic.claude-haiku-4-5-20251001-v1:0 --out <dir> --yes
   ```

6. Write `stop` to the control channel. Check the instance is gone.

## Lessons

- Onyx's search tool is hidden and skipped unless a connector other than the built-in ingestion connector exists. `SearchTool.is_available` requires a connector with id above 0; documents sent through the ingestion API land on connector 0, so `/api/tool` listed no search tool, chat never searched, and the first full run answered from the model alone. The fix is one inert connector row (no connector-credential pair, so nothing indexes), now in `boot.sh`. Making the user an admin was not the cause, though the first-user promotion did not apply either.
- The Onyx installer's non-interactive default is Lite. Standard is `docker compose -p onyx -f docker-compose.yml up -d` in `/opt/onyx/deployment`, and OpenSearch needs `vm.max_map_count` raised.
- Bedrock's "Too many tokens per day" in the labs account is a rolling window per region. us-east-1 was exhausted; us-west-2 still served. There is no adjustable daily-token quota row for Sonnet 4.5 in Service Quotas, so a support case is the route; its text was given to Dermot. Knowledge Store moved to the Anthropic API (`LLM_PROVIDER=anthropic`) for the rest of the run. The API's workspace credits ran out once mid-run, Dermot bought more, and 21 questions were retried.
- Two fixes that came out of this are in v0.8.0: the local agent now follows `LLM_PROVIDER` (it used to build a Bedrock model regardless), and the Anthropic SDK 1.17 no longer takes `temperature` or `top_p` on `messages.stream`, so the model client sends them only when the SDK's signature has them.
- In a cloud session only jobs the session tracks (`run_in_background`) survive idle time. Plain `nohup` lanes were killed with the session and 94 answers were lost once. Every lane and the budget guard ran as tracked jobs after that.
- A `pkill -f` pattern that appears in the killing command's own line kills the killer. Build the pattern with `printf`.
- Stale `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` with leading spaces sat in the environment; every AWS command ran with `env -u` for both and `AWS_PROFILE=labs`.
- The set's collection name must match the lake's (`enterprise-rag`, not `redwood`), and a local lake has no collections registry until one is written.
- The harness's score is for the agent's own output. A recorded answer has no abstention flag and no claim checks, so `--answers` runs should be compared on the grader's verdicts and metrics, and an abstention that cites the documents it searched reads as a false answer. Either give `FileAnswerer` an abstention heuristic or report the grader only for recorded answers.
- Measure, do not estimate, the cost of a system you do not know. Onyx's `user_usage` table (`model`, `flow`, `input_tokens`, `output_tokens`) gave the real figure in one query through the control channel; had it been read after the first ten answers the run would have stopped inside the cap, or been sized to it.
- A budget guard that counts spend from report files must count only the lanes still running and must take two readings over the stop line before stopping; the first version counted merged reports as new spend and stopped the Onyx host twice for nothing.
- The classifier in this session refused to copy the Anthropic key to the Onyx host through S3, and that refusal stands: the host stays on Bedrock through its instance role.

## Costs

| Item | Measured |
|---|---|
| Knowledge Store passage arm, a lookup question | about 0.25 dollars (Sonnet 4.5, no caching) |
| Knowledge Store passage arm, a multi-hop or list question | about 0.42 dollars |
| Grading, a question | about 0.01 dollars (Haiku 4.5) |
| Onyx, a question | about 0.23 dollars: 0.21 on lookups, 0.25 on multi-hop, list and unanswerable (about 72,000 input and 910 output tokens, Sonnet 4.5 on Bedrock, measured from its `user_usage` table) |
| Extraction for the graph arm | about 0.11 dollars a document, so about 80 dollars for the 722 |
| EC2 for Onyx | 0.408 dollars an hour; the two hosts that answered ran 1.3 hours each (install, Standard switch, ingestion and indexing take about 45 minutes before the first question). Two earlier hosts, stopped by the guard's false readings, are in the 79 dollars below |
| Whole stage | about 110 dollars against the final 110 cap: 79 up to 01:05 UTC (the Knowledge Store arm, the embeddings, the earlier Onyx hosts), 13.6 for Onyx's first 64 Bedrock answers, 15.1 for the other 60, 1.1 of EC2 and about 1.2 of grading |

## What is left

In this order.

1. The phase-two platform pull request: set `agent.runtime = true` in `deployments/knowledge-store/main.tf` once `master: patternode-platform` says the v0.8.0 agent image is in ECR. Then the master session promotes `deploy` and Dermot applies.
2. Multi-hop. Onyx passed all 20 and Knowledge Store 16, with correctness 0.83 against 0.63. Read the four partial answers against Onyx's, then try one change at a time: a wider first retrieval (Onyx hands the model about 40 sections at once), a `read_document` tool so the agent sees a whole document when a passage is a fragment, and prompt caching so the growing context stops being the cost.
3. The stop rule. Eleven of the thirteen Knowledge Store errors were a spent call budget: six lookups, four of the five list questions and three of the five unanswerable. The agent should decline after a bounded number of empty searches and answer with what it has when the budget nears its end; the list questions need a tool that lists by keyword or reads a whole document. Re-run the 30 non-lookup questions after the change. This alone closes most of the gap to Onyx.
4. Cost. Prompt caching on the system prompt and the tool results, and a measurement of tokens a question before and after, before any 722-document run.
5. The graph arm: extract the 722 documents (about 80 dollars), write a graph-shaped question set (the benchmark's questions are passage-shaped), run `--tools all`, and compare against both baselines on the same judge.
6. Onyx with its own knowledge graph beta switched on, as the fourth arm, if the graph arm shows a gap worth chasing.
7. Evaluation in CI: the full set and the judge run on every change to answering, with the online judge dialled down as confidence grows. DeepEval is the runner and grader; promptfoo is not needed now.

## Rules the next session must keep

- Conventional Commits. Knowledge-store commits use `git commit -s`.
- No em dash as sentence punctuation. No bold inside a sentence.
- Do not name an employer, and do not raise employment consent.
- Dermot manages keys. Give the command and stop. Do not copy a key to another host.
- Only Dermot changes a guardrail. Do not put GIFS code in this repository.
- Other sessions never merge, promote or deploy. Platform pull requests go to `master: patternode-platform`; knowledge-store merges are Dermot's.
- A hard budget is a hard budget: run a guard as a tracked job and stop before the cap.
