# Handoff: Knowledge Store briefing

This packet is enough for a new agent to finish the briefing without the conversation that produced the picture. Read this file first. The generator output under `docs/explainer/` stays the source the build rewrites. This handoff is the copy to hand over.

## What this briefing is for

The briefing is a little over five minutes. It opens by naming the collection the examples use, and by saying that collection is a stand-in. It is for people, including executives, who only broadly understand AI agents. After it, it should be clear that the technique improves consistency and accuracy because a result has to be tied to a passage. It does not show the product being operated.

## What is already finished

The picture is rendered in the Patternode brand (Midnight Terminal navy, IBM Plex, the mark). The brand restyle is commit `0784a06` (`docs: draw the briefing in the Patternode brand`). The briefing opens on the collection, before any Holmes example.

Work lives on `cursor/knowledge-store-explainer-e63b` in the knowledge-store repository. The draft pull request is https://github.com/patternode/knowledge-store/pull/41. Its base branch is `main`. Do not open a second pull request, and do not create a new branch for this briefing.

Seven clips, then the assembly (5:07, 307.4 seconds):

| Assembly in | Assembly out | File |
|---|---|---|
| 0:00 | 0:35 | `docs/explainer/media/00-the-collection.mp4` |
| 0:35 | 1:20 | `docs/explainer/media/01-usual-path.mp4` |
| 1:20 | 2:04 | `docs/explainer/media/02-ontology-and-graph.mp4` |
| 2:04 | 2:46 | `docs/explainer/media/03-graph-and-vectors.mp4` |
| 2:46 | 3:23 | `docs/explainer/media/04-bring-ontology.mp4` |
| 3:23 | 4:07 | `docs/explainer/media/05-derive-ontology.mp4` |
| 4:07 | 5:07 | `docs/explainer/media/06-when-someone-asks.mp4` |
| 0:00 | 5:07 | `docs/explainer/media/assembly.mp4` |

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

It is a stand-in. The same pictures apply to a company's own files, a research library, or any other collection. Nothing in the method depends on these particular stories.

#### 2. The usual path

Clip `01-usual-path.mp4`. Assembly 0:35 to 1:20.

An agent that answers from a company's own documents usually takes one path. The documents are cut into chunks and stored as vectors. A question retrieves the chunks nearest to it in meaning, and the agent writes a sentence from them.

Here the question is the name of Sherlock Holmes's mother. The stories never give it. The nearest chunks are about other mothers, including Helen Stoner's. The model can still write her mother's name, and attach a citation once the sentence exists. The words were in the collection. The relationship was not.

#### 3. Ontology and graph

Clip `02-ontology-and-graph.mp4`. Assembly 1:20 to 2:04.

An ontology is the picture of what a collection is allowed to say. It names the kinds of things, and the links between them. A person. A case. A cause. A person investigates a case. A person is killed by a cause.

A knowledge graph is that picture, filled in from the documents. Holmes investigates the Speckled Band. Dr Grimesby Roylott is killed by a swamp adder. Each fact points back to the passage that said it. The agent can ask what is connected to what, and of what kind.

#### 4. Graph and vectors

Clip `03-graph-and-vectors.mp4`. Assembly 2:04 to 2:46.

When a question names things, the graph is the path. What killed Dr Roylott walks from the person, along killed by, to the cause, and the passage comes with the fact.

When a question describes a situation, the words may not match. A doctor dies of a snake in his own room. Vector search finds the passage by meaning. The facts cite passages, so that hit leads back to the same fact. The graph holds the structure. The vectors hold the wording the question never used.

#### 5. Bring the ontology

Clip `04-bring-ontology.mp4`. Assembly 2:46 to 3:23.

If you already have the vocabulary, you bring the ontology with the documents. The documents are kept as they arrived, and divided into passages small enough to cite. Extraction reads each passage through the ontology you brought.

A fact is kept only when that passage contains it. Roylott, killed by, a swamp adder, stays, because The Speckled Band says so. From that record the lab builds the graph, and one vector for each passage.

#### 6. Derive the ontology

Clip `05-derive-ontology.mp4`. Assembly 3:23 to 4:07.

If you do not bring an ontology, the documents arrive on their own. The lab reads a sample and proposes the kinds of things they keep mentioning, and the links that should be allowed. Those proposals become a draft. A person reviews it and publishes it.

Then the same extraction runs. Passages are read into the vocabulary that came from the documents, and the graph and the vectors are built in the same way. The ontology was derived. A fact still has to be in the passage.

#### 7. The chat

Clip `06-when-someone-asks.mp4`. Assembly 4:07 to 5:07.

A person types a message in the chat. The agent is given the collection's ontology, and it plans in those types. A message that names something follows the graph. What killed Dr Roylott walks from the person to the cause, and the passage cited by that fact is read.

The agent proposes a statement, with a quote taken from the passage. The quote is checked. It is in The Speckled Band, so the statement stays. The result in the chat is the swamp adder, with that passage beside it.

A second message takes the same path. The name of Sherlock Holmes's mother meets other mothers in the stories, and nothing that names his. No statement survives the check. The result in the chat is a decline.

### Record yourself

From `voice-record.md`. Read each clip straight through, as if explaining the diagram to a room. Pause between the paragraphs. The clip is long enough for this read at a measured pace.

#### 1. The collection

Clip `00-the-collection.mp4`. Assembly 0:00 to 0:35.

These examples use one collection. A collection, sometimes called a corpus, is the set of documents an agent is allowed to answer from. Here, that set is three Sherlock Holmes books: the Adventures, the Memoirs, and the Return.

It is a stand-in. The same pictures apply to your own documents, a research library, or any other collection. Nothing in the method depends on these particular stories.

#### 2. The usual path

Clip `01-usual-path.mp4`. Assembly 0:35 to 1:20.

An agent answering from your own documents usually works like this. The pages are cut into chunks and stored as vectors. A question pulls back the chunks nearest in meaning, and the agent writes a sentence.

Take a question the stories do not answer: the name of Sherlock Holmes's mother. Nothing in the collection says it. The nearest chunks are about other mothers, including Helen Stoner's. From those words the model can write a name, and a citation gets attached after the sentence exists. The words were there. They were about someone else.

#### 3. Ontology and graph

Clip `02-ontology-and-graph.mp4`. Assembly 1:20 to 2:04.

An ontology is a picture of what these documents are allowed to mean. The kinds of things, and the links you permit. A person. A case. A cause. A person investigates a case. A person is killed by a cause.

The knowledge graph is that picture filled in. Holmes investigates the Speckled Band. Dr Roylott is killed by a swamp adder. Every fact points back to the passage it came from. The agent can follow a connection, instead of hoping the right words sit next to each other.

#### 4. Graph and vectors

Clip `03-graph-and-vectors.mp4`. Assembly 2:04 to 2:46.

Ask what killed Dr Roylott, and the graph is enough. Person, killed by, cause, and the passage is already on the fact.

Ask it another way. A doctor dies of a snake in his own room, and the wording does not match the page. The vectors find that page by meaning. Because each fact cites a passage, the search leads back to the same fact. Structure in the graph. Wording in the vectors.

#### 5. Bring the ontology

Clip `04-bring-ontology.mp4`. Assembly 2:46 to 3:23.

This is the path when you bring the ontology. Documents come in and stay as they arrived. They are split into passages you can cite. The ontology you brought sits beside that flow, and extraction reads each passage in those types.

A fact is kept only when the passage contains it. The Speckled Band names the swamp adder, so that fact enters the graph. Beside the graph, one vector for each passage.

#### 6. Derive the ontology

Clip `05-derive-ontology.mp4`. Assembly 3:23 to 4:07.

This is the path when you do not bring an ontology. The same documents come in. A sample of them is read, and the lab proposes the kinds of things they talk about, and the links between those kinds. That becomes a draft. You look at it, and you publish it.

From there it is the same flow. Passages are read into the ontology that was derived from them. The graph and the vectors are built the same way, and a fact still has to be in the passage.

#### 7. The chat

Clip `06-when-someone-asks.mp4`. Assembly 4:07 to 5:07.

Someone types in the chat. The agent has the ontology, so it plans in those types. If the message names something, it follows the graph. What killed Dr Roylott goes from the person to the cause, and the passage on that fact is read.

The agent offers a statement and a quote from the passage. The quote is checked. The Speckled Band does say swamp adder, so that statement stays. What you see in the chat is the swamp adder, and the passage it came from.

Type the other question, and it is the same path. Holmes's mother's name meets other mothers, not his. Nothing survives the check. The chat declines.

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
- [ ] Treat `docs/explainer/comfy-shots.md` as optional atmosphere. It may be stale relative to the seven-clip cut. Do not ask an image model to draw words. ComfyUI is not in this workspace.
- [ ] Leave lab screen recordings out. Do not show the product being operated.
- [ ] After any palette or layout change, check the late frames of each clip. Do not commit `docs/explainer/media/stills/` or any `__pycache__`.
- [ ] If the assembly changes, replace `user-interfaces/site/public/media/knowledge-store-briefing.mp4` on patternode-platform branch `cursor/knowledge-store-briefing-link-e63b` and update https://github.com/patternode/patternode-platform/pull/421. On that repository: no em dashes inside a sentence, no bold mid-sentence, and never name Dermot's employer. Pull requests use the repository template, including Why and a release note with Visibility: internal. The base branch is `develop`.
- [ ] Keep this repository's pull request on base `main`. Commit style here is `docs: ...`. Stay on `cursor/knowledge-store-explainer-e63b` and update https://github.com/patternode/knowledge-store/pull/41. Leave that pull request a draft.
