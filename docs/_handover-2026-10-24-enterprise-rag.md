# Handover: enterprise RAG collection, literal conformance, and the measures ontology

Written 24 October 2026, early morning NZDT, for the session that takes this work over.
In the knowledge-store repository this file is `docs/_handover-2026-10-24-enterprise-rag.md`.
The leading underscore keeps it off the documentation site, which treats the whole repository as its page tree and excludes `**/_*.md`.
On the platform branch the same text is `deployments/knowledge-store/handover-2026-10-24.md`.

Two repositories. Architecture decisions stay in patternode-architecture. This work did not add an ADR there.

| Repository | Checkout on this machine | Branch | Remote |
|---|---|---|---|
| patternode/knowledge-store | `/tmp/knowledge-store` | `cursor/conform-literals-9e3d` | Pushed on 24 October 2026 by the session that took this over. Pull request patternode/knowledge-store#111 into `main`. Base is `main` at `36f56d2` (`chore(main): release 0.5.0`). |
| patternode/patternode-platform | `/workspace` | `cursor/enterprise-rag-bench-9e3d` | Already on origin. Pull request [patternode/patternode-platform#579](https://github.com/patternode/patternode-platform/pull/579) into `develop`. |

The knowledge-store commits were mirrored as branches on patternode-platform so they were not stuck on this machine. They are the knowledge-store tree, not platform code. Do not open a pull request from either mirror into `develop`. The conformer mirror has been pushed back to knowledge-store and is in the pull request above; the mirror branch can be deleted once that pull request merges.

| Mirror branch on patternode-platform | Knowledge-store branch it carries |
|---|---|
| `cursor/ks-conform-literals-9e3d` | `cursor/conform-literals-9e3d` |
| `cursor/ks-deepeval-grader-9e3d` | `cursor/deepeval-grader-9e3d` |

To put them back on knowledge-store, from a clone whose credentials can push there:

```bash
git fetch https://github.com/patternode/patternode-platform.git \
  cursor/ks-conform-literals-9e3d:cursor/conform-literals-9e3d
git push origin cursor/conform-literals-9e3d
git fetch https://github.com/patternode/patternode-platform.git \
  cursor/ks-deepeval-grader-9e3d:cursor/deepeval-grader-9e3d
git push origin cursor/deepeval-grader-9e3d
```

The commit hashes are the same as on this machine. A copy of this handover is also on the platform pull request branch, under `deployments/knowledge-store/handover-2026-10-24.md`.

A second knowledge-store branch, `cursor/deepeval-grader-9e3d`, is one commit on the same `main` and is not part of the ontology line. It is described at the end.

## What the user asked for, in order

The session that produced this work was asked, in this order:

1. Conform dates, times and numbers in document text before chunking, using standards, and only where the reading is unambiguous.
2. Keep going through the literal families that showed up in the 722 cited EnterpriseRAG documents: phones and parenthetical amounts, time periods, punctuation and identifiers, information sizes.
3. Split the conformer into one module per family.
4. Parse unmapped CSV and TSV as rows, and keep PDF pages apart.
5. Fix row-label clashes and blank PDF pages.
6. Consider ontology classes for number, metric and time, built from standards, so a domain ontology can be built up from them.
7. Apply that to the space-missions sample. This was rejected. The user said none of the existing ontologies are the base, and a new one is needed.
8. Add the measures ontology as that base.
9. Say which AWS credentials this cloud agent needs, and how they get into this environment.
10. Say what is next, whether more code is left, and whether every pipeline stage including knowledge-graph extraction is implemented.
11. Say how the enterprise RAG ontology will be derived.
12. Commit the work on feature branches and write this handover.

## Decisions that are settled

Do not reopen these unless the user does.

Numbers and times are value kinds, not superclasses of domain concepts. A company is a company. Its revenue is a quantity. A launch day is an instant. Domain classes do not subclass `kv:` kinds or `km:Metric`, `km:Quantity`, `km:Instant`, `km:Period` to mean "this thing is a number" or "this thing is a time".

Two layers, on purpose:

| Layer | Namespace | Prefix | Role |
|---|---|---|---|
| Value kinds | `https://w3id.org/knowledge-store/values#` | `kv:` | The shape of a literal. Datatypes and the `kv:unit` annotation. |
| Measures | `https://w3id.org/knowledge-store/measures#` | `km:` | Four classes a domain ontology imports and points at. |
| Core | `https://w3id.org/knowledge-store/core#` | `ks:` | Where a fact came from. Unchanged by this work. |
| Domain | The collection's own base | | What the documents are about. Not written yet for enterprise RAG. |

Value kinds, in `docs/values-vocabulary.md` and `src/knowledge_store/ontology/domain/values.ttl`:

| Kind | Stored form | Left as a string |
|---|---|---|
| Day | `xsd:date`, `2023-07-14` | A numeric date that could be day-first or month-first |
| Clock | `xsd:dateTime` | A clock with no am/pm, zone, or hour of 13 or more, unless a date or the other end of a range fixes it |
| Duration | `xsd:duration`, `PT2H`, `P3D` | A business day, because the length is not fixed |
| Interval | `kv:interval`, `2023-07-14/2023-07-20` | A quarter, a fiscal year, a half, a bare year |
| Quantity | `xsd:decimal` or `xsd:integer`, plus `kv:unit` | A unit that is not the same on every value of that attribute |

`kv:unit` is an annotation, so every value of that attribute shares the unit. A QUDT unit IRI is used when one is exact. Alignment is to XML Schema, ISO 8601, OWL-Time and QUDT. The graphs of QUDT and OWL-Time are not copied in.

Measures, in `docs/measures-ontology.md` and `src/knowledge_store/ontology/domain/measures.ttl`, version `1.0.0`:

| Class | Meaning | `rdfs:seeAlso` |
|---|---|---|
| `km:Metric` | A defined measure. Revenue is a metric. 1200 USD is not. | QUDT QuantityKind |
| `km:Quantity` | One number, one unit, one metric. | QUDT Quantity |
| `km:Instant` | A point in time. A day and a clock time are different values. | OWL-Time Instant |
| `km:Period` | A stretch of time, with a start and an end, a duration, or both. | OWL-Time Interval |

Properties: `valueOf` (Quantity to Metric), `numericValue` (decimal), `unit` (anyURI), `during` (Quantity to Period), `at` (Quantity to Instant), `onDate` (date), `atTime` (dateTime), `beginning` and `end` (Period to Instant), `duration`, `interval` (`kv:interval`).

When to use which:

- A fixed-shape attribute stays an attribute. Always a day: `xsd:date`. Always US dollars: decimal plus `kv:unit`.
- A quantity is for a number whose metric or unit varies, or that belongs to a period.
- A quarter, fiscal year, half or bare year stays a string until the documents give it a start and an end. Then it is a Period.

The space-missions sample is not the base. A change that renamed `sampleCostMillionUsd` to `sampleCost`, added `cruiseDuration`, and bumped that ontology from `1.0.0` to `2.0.0` was committed and then reverted (`ee509eb`, then `b815296`). The sample catalog, its CSV column `sample_cost_million_usd`, and ontology version `1.0.0` are as they were on `main`. Do not retrofit Holmes, earnings, mortgage or missions to demonstrate the measures ontology.

One small leftover on the sample is intentional. `examples/space-missions/ontology/r2rml-mapping.ttl` gained the `kv:` prefix line, because `mapping.r2rml()` has emitted that prefix since the value-kinds commit and a test compares the file to the generator. The sample ontology itself was not changed.

A unit change on a property is a semantic diff, so it requires a major version and a full re-extraction. That rule stayed after the revert. It is in `src/knowledge_store/ontology/slices/versions.py`.

Code may know the measures file and IRI so it can merge an import. Code does not name Metric, Quantity, Instant or Period in business logic. Domain ontologies live in another namespace. `mine()` is namespace-scoped and rdflib does not follow `owl:imports`, so `model.load` parses the bundled `measures.ttl` when `owl:imports` starts with `https://w3id.org/knowledge-store/measures`. Nothing is fetched over the network. Loading `measures.ttl` itself does not parse itself a second time, because its import is the values vocabulary. If a domain file and the measures file both contain an `owl:Ontology` node, the loader keeps the domain file's version and namespace. A second class with the same local name and a different IRI is refused.

The writer drops a declared class whose canonical name is Metric, Quantity, Instant or Period. It keeps those names as a parent, domain or range. It emits `@prefix km:` and `owl:imports <https://w3id.org/knowledge-store/measures>` only when a domain term uses them. It does not copy measures terms back into the domain file. SHACL uses `sh:class km:Quantity` (and the other three) and does not regenerate shapes for measures properties.

Review can set a domain or range to a measures class without that class being in the draft. `set_parent` onto a measures class is not special-cased. The measures document says not to subclass them.

Discovery's consolidate prompt (`DEFINE_SYSTEM` in `src/knowledge_store/ontology/slices/discover.py`) tells the model that the four classes already exist, to use them as a domain or a range, and not to declare them again. The propose prompt was not changed. It still asks for general types. The datatype list is string, decimal, integer, date, dateTime, duration, interval, boolean, anyURI.

## Ingestion: what the silver text is

Bronze bytes stay as stored. Refine conforms the parsed text, then cuts passages. The conformer version is `conform@1`. Fenced code is left as written. Only unambiguous forms are rewritten. The order is the behaviour, because a later rule sees spans an earlier rule has claimed:

1. punctuation (quotes, dashes, ellipsis, ligatures fold to ASCII)
2. identifiers (http/https scheme and host, email domain, UUID case)
3. scientific numbers and exact fractions
4. periods (durations and intervals)
5. dates
6. clocks
7. information sizes
8. numbers (thousands separators, parenthetical losses)

Each family is a module under `src/knowledge_store/ingestion/domain/conform/`. `conform/__init__.py` only runs them. `kernel/values.py` is the shared reading of a number and a written date, also used for a table cell.

Rules that were pinned because the corpus would have been damaged without them:

- A phone number is not a list of numbers. Parentheses mark a loss only when the amount has a currency sign or a grouping separator. `(1.2%)` is not a negative number.
- A hyphenated range of numbers is rewritten on each side. A hyphenated tag stays (`A100-40GB`).
- An information size is a number and a symbol (`8 MB`, `10 MiB`, `256 B`). Decimal and binary prefixes are not converted into each other. A lowercase `b` stays, so a bit form stays. A bare `B` stays, because it also means a billion (`70B`).
- `UTF-8 bytes` stays. `100Gb` stays.
- A month written with its year is that month (`2023-07`). Milliseconds are decimal seconds.
- Words such as yes and no are not booleans.
- A decimal keeps its digits as written. `0.70` stays `0.70` and `3.10` stays `3.10`, because `Python 3.10` is a version as often as a number, and `1.0 -> 1` was changing `CUDA 12.0` and `Release 2.0` in the corpus. The rewrite only folds thousands separators, signs, currency spacing, percent words and parenthetical losses. A table cell's stored form (`kernel/values.py`, `canonical`) still drops trailing zeros, and comparisons are numeric, so `1200.50` in a passage and `1200.5` in a cell are equal. Changed on 24 October 2026 by the session that took this over, after running the conformer over the 722 documents.

Unmapped CSV and TSV (`table@1`, `ingestion/domain/delimited.py`): a mapped table is bound later and is never refined as prose. A file no mapping names becomes one line per data row, `column: value | column: value`. The first row is the header. A column named title wins over one named name. A repeated header gets a distinct label (`name`, `name (2)`). A blank header becomes `column N`. A cell that contains the row separator is written with a slash, so a later split stays on the real cell boundary. Empty rows are dropped. Extra cells past the header become `column N`.

PDF (`pdf@1`): one part per page. Blank pages are dropped before silver is written. Each kept page is conformed and packed on its own, so a passage never joins the next page. A PDF with no text layer raises `UnsupportedFormat`. OCR is not built. The size cap for PDF is 100 MB. Other formats are 20 MB.

Chunking: markdown and HTML cut on headings and fences. A table packs one row at a time, and a row longer than the cap breaks between cells. Every other parser packs paragraphs.

The 722-document check is `tests/ingestion/unit/test_conform_corpus.py`. It runs only when `ENTERPRISE_RAG_DOCUMENTS` points at the documents directory. The knowledge-store checkout does not contain that corpus. The platform checkout does: `/workspace/deployments/knowledge-store/corpora/enterprise-rag/documents/`. The test was written against that set. This handover turn did not re-run it, because the variable was not set in the suite below.

## How the enterprise RAG ontology will be derived

The collection is declared in patternode-platform `deployments/knowledge-store/main.tf`. Id `enterprise-rag`. `ontology_mode = "curated"`. No `ontology_dir`. Profile name Redwood Inference, the fictional company in EnterpriseRAG-Bench v1.0.0. Ontology base `https://example.org/knowledge-store/enterprise-rag/ontology#`.

That means the ontology is discovered from the documents, then published by a person. It is not a hand-authored file, and the sweep does not publish the draft itself. Missions is the opposite: it has `ontology_dir = "ontology/missions"` and the sweep publishes that file. Holmes has a profile and no ontology directory, same curated default as enterprise RAG.

The corpus on the platform branch is the 722 documents the 500 questions cite, under `deployments/knowledge-store/corpora/enterprise-rag/documents/`. Counts checked when that pull request was opened: confluence 214, jira 118, slack 79, github 65, google_drive 63, linear 60, gmail 58, hubspot 34, fireflies 31. Every `expected_doc_id` had a file. `questions.jsonl` stays in git and must not be uploaded: a file in `landing/` is ingested as a document, and that file holds the gold answers. The benchmark's other half-million documents are distractors for a retrieval score. They are not in the repository. Refining them, and extracting them after an ontology exists, is a different and much larger run.

Upload, only after this collection is on the applied deploy revision:

```powershell
Set-Location deployments/knowledge-store
$env:AWS_PROFILE = "earnings-lab"
aws s3 sync corpora/enterprise-rag/documents s3://<lake bucket>/landing/enterprise-rag/
```

The upload starts a sweep. One sweep at a time, via an S3 lock. The stages in `src/knowledge_store/apps/sweep.py` are implemented, including extraction and graph load: ingest, refine, discover or publish a provided ontology, extract, bind tables, candidate register, project, then load graph, documents, SPARQL and passages. A collection does not reach extraction without an active ontology.

With no active version and fewer than `discovery_min_docs` refined documents (default 5), status is `waiting_for_documents`. Once that bar is met, and there is no draft yet, discovery runs. Defaults, also the lab settings: sample 20, resamples 2, target about 15 classes, review on. Discovery reads a sample, so its cost is sample times resamples, not 722. Each sampled document contributes at most eight passages. The method is EDC (extract, define, canonicalise; Zhang and Soh, EMNLP 2024):

1. Propose types per document, each with a definition and verbatim passage examples. An example that is not in the cited passage is dropped.
2. Aggregate by normalised name. Stability is the share of resamples that proposed the term.
3. Consolidate into a small ontology: synonyms, a shallow hierarchy, domain and range, datatypes, about 15 classes, and a record of what was rejected.
4. Review. A second call returns edits only. Code applies the ones that are valid and records the rest as skipped.

The draft is `ontology/drafts/<id>/` as `ontology.ttl`, `shapes.ttl` and `report.json`. Status becomes `awaiting_curation`. Extraction does not run.

A person then curates it. Commands from `deployments/knowledge-store/ontology/README.md` and knowledge-store `docs/deploy/aws/README.md` section 12:

```bash
export LAKE_URI=s3://<lake bucket>
aws s3 ls $LAKE_URI/collections/enterprise-rag/ontology/drafts/
knowledge-store -c enterprise-rag ontology pull <draft id> ontology/enterprise-rag/
# edit ontology/enterprise-rag/ontology.ttl and set owl:versionInfo to "1.0.0"
knowledge-store -c enterprise-rag ontology diff ontology/enterprise-rag/
knowledge-store -c enterprise-rag ontology publish ontology/enterprise-rag/ --activate
```

Publishing starts extraction of every document against that version. The sweep then projects and loads Neptune, the SPARQL store and the passage index. Passage search is the Knowledge Base when `KNOWLEDGE_BASE_ID` is set, otherwise keyword search. Passage text stays in silver. The graph cites passage ids.

Fifteen classes is the lab-wide discovery target, and the platform README already says it is small for this corpus. The published `1.0.0` is the first usable core. After extraction, terms the ontology could not say are recorded as candidates and stay out of the graph. `knowledge-store -c enterprise-rag candidates --propose` sends those through consolidation again, with the current ontology in front of the model and an instruction to leave existing terms unchanged. A term is included when at least two documents named it, or a kept workbench request asked for it, and a synonym does not already cover it. That draft is a proposed minor version. If the proposal changes an existing term anyway, the report says so: publishing that change needs a major version and a full re-extraction. A person publishes it. In curated mode a term reaches the ontology only when someone publishes a version that contains it.

Version classes, from `versions.py`: descriptive is a patch and does not re-extract; additive is a minor and delta-extracts; a parent, domain, range or unit change is semantic and a major; a removal is a major. Both majors re-extract everything.

## What the live lab will not do until a release

The lab Terraform pin is `ref=v0.3.0` in `deployments/knowledge-store/main.tf`. The lab runs that tag only after it is on `deploy` and has been applied. Merging a pin does not deploy it. knowledge-store `main` moving does not change the lab.

`v0.3.0` does not contain this branch. On that image:

- The consolidate prompt does not know the measures ontology. A draft discovered there will not import `km:`.
- The conformer, `table@1` and per-page PDF packing are not in the image either.
- The extraction model and the chat model in this account are `us.anthropic.claude-sonnet-4-5-20250929-v1:0`. Bedrock in this account serves Sonnet 4.5, not Sonnet 5. That was checked 29 September 2026 and is commented in `main.tf`. Do not switch the id as part of taking this over.

The lab's AWS account (its id, the lake bucket and the state bucket are in platform `deployments/knowledge-store/main.tf` and its `backend.hcl`), region `us-east-1`, SSO profile `earnings-lab` (`aws sso login --profile earnings-lab`). Credentials come from the profile. No secret belongs in tfvars. Bedrock is IAM.

This cloud agent VM had no AWS CLI and no `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` or `AWS_SESSION_TOKEN` when last checked. On 24 October 2026 the next session found `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` set, but to the agent proxy's placeholders (a value starting `prox`), which AWS rejects (`InvalidClientTokenId`): a SigV4-signed request cannot have its key swapped by the proxy. The keys have to be ordinary environment variables of the agent, with `AWS_SESSION_TOKEN` when they come from SSO, and `AWS_REGION=us-east-1`. Nothing was uploaded. Dashboard secrets apply to the next agent, not to an agent that is already running. An `AWS_SESSION_TOKEN` exported from SSO expires. The user was told to put those three values in the environment secrets and start a new agent, and to set `AWS_REGION=us-east-1` in the agent. Do not create a new IAM user. Do not lecture about rotating or protecting a key. Give the command that sets it and stop.

Nothing has been uploaded to the lake in this work. No enterprise ontology has been authored or discovered. No `measures-v1.0.0` git tag exists, so the w3id version redirect for measures does not resolve yet. `docs/w3id/htaccess` and `docs/w3id/README.md` already describe `/measures` and `/measures/<semver>` the same way as core. Copying that `.htaccess` into perma-id/w3id.org is a separate pull request, and it should wait until the tag exists.

## Commits on `cursor/conform-literals-9e3d`

All times NZDT. All are on top of `36f56d2`. Signed-off-by is present. They are ordinary commits, not GPG-signed.

| Commit | When (NZDT) | What |
|---|---|---|
| `54940ef` | 23 Oct 2026, 10:58 | Conform dates, times and numbers before chunking. |
| `da3970a` | 23 Oct 2026, 12:15 | Keep phones and parenthetical amounts out of the number rules. |
| `db0a76e` | 23 Oct 2026, 12:27 | Conform unambiguous time periods to ISO 8601. |
| `e63fac4` | 23 Oct 2026, 12:33 | Fold punctuation and identifiers. |
| `8d9bf69` | 23 Oct 2026, 13:51 | Conform information sizes to one symbol. |
| `820bf57` | 23 Oct 2026, 14:07 | Split refine into conform, section and chunk modules. |
| `45f5ca9` | 23 Oct 2026, 14:37 | Read unmapped tables as rows and keep PDF pages apart. |
| `a0a3556` | 23 Oct 2026, 15:11 | Unique row labels, escaped separators, blank pages out of silver. |
| `b00796a` | 23 Oct 2026, 16:12 | Value kinds vocabulary. |
| `ee509eb` | 23 Oct 2026, 17:55 | Units on the space-missions sample. Rejected. |
| `b815296` | 23 Oct 2026, 17:59 | Revert that sample change. Keep the unit-is-semantic rule. |
| `5a1cfe5` | 23 Oct 2026, 18:02 | Measures ontology, loader, writer, review, discovery prompt. |

Documentation commits follow `5a1cfe5` and add this handover. Read the branch tip, not only the table above. The diff of the code against `main`, before those notes, is 53 files, about 3198 insertions and 92 deletions. The revert pair is in the history on purpose. Do not squash those two away locally. A squash merge of the pull request will fold them, which is fine: the tree at the tip does not contain the sample retrofit.

## Tests run for this handover

On 24 October 2026, from `/tmp/knowledge-store` with `PYTHONPATH=src`:

```bash
python3 -m pytest tests/ontology tests/ingestion tests/extraction \
  tests/kernel/unit/test_values.py tests/knowledge_graph/slices/test_table_query.py -q
```

Result: 734 passed, 12 skipped, in about 16 seconds. The skips include the 722-document corpus test, which needs `ENTERPRISE_RAG_DOCUMENTS`. rdflib deprecation warnings are existing noise, not failures. `python` is not on this VM. Use `python3`. `pyshacl` was installed earlier in the session (`pyshacl>=0.30`) after an import error. It was not missing on this run.

An earlier run of `tests/ontology tests/extraction tests/answering` after the measures commit reported 586 passed and 2 skipped. That command was not repeated for this handover.

On 24 October 2026 the session that took this over ran, from a fresh clone with a venv holding the core, `dev` test packages, `boto3`, `httpx` and `anthropic` but not `strands-agents`, `bedrock-agentcore` or `inspect-ai`:

- the whole suite with `--cov`, then `python tests/check_coverage.py`: 1866 passed, 39 skipped. Every context this branch touches is at or above its floor: ingestion/domain 100% (it was 93.6% before `test_conform_edges.py`), kernel 98.3%, knowledge_graph/slices 98.5%, platform_services/adapters 97.1%. answering/adapters, apps and evaluation/adapters read below floor in that venv only because their tests skip without `strands-agents`, `bedrock-agentcore`, `inspect-ai` and `transformers`; CI installs them
- the 722-document conformer check, `ENTERPRISE_RAG_DOCUMENTS` pointing at the corpus extracted from platform branch `cursor/enterprise-rag-bench-9e3d`: 1 passed, before and after the number-rule change
- `npm ci && npm run build`: the documentation site builds with no broken link
- a local lake (`knowledge-store --lake <dir> -c enterprise-rag ingest`, then `refine`) over the same 722 documents, with the lab's collection config written by hand under `collections/enterprise-rag/config/`: 722 stored, 722 refined, 3,152 passages (1 to 20 per document), none skipped. The conformer changed 669 of the 722: punctuation 9,360 rewrites in 516 documents, periods 2,764 in 535, dates 962 in 165, numbers 300 in 100 (before the trailing-zero change), trailing spaces 206 in 85, clocks 154 in 64, sizes 97 in 46. Discovery was not run locally: no model credential reaches this environment.

## Platform pull request 579

[patternode/patternode-platform#579](https://github.com/patternode/patternode-platform/pull/579), branch `cursor/enterprise-rag-bench-9e3d`, base `develop`.

| Commit | When (NZDT) | What |
|---|---|---|
| `c1b7da8a` | 23 Oct 2026, 10:32 | Add the enterprise-rag collection and the 722 documents. |
| `cf2261f5` | 24 Oct 2026, 12:56 | Skip Checkov CKV_TF_1 on the release-tag module pin. The pin is a tag on purpose. |
| `391a4b96` | 24 Oct 2026, 02:36 | Add this handover on the platform branch. |

The module source stays `ref=v0.3.0`. Moving the pin is a later change, after a knowledge-store release that contains this work.

The license of the corpus is MIT, Copyright (c) 2026 DanswerAI, Inc. The license file sits beside the corpus. The paper is arXiv:2605.05253.

## The other knowledge-store branch

`cursor/deepeval-grader-9e3d` at `92ec4ca`, 23 October 2026, 11:23 NZDT. One commit on `main`: `feat(evaluation): grade faithfulness with deepeval beside the score`. DeepEval's faithfulness metric judges an answer against the passages it used. The grade is reported next to the deterministic score and does not change it. It is not a release gate (the commit cites ADR-012). The `deepeval` extra pins 4.3.1 and stays out of `dev`, because the package ships pytest plugins. The judge calls Bedrock Converse with the run's model id. Files: `evaluation/adapters/deepeval_grader.py`, `apps/evaluate.py`, `evaluation/adapters/report.py`, tests, and the evaluation ABB and context pages. This branch does not contain the conformer or the measures ontology, and the conformer branch does not contain this grader. They can merge independently. This handover did not re-run the deepeval tests.

## What is left

In this order.

1. Done on 24 October 2026: `cursor/conform-literals-9e3d` is pushed to patternode/knowledge-store and is pull request patternode/knowledge-store#111 into `main`. The earlier note here said `develop`; that repository's `AGENTS.md` retired `develop` ("open nothing into `develop`"), its CI and Release Please follow `main`, and it has no `develop` branch, so `main` is the base. Do not open `cursor/ks-conform-literals-9e3d` as a pull request into patternode-platform `develop`: that branch is the knowledge-store tree. Platform pull request 579 is already into `develop` and stays the corpus change. The title is the changelog line after a squash. `feat` bumps the minor version. Release Please writes `pyproject.toml`, `__version__`, `.release-please-manifest.json` and `CHANGELOG.md` from pulls that reach `main`. Do not edit those by hand. The description must cite a reason: an issue, a thread, an improvement, an ADR, or a line `No reference:` and why. There is no IMP, issue or ADR for this work yet. Use `No reference:` and say the user asked for literal conformance and a measures ontology to build the enterprise RAG ontology on. Fill `.github/pull_request_template.md`. Say that deployments need a release before any of this runs, and that the agent image changes only if answering code changed. The value-kinds work touches `table_query.py` and renditions. The measures work does not change the chat agent. The conformer changes what silver text extraction will see once the pipeline image is rebuilt.
2. If the grader should ship, open that pull request into `main` as well. It is independent. Leave it until asked. Note that patternode/knowledge-store#110 (`cursor/deepeval-evaluation-framework-9469`, open into `main`) already proposes DeepEval as the evaluation framework with a runner and a model grader, so the grader branch may be superseded by it; compare before opening.
3. Do not merge, promote or deploy. `master: patternode-platform` merges the platform pull request. Knowledge-store merges are that repository's own maintainers and Release Please. Tell the master session the platform pull request is ready only when CI is green. The ready note names the pull request, says what it changes, and says what shipping needs.
4. Release Please on knowledge-store follows `main`: merging the pull request adds it to the open release pull request, and merging that cuts the tag. The lab pin moves only after a release tag contains this work. Then, in platform, move `ref=v0.3.0` to that tag in a pull request into `develop`, promote `deploy`, and have Dermot apply. Until that apply, an upload tests `v0.3.0`.
5. Only after the collection is on the applied revision, upload the 722 documents. Expect the first sweep to discover a draft and stop at `awaiting_curation`.
6. If the applied image is still `v0.3.0`, the draft will not use the measures ontology. If the applied image contains this branch, the draft should use Metric, Quantity, Instant and Period as domain or range and should not redeclare them. Check the draft for that before publishing.
7. Curate the draft under `ontology/enterprise-rag/`, set `owl:versionInfo` to `1.0.0`, diff, and publish with `--activate`. That is what starts extraction, projection and the graph load.
8. After extraction, use `candidates --propose` for the terms the first 15 classes could not say. Do not raise the first sample to the whole 722 as a substitute. Discovery cost is the sample.
9. Tag `measures-v1.0.0` when the vocabulary is released, then open the w3id.org pull request. Not before the tag exists.
10. AWS on a new agent: the three session variables from `aws sso login --profile earnings-lab`, plus `AWS_REGION=us-east-1`. This VM never received them.

## Rules the next session must keep

- Conventional Commits. Knowledge-store commits use `git commit -s`.
- No em dash as sentence punctuation. No bold inside a sentence.
- Do not name an employer, and do not raise employment consent.
- Do not edit a guardrail. Do not put GIFS code in this repository.
- Do not write a new ADR under platform `docs/architecture/`. A design change goes to patternode-architecture.
- Dermot manages keys. Give the command and stop.
- Dermot runs every `terraform apply`.
- The live lab is the applied pin, not `main` and not this branch.
- Do not upload `questions.jsonl` or the half-million distractors.
- Do not retrofit the space-missions, Holmes or other sample ontologies.
