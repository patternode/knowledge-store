# Handoff: Knowledge Store briefing

This packet is enough for a new agent to finish the briefing without the conversation that produced the picture. Read this file first. The generator output under `docs/explainer/` stays the source the build rewrites. This handoff is the copy to hand over.

## What this briefing is for

The briefing is just under five minutes. It opens by naming the collection the examples use, and by saying that collection is a stand-in. It is for people, including executives, who only broadly understand AI agents. The shape is a setting, a problem, a turn, how this lab builds the graph, and a close. After it, it should be clear what is better when a graph and vectors work together, and what to do next on any collection. It does not show the product being operated.

## What is already finished

The picture is rendered in the Patternode brand (Midnight Terminal navy, IBM Plex, the mark). The brand restyle is commit `0784a06` (`docs: draw the briefing in the Patternode brand`). The briefing opens on the collection, before any Holmes example.

Work lives on `cursor/knowledge-store-explainer-e63b` in the knowledge-store repository. The draft pull request is https://github.com/patternode/knowledge-store/pull/41. Its base branch is `main`. Do not open a second pull request, and do not create a new branch for this briefing.

Eight clips, then the assembly (4:57, 297.0 seconds):

| Assembly in | Assembly out | File |
|---|---|---|
| 0:00 | 0:35 | `docs/explainer/media/00-the-collection.mp4` |
| 0:35 | 1:15 | `docs/explainer/media/01-usual-path.mp4` |
| 1:15 | 1:50 | `docs/explainer/media/02-ontology-and-graph.mp4` |
| 1:50 | 2:24 | `docs/explainer/media/03-graph-and-vectors.mp4` |
| 2:24 | 2:54 | `docs/explainer/media/04-bring-ontology.mp4` |
| 2:54 | 3:25 | `docs/explainer/media/05-derive-ontology.mp4` |
| 3:25 | 4:01 | `docs/explainer/media/06-when-someone-asks.mp4` |
| 4:01 | 4:57 | `docs/explainer/media/07-what-is-better.mp4` |
| 0:00 | 4:57 | `docs/explainer/media/assembly.mp4` |

Both voice scripts are written. `docs/explainer/script.md` is the timeline and the on-screen picture notes. `docs/explainer/voice-pro.md` is the professional narrator. `docs/explainer/voice-record.md` is the read-yourself twin. `docs/explainer/build.py` generates those three files from its `SECTIONS` list. `docs/explainer/README.md` is the short entry point.

The picture is silent. The assembly file carries a silent audio track so a later mix can replace that silence. Mixing a voice onto the assembly is not done.

The website copy is a separate repository. patternode-platform branch `cursor/knowledge-store-briefing-link-e63b` serves the file as `/media/knowledge-store-briefing.mp4`, linked from the Knowledge Store lab page. The file in that repository is `user-interfaces/site/public/media/knowledge-store-briefing.mp4`. The draft pull request is https://github.com/patternode/patternode-platform/pull/421. Its base branch is `develop`. Do not edit patternode-platform unless the assembly is re-rendered.

## Voice scripts

The two reads below are the current prose, copied here so this packet stands alone. One block per clip. The clip filename and the assembly in and out times are the ones in `script.md`.

`python3 docs/explainer/build.py` regenerates `script.md`, `voice-pro.md`, and `voice-record.md` from the `SECTIONS` list in `build.py`. A story change belongs in that list. Then regenerate the docs. `python3 docs/explainer/build.py --docs`, from the repository root, rewrites those three files and does not re-encode the video. After a regeneration, copy the new prose back into this handoff, or the packet will drift from the generator output. A full `python3 docs/explainer/build.py` also renders the clips. Do not run that unless the picture itself must change.

### Professional narrator

From `voice-pro.md`. For a narrator in the style of a serious technical film: unhurried, precise, no sales language. Read each clip as continuous prose. Pause between the paragraphs.

#### 1. The collection

Clip `00-the-collection.mp4`. Assembly 0:00 to 0:35.

The examples that follow use one collection. A collection, sometimes called a corpus, is the set of documents an agent is allowed to answer from. Here that set is three Sherlock Holmes books: the Adventures, the Memoirs, and the Return.

It is a stand-in for any documents. The usual way, then why a graph belongs with the vectors, then how a collection becomes that graph, then what to do next.

#### 2. The usual path

Clip `01-usual-path.mp4`. Assembly 0:35 to 1:15.

An agent that answers from a company's own documents usually takes one path. The documents are cut into chunks and stored as vectors. A question retrieves the nearest chunks, and the agent writes a sentence.

The question is the name of Sherlock Holmes's mother. The stories never give it. The nearest chunks are about other mothers, including Helen Stoner's mother, Mrs Stoner. The model can still write that name, and attach a citation afterwards. The words were there. The relationship was not.

#### 3. Ontology and graph

Clip `02-ontology-and-graph.mp4`. Assembly 1:15 to 1:50.

An ontology is the picture of what a collection is allowed to say. It names the kinds of things, and the links between them. A person. A case. A cause. A person investigates a case. A person is killed by a cause.

A knowledge graph is that picture, filled in. Holmes investigates the Speckled Band. Dr Roylott is killed by a swamp adder. Each fact points at a passage.

#### 4. Graph and vectors

Clip `03-graph-and-vectors.mp4`. Assembly 1:50 to 2:24.

When a question names things, the graph is the path. What killed Dr Roylott walks from the person, along killed by, to the cause. The passage comes with the fact.

Instead, a doctor dies of a snake in his own room. The vectors find that passage by meaning and return to the same fact. The graph holds the connection. The vectors hold the wording the question never used.

#### 5. Bring the ontology

Clip `04-bring-ontology.mp4`. Assembly 2:24 to 2:54.

If you already have the vocabulary, you bring the ontology with the documents. They are divided into passages. Extraction reads each passage through the ontology you brought.

A fact is kept only when the passage contains it. The swamp adder stays, because The Speckled Band says so. The lab builds the graph, and one vector for each passage.

#### 6. Derive the ontology

Clip `05-derive-ontology.mp4`. Assembly 2:54 to 3:25.

If you do not bring an ontology, the documents arrive on their own. The lab reads a sample and proposes the kinds of things they mention, and the links that should be allowed. A person publishes that draft.

Then the same extraction runs. The graph and the vectors are built the same way. A fact still has to be in the passage.

#### 7. The chat

Clip `06-when-someone-asks.mp4`. Assembly 3:25 to 4:01.

A person types a message in the chat. What killed Dr Roylott walks from the person to the cause, and the cited passage is read. It is in The Speckled Band, so the statement stays. The result is a swamp adder, with that passage beside it.

Holmes's mother's name takes the same path. It meets other mothers, and nothing that names his. The result is a decline. The sources do not say.

#### 8. What is better

Clip `07-what-is-better.mp4`. Assembly 4:01 to 4:57.

A graph and the vectors do different work. The graph holds what is connected to what, and of what kind. The vectors hold wording the question never used. A result comes back only when a passage supports it. The swamp adder stays, because the Speckled Band says so. Holmes's mother's name does not, because the collection never gives it. A sentence no longer receives a citation after it has been written.

The next step is the same on any collection. Bring an ontology, or let the documents propose one and have a person publish it. Then ask. What the sources support is returned, with the passage beside it. What they do not say is left unsaid.

### Record yourself

From `voice-record.md`. Read each clip straight through, as if explaining the diagram to a room. Pause between the paragraphs. The clip is long enough for this read at a measured pace.

#### 1. The collection

Clip `00-the-collection.mp4`. Assembly 0:00 to 0:35.

These examples use one collection. A collection, sometimes called a corpus, is the set of documents an agent is allowed to answer from. Here, that set is three Sherlock Holmes books: the Adventures, the Memoirs, and the Return.

It is a stand-in for your own documents. The usual way, then why a graph belongs with the vectors, then how a collection becomes that graph, then what to do next.

#### 2. The usual path

Clip `01-usual-path.mp4`. Assembly 0:35 to 1:15.

An agent answering from your own documents usually works like this. The pages are cut into chunks and stored as vectors. A question pulls back the nearest chunks, and the agent writes a sentence.

The stories never name Sherlock Holmes's mother. The nearest chunks are about other mothers, including Helen Stoner's mother, Mrs Stoner. From those words the model can write that name, and a citation gets attached afterwards. The words were there. They were about someone else.

#### 3. Ontology and graph

Clip `02-ontology-and-graph.mp4`. Assembly 1:15 to 1:50.

An ontology is a picture of what these documents are allowed to mean. The kinds of things, and the links you permit. A person. A case. A cause. A person investigates a case. A person is killed by a cause.

The knowledge graph is that picture filled in. Holmes investigates the Speckled Band. Dr Roylott is killed by a swamp adder. Every fact points at a passage.

#### 4. Graph and vectors

Clip `03-graph-and-vectors.mp4`. Assembly 1:50 to 2:24.

Ask what killed Dr Roylott, and the graph is enough. Person, killed by, cause, and the passage is already on the fact.

Instead, a doctor dies of a snake in his own room. The vectors find that passage by meaning and return to the same fact. The graph holds the connection. The vectors hold the wording the question never used.

#### 5. Bring the ontology

Clip `04-bring-ontology.mp4`. Assembly 2:24 to 2:54.

This is the path when you bring the ontology. Documents stay as they arrived and are split into passages to cite. Extraction reads each passage in the types you brought.

A fact is kept only when the passage contains it. The Speckled Band names the swamp adder, so that fact stays. One vector is stored for each passage.

#### 6. Derive the ontology

Clip `05-derive-ontology.mp4`. Assembly 2:54 to 3:25.

This is the path when you do not bring an ontology. The documents come in. A sample is read, and the lab proposes the kinds of things they talk about. You publish that draft.

Then the same extraction runs. The graph and the vectors are built the same way. A fact still has to be in the passage.

#### 7. The chat

Clip `06-when-someone-asks.mp4`. Assembly 3:25 to 4:01.

Someone types in the chat. What killed Dr Roylott goes from the person to the cause, and the passage on that fact is read. The Speckled Band says swamp adder, so the statement stays. You see a swamp adder, with that passage beside it.

Ask for Holmes's mother's name. It meets other mothers, not his. The chat declines. The sources do not say.

#### 8. What is better

Clip `07-what-is-better.mp4`. Assembly 4:01 to 4:57.

A graph and the vectors do different work. The graph holds what is connected to what, and of what kind. The vectors hold wording the question never used. A result comes back only when a passage supports it. The swamp adder stays, because the Speckled Band says so. Holmes's mother's name does not, because the collection never gives it. A sentence no longer gets a citation after it has been written.

The next step is the same for your own documents. Bring an ontology, or let the documents propose one and you publish it. Then ask. What the sources support comes back, with the passage beside it. What they do not say is left unsaid.

## Facts that must stay accurate

### Holmes corpus

The example corpus is the three short-story collections: The Adventures of Sherlock Holmes, The Memoirs of Sherlock Holmes, and The Return of Sherlock Holmes. `examples/sherlock-holmes/fetch.py` downloads them from Project Gutenberg as books 1661, 834, and 108. The story files are gitignored (`examples/sherlock-holmes/stories/`). They are not in the repository.

Dr Grimesby Roylott dies of a swamp adder bite in The Adventure of the Speckled Band. The story says "It is a swamp adder!" and "the deadliest snake in India."

Sherlock Holmes's mother is never named. Helen Stoner's mother is Mrs Stoner. That is why a nearest-words search can attach the wrong person. 221B Baker Street does appear in the stories. Do not use it as the decline example. The decline example is Holmes's mother's name.

### Two ingestion paths

These match the repository README. The picture shows both, then the same extraction.

Bring an ontology. `ontology_dir` is set to a directory holding `ontology.ttl` (and optionally `shapes.ttl`). Discovery never runs. Documents are kept as they arrived and divided into passages. Extraction keeps a fact only when that passage contains it. One vector is stored for each passage.

Derive an ontology. The collection has no ontology yet. Discovery starts once at least `discovery.min_docs` documents have been refined. The default is 5. The steps are sample, propose, aggregate, consolidate, and review. Curated mode is what the clips show: it stops at a draft, and a person publishes it. Candidates stay out of the graph until a person publishes a version that contains them. Then the same extraction runs. A fact still has to be in the passage.

### Chat

The collection's ontology goes into the system prompt. The agent uses read-only tools. A claim is a statement, a passage id, and a verbatim quote. `src/knowledge_store/agent/grounding.py` checks that the quote is in the passage (`MIN_QUOTE_CHARS = 12`). If nothing survives, the result is a decline: "I can't answer that from the sources in this collection." The picture says "The sources do not say."

Gold RDF is the system of record. The picture stays conceptual. Do not invent SHACL, tool names, or sha256 in the picture.

## Brand

patternode-business was not readable from the environment that drew this picture. The picture follows the copy the website ships: `patternode-platform/user-interfaces/embed-kit/tokens.css`. That file names its source of truth as `patternode-business/marketing/brand/tokens.json`. DEC-001 option B is Midnight Terminal. DEC-003 is IBM Plex.

Use these values. Do not invent a palette.

| Role | Token in the picture | Hex |
|---|---|---|
| Dark ground | `--pn-neutral-950` | `#1b202c` |
| Text | `--pn-neutral-50` | `#f5f7fb` |
| Brand cyan | `--pn-brand-cyan` | `#00b8e6` |
| Logo tile on the navy ground | site dark `--pn-logo-tile` | `#0b1437` |
| Ontology | GOLD, amber, `--pn-cat-3` | `#e69f00` |
| Graph, and a result a passage supports | TEAL, cyan | `#00b8e6` |
| Documents and vectors | BLUE, indigo, `--pn-secondary-400` | `#909cff` |
| Search hits | ROSE, `--pn-tertiary-400` | `#ff6d98` |
| A result the sources do not support | CORAL, danger, `--pn-danger-400` | `#ff7569` |

`build.py` names the diagram roles GOLD, TEAL, BLUE, ROSE, and CORAL with those colours.

The mark is the polyline from the site Logo component (`user-interfaces/site/src/components/Logo.astro`): points `8,44 20,30 30,38 44,16 56,24`, cyan stroke `#00b8e6`, with white nodes at `(20, 30)` and `(44, 16)`, on the navy tile.

Fonts live in `docs/explainer/assets/fonts/` under the SIL Open Font Licence (`OFL.txt`): IBM Plex Sans (`IBMPlexSans[wdth,wght].ttf`) and IBM Plex Mono (`IBMPlexMono-Regular.ttf`).

Rebuild from the repository root:

```bash
python3 docs/explainer/build.py --docs
python3 docs/explainer/build.py
```

The first command rewrites the three generated docs. The second also re-encodes the clips and `docs/explainer/media/assembly.mp4`. After a re-render, copy that assembly to `user-interfaces/site/public/media/knowledge-store-briefing.mp4` on the platform branch named above, and update pull request 421.

## What is left

- [ ] Dermot records `docs/explainer/voice-record.md`, or a narrator reads `docs/explainer/voice-pro.md`. The picture is silent. Mixing the voice onto `docs/explainer/media/assembly.mp4` is not done. Time the read to the assembly in and out points above.
- [ ] Treat `docs/explainer/comfy-shots.md` as optional atmosphere. It may be stale relative to the eight-clip cut. Do not ask an image model to draw words. ComfyUI is not in this workspace.
- [ ] Leave lab screen recordings out. Do not show the product being operated.
- [ ] After any palette or layout change, check the late frames of each clip. Do not commit `docs/explainer/media/stills/` or any `__pycache__`.
- [ ] If the assembly changes, replace `user-interfaces/site/public/media/knowledge-store-briefing.mp4` on patternode-platform branch `cursor/knowledge-store-briefing-link-e63b` and update https://github.com/patternode/patternode-platform/pull/421. On that repository: no em dashes inside a sentence, no bold mid-sentence, and never name Dermot's employer. Pull requests use the repository template, including Why and a release note with Visibility: internal. The base branch is `develop`.
- [ ] Keep this repository's pull request on base `main`. Commit style here is `docs: ...`. Stay on `cursor/knowledge-store-explainer-e63b` and update https://github.com/patternode/knowledge-store/pull/41. Leave that pull request a draft.
