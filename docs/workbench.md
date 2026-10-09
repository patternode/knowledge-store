# The workbench

The chat page opens as the chat alone, which is how someone asking a question sees it. Demonstrate, in the header, shows the other two parts, and User view hides them again. The choice is remembered in that browser. On the left are sample questions, grouped low, medium and high, from the collection's profile. In the middle is the chat: ask, get an answer built from checked claims, with every statement linked to its passage. On the right is a workbench for the people who look after the collection. There they can watch what the agent does, find out why a question went unanswered, see what the question cost, and see which parts of the ontology the questions actually use.

Everything here is in this repository and needs no settings. A deployment gets it by moving its module pin to a release that has it.

## Watching the agent work

Every question records its steps as they happen:

| Step | What it says |
|---|---|
| tool | The tool call and its arguments, in words ("Searched entities for "Voyager" of type Mission: 3 found"), what came back, the ontology terms it touched and how long it took. Open the input to see the exact arguments. That input is labeled Knowledge graph query for an entity, neighbourhood or path lookup, Vector query when a passage search used the knowledge base, and Keyword passage search when it searched the stored text. |
| model | A model call: the agent deciding what to do next. The line under it is how long that call thought, the tokens it reported (input, output, cache write, cache read, including zeros), and its list price. |
| check | The cited passages being read back and every quote checked against them. |
| repair | Citations that failed, sent back to the agent once to fix. |
| guardrail | The Bedrock Guardrail declining the question, or removing a claim it found ungrounded. |
| done, error | How it ended: claims shown and sources, an abstention and what was missing, or why it stopped. |

How the steps reach the page:

1. The chat API answers asynchronously (API Gateway allows 30 seconds, and a long question takes longer). The page polls `GET /api/chat` every 1.5 seconds.
2. The portal asks the agent on AgentCore Runtime with `"stream": true`. The agent runs the question in a thread and sends each step as a server-sent event as it is recorded, then the result.
3. The portal writes the steps so far into the pending answer in the chat table, at most once a second, so a poll shows them. Without the agent, the portal's own tool loop records the same steps.
4. The workbench shows the selected question's steps live. Inline, the pending answer shows the latest step and the time so far.

The steps answer the question a long wait raises: is it stuck, searching for the wrong type, reading the wrong documents, or failing its citations? Each step is coloured by its type: model thinking, a knowledge graph query, a vector query, a keyword search, a passage read, an ontology read, a check, a repair, the guardrail, any other tool, and how it finished. Under the list, every one of those types is counted, including the ones this question did not use, then each tool by how many times it was called, then the tokens across the model calls. The cost by path charges each model call to the paths of the tools that followed it, split evenly when one call used several, and charges a model call with no tool after it to the answer. The answer itself is repeated under that table. The step budget (`valves`) is visible too: a question that hits `max_tool_calls` shows it. The portal's own loop stops after 10 model rounds. The agent stops after `max_model_calls` (14) and refuses further tools after `max_tool_calls` (16).

## What the question cost

A finished question shows its list price in the workbench, split two ways:

- By token kind: input, output, cache write and cache read, with the token count beside the price.
- By model call: each Thinking step carries that call's own price, and the cost section lists them again.

The price is the list price in `ledger.py` (Bedrock regional inference includes the 10% premium). Searches and passage reads are not charged. A guardrail check is named when one ran, and is not in the price. Credits, discounts and tax are not included. A question that reported no token use says so, rather than showing zero.

## What would it take?

A finished answer offers "What would it take to answer this?". It is the main offer when the agent could not answer, or answered with nothing checked. The same mode is in the question box ("What would it take?") for a question you expect to fail.

That mode runs an analyst rather than the chat agent. It has the same tools, the same ontology and the same scope as the person asking. It gets the question and what the chat agent said and tried. It explores the graph and passages, then reports:

| Part | Meaning |
|---|---|
| Verdict | `answerable` (it can be answered now, and how), `extraction_missed` (a passage states it but the graph lacks it), `ontology_missing` (no type, relation or attribute can hold it), `data_missing` (no document covers it) or `out_of_scope` |
| Ontology to add | Classes (with a parent from the ontology), relations (domain and range) and attributes (domain and datatype), each with a definition and why the question needs it |
| Already in the ontology | Terms that would carry the answer, so nothing is proposed twice under another name |
| Data to add | The documents or kinds of source that would have to be added |
| Missing from the graph | Facts a passage states that extraction did not capture, with the passage id |
| Questions it can answer now | Close questions the graph answers today. Selecting one puts it in the question box. |

The analyst changes nothing. A curator (a person with private access) can keep the report as an ontology request. It is stored in the collection's lake under `ontology/requests/`, which is the one place the portal writes to the lake. Requests show in the ontology page's Requests tab. How a kept request becomes part of a later ontology version, and how the ontology was derived in the first place, is in [How an ontology is derived](../README.md#how-an-ontology-is-derived).

Requests join the ontology lifecycle through the candidate register. `knowledge-store candidates` lists each requested term with `asked` (how many requests asked for it) beside `docs` (how many documents extraction found it in). `knowledge-store candidates --propose` considers a requested term even when no document has used it yet, because a person asked for it, and the draft still waits for a curator to publish it. Questions are untrusted input just as document text is, so nothing reaches the ontology without a person publishing it.

## Which parts of the ontology get used

Every answered question records the ontology terms it touched, at three levels:

| Level | Meaning |
|---|---|
| asked for | The agent searched by the term: a type given to `search_entities` or `list_entities` |
| read | The term came back in what the agent read: an entity's types, the relations and attributes of its facts, the relations along a neighbourhood or a path |
| cited | A fact of that term is stated in a passage the answer cites |

The workbench shows these terms for the selected answer, and the totals for this browser session. The ontology page has a question overlay with three windows: all time, this month and this session. It draws a ring round each class, as thick as its share of the most used class, with the number of questions that used it. Relations that questions used are drawn bright. Classes no question used are faded. The side panel lists the most used classes and the populated classes no question has reached, and adds a Questions column (cited in brackets) to the properties.

### Session or all questions: what the numbers can and cannot say

A session's numbers are mostly noise: one person's dozen questions, shaped by what they happened to be curious about that hour. They are useful for one thing, seeing what your own questions just did, so they stay in the browser (sessionStorage) and nowhere else.

The totals that help refine an ontology are across all questions and people, so those are kept on the server. They are counters in the chat table, one row per collection for all time and one per month, added to atomically once per answered question. They hold term names and counts only, never the question or who asked, so they are shown to every reader. "What would it take?" runs are not counted: they explore on purpose, which would inflate the terms they look at.

Read them with three caveats:

- They count what people ask about, not what the ontology does well. A class nobody asks about may still be needed (the questions have not come yet), and a much-used class may answer badly. "Read" without "cited" is the signal to look at: the agent went there and found nothing it could use.
- They follow names across versions. A term renamed in a new ontology version starts again from zero, and the old name keeps its count.
- The strongest refinement signal is not in these numbers. It is in the requests: terms people needed that the ontology does not have. The usage totals tell you where the ontology is exercised. The requests tell you where it falls short.

## API

| Route | |
|---|---|
| `POST /api/chat` `{question, history, mode, about}` | `mode` is `ask` (the default) or `gaps`. `about` (for `gaps`) carries the chat agent's answer, its gaps and the titles of its steps. |
| `GET /api/chat?id=` | `status` is `pending`, `running` (with `steps` so far), `done` or `failed`. A finished answer adds `steps` and `ontology_hits`; a `gaps` run has `report` in place of an answer. |
| `GET /api/usage?window=all\|month` | `{questions, classes, relations, attributes}`, each term with its `queried`, `read` and `cited` counts |
| `GET /api/requests`, `POST /api/requests` `{question, report, ontology_version}` | The kept requests, newest first, and keeping one. For people with private access only, because reports quote questions and passages. |

The code is in `src/knowledge_store/workbench.py` (steps, terms, counters, requests and the analyst's prompt and schema), `agent/app.py` (`analyse`, streaming), `portal_api/handler.py` and `portal_api/chat.py`, and in the chat page's `app.js` and `ontology.js`.
