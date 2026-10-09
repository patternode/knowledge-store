# Handoff: Knowledge Store briefing

This packet is enough for a new agent to finish the briefing without the conversation that produced the picture. Read this file first. The generator output under `docs/explainer/` stays the source the build rewrites. This handoff is the copy to hand over.

## What this briefing is for

The briefing is about 5:50. It opens by saying why it is worth hearing, then names the collection the examples use, and says that collection is a stand-in. It is for people, including executives, who only broadly understand AI agents. The shape is a purpose, a setting, a problem, a turn, how this lab builds the graph, a close, and how to try the public repository. After it, it should be clear what is better when a graph and vectors work together, and what to do next on any collection. It does not show the product being operated.

The running example is the first sample question on the Knowledge Store dashboard: where Professor Moriarty appears. The decline is where he was born. Do not put a swamp adder, The Speckled Band, or Holmes's mother back on screen. Those examples were replaced because the adder reads as either a snake or an adding machine.

## What is already finished

The picture is rendered in the Patternode brand (Midnight Terminal navy, IBM Plex, the mark). The brand restyle is commit `0784a06` (`docs: draw the briefing in the Patternode brand`). The briefing opens on the purpose, then the collection, before any Holmes example.

Work lives on `cursor/knowledge-store-explainer-e63b` in the knowledge-store repository. The draft pull request is https://github.com/patternode/knowledge-store/pull/41. Its base branch is `main`. Do not open a second pull request, and do not create a new branch for this briefing.

Ten clips, then the assembly (5:50, 349.7 seconds):

| Assembly in | Assembly out | File |
|---|---|---|
| 0:00 | 0:21 | `docs/explainer/media/00-purpose.mp4` |
| 0:21 | 0:56 | `docs/explainer/media/00-the-collection.mp4` |
| 0:56 | 1:36 | `docs/explainer/media/01-usual-path.mp4` |
| 1:36 | 2:13 | `docs/explainer/media/02-ontology-and-graph.mp4` |
| 2:13 | 2:49 | `docs/explainer/media/03-graph-and-vectors.mp4` |
| 2:49 | 3:20 | `docs/explainer/media/04-bring-ontology.mp4` |
| 3:20 | 3:51 | `docs/explainer/media/05-derive-ontology.mp4` |
| 3:51 | 4:30 | `docs/explainer/media/06-when-someone-asks.mp4` |
| 4:30 | 5:07 | `docs/explainer/media/07-what-is-better.mp4` |
| 5:07 | 5:50 | `docs/explainer/media/08-try-it.mp4` |
| 0:00 | 5:50 | `docs/explainer/media/assembly.mp4` |

Both voice scripts are written. `docs/explainer/script.md` is the timeline and the on-screen picture notes. `docs/explainer/voice-pro.md` is the professional narrator. `docs/explainer/voice-record.md` is the read-yourself twin. `docs/explainer/build.py` generates those three files from its `SECTIONS` list. `docs/explainer/README.md` is the short entry point.

The mixed voice on the assembly is the professional read of `voice-pro.md`. It was spoken with the Microsoft Edge neural voice en-US-ChristopherNeural through edge-tts, at rate -10%. Speech starts 0.8 seconds into each clip. A take that would run past its clip is sped enough to finish with a short breath. The other clips are left at the spoken pace, and the time after the last word stays silent. `voice-record.md` is still there if Dermot wants to replace this mix with his own recording.

Paragraph takes, one wav per paragraph, are in `docs/explainer/assets/narration/`. `python3 docs/explainer/narrate.py` joins them with a short pause, fits each take to its clip, and remuxes the existing picture without redrawing a frame. `python3 docs/explainer/narrate.py --synthesize` calls edge-tts again and replaces those wavs. There was no recording by Dermot on disk, so the mix uses the synthesized professional read. After this story change the wavs were synthesized again. The close has one paragraph. Do not leave an older second close take in that folder.

The website copy is a separate repository. patternode-platform branch `cursor/knowledge-store-briefing-link-e63b` serves the file as `/media/knowledge-store-briefing.mp4`, linked from the Knowledge Store lab page. The file in that repository is `user-interfaces/site/public/media/knowledge-store-briefing.mp4`. The draft pull request is https://github.com/patternode/patternode-platform/pull/421. Its base branch is `develop`. Replace that file when the assembly changes.

## Voice scripts

The two reads below are the current prose, copied here so this packet stands alone. One block per clip. The clip filename and the assembly in and out times are the ones in `script.md`.

`python3 docs/explainer/build.py` regenerates `script.md`, `voice-pro.md`, and `voice-record.md` from the `SECTIONS` list in `build.py`. A story change belongs in that list. Then regenerate the docs. `python3 docs/explainer/build.py --docs`, from the repository root, rewrites those three files and does not re-encode the video. After a regeneration, copy the new prose back into this handoff, or the packet will drift from the generator output. A full `python3 docs/explainer/build.py` also renders the clips. Do not run that unless the picture itself must change. That encode writes a silent track. Run `python3 docs/explainer/narrate.py` afterwards.

### Professional narrator

From `voice-pro.md`. For a narrator in the style of a serious technical film: unhurried, precise, no sales language. Read each clip as continuous prose. Pause between the paragraphs.

#### 1. The purpose

Clip `00-purpose.mp4`. Assembly 0:00 to 0:21.

This briefing shows how an agent can answer from documents without inventing what they never said. The usual way fails. A graph and a vector search belong together. Then, how to try this open-source store on your own documents.

#### 2. The collection

Clip `00-the-collection.mp4`. Assembly 0:21 to 0:56.

The examples that follow use one collection. A collection, sometimes called a corpus, is the set of documents an agent is allowed to answer from. Here that set is three Sherlock Holmes books: the Adventures, the Memoirs, and the Return.

It is a stand-in for any documents. The usual way, then why a graph belongs with the vectors, then how a collection becomes that graph, then what to do next.

#### 3. The usual path

Clip `01-usual-path.mp4`. Assembly 0:56 to 1:36.

An agent that answers from a company's own documents usually takes one path. The documents are cut into chunks and stored as vectors. A question retrieves the nearest chunks, and the agent writes a sentence.

The question is where Professor Moriarty was born. The stories never say. The nearest chunk calls him a man of good birth and excellent education. The model can still write that phrase, and attach a citation afterwards. The words were there. They do not name a place.

#### 4. Ontology and graph

Clip `02-ontology-and-graph.mp4`. Assembly 1:36 to 2:13.

An ontology is the picture of what a collection is allowed to say. It names the kinds of things, and the links between them. A person. A story. A place. A person appears in a story. A person meets someone at a place.

A knowledge graph is that picture, filled in. Professor Moriarty appears in The Final Problem. That story brings him and Holmes to the Reichenbach Falls. Each fact points at a passage.

#### 5. Graph and vectors

Clip `03-graph-and-vectors.mp4`. Assembly 2:13 to 2:49.

When a question names things, the graph is the path. Where does Professor Moriarty appear walks from the person, along appears in, to the story, and on to the falls. The passage comes with the fact.

Instead, two rivals fall together at a waterfall. The vectors find that passage by meaning and return to the same fact. The graph holds the connection. The vectors hold the wording the question never used.

#### 6. Bring the ontology

Clip `04-bring-ontology.mp4`. Assembly 2:49 to 3:20.

If you already have the vocabulary, you bring the ontology with the documents. They are divided into passages. Extraction reads each passage through the ontology you brought.

A fact is kept only when the passage contains it. The Final Problem names Moriarty and the Reichenbach Falls, so that fact stays. The lab builds the graph, and one vector for each passage.

#### 7. Derive the ontology

Clip `05-derive-ontology.mp4`. Assembly 3:20 to 3:51.

If you do not bring an ontology, the documents arrive on their own. The lab reads a sample and proposes the kinds of things they mention, and the links that should be allowed. A person publishes that draft.

Then the same extraction runs. The graph and the vectors are built the same way. A fact still has to be in the passage.

#### 8. The chat

Clip `06-when-someone-asks.mp4`. Assembly 3:51 to 4:30.

A person types a message in the chat. Where does Professor Moriarty appear walks from the person to the story, and the cited passage is read. It is in The Final Problem, so the statement stays. The result is that story, with the passage beside it.

Where he was born takes the same path. It meets the phrase a man of good birth, and nothing that names a place. The result is a decline. The sources do not say.

#### 9. What is better

Clip `07-what-is-better.mp4`. Assembly 4:30 to 5:07.

A graph and the vectors do different work. The graph holds what is connected to what, and of what kind. The vectors hold wording the question never used. A result comes back only when a passage supports it. The Final Problem stays, because that story says where Moriarty appears. Where he was born does not, because the collection never names a place. A sentence no longer receives a citation after it has been written.

#### 10. Try it

Clip `08-try-it.mp4`. Assembly 5:07 to 5:50.

Here is what we just covered. Nearest words can attach a citation to the wrong fact. A graph holds the connection, and vectors find the wording. A result stays only when a passage supports it. Professor Moriarty appears in The Final Problem, at the Reichenbach Falls. Where he was born, the sources do not say.

To try it, go to the public repository, github.com/patternode/knowledge-store. Clone it. It is open source. The deploy guide shows how to run it in your own AWS account, on your own documents.

### Record yourself

From `voice-record.md`. Read each clip straight through, as if explaining the diagram to a room. Pause between the paragraphs. The clip is long enough for this read at a measured pace.

#### 1. The purpose

Clip `00-purpose.mp4`. Assembly 0:00 to 0:21.

This briefing shows how an agent can answer from your own documents without inventing what they never said. The usual way fails. A graph and a vector search belong together. Then, how to try this open-source store yourself.

#### 2. The collection

Clip `00-the-collection.mp4`. Assembly 0:21 to 0:56.

These examples use one collection. A collection, sometimes called a corpus, is the set of documents an agent is allowed to answer from. Here, that set is three Sherlock Holmes books: the Adventures, the Memoirs, and the Return.

It is a stand-in for your own documents. The usual way, then why a graph belongs with the vectors, then how a collection becomes that graph, then what to do next.

#### 3. The usual path

Clip `01-usual-path.mp4`. Assembly 0:56 to 1:36.

An agent answering from your own documents usually works like this. The pages are cut into chunks and stored as vectors. A question pulls back the nearest chunks, and the agent writes a sentence.

Ask where Professor Moriarty was born. The stories never say. The nearest chunk calls him a man of good birth. From those words the model can write that phrase, and a citation gets attached afterwards. The words were there. They do not name a place.

#### 4. Ontology and graph

Clip `02-ontology-and-graph.mp4`. Assembly 1:36 to 2:13.

An ontology is a picture of what these documents are allowed to mean. The kinds of things, and the links you permit. A person. A story. A place. A person appears in a story. A person meets someone at a place.

The knowledge graph is that picture filled in. Professor Moriarty appears in The Final Problem. That story brings him and Holmes to the Reichenbach Falls. Every fact points at a passage.

#### 5. Graph and vectors

Clip `03-graph-and-vectors.mp4`. Assembly 2:13 to 2:49.

Ask where Professor Moriarty appears, and the graph is enough. Person, appears in, story, meets at the falls, and the passage is already on the fact.

Instead, two rivals fall together at a waterfall. The vectors find that passage by meaning and return to the same fact. The graph holds the connection. The vectors hold the wording the question never used.

#### 6. Bring the ontology

Clip `04-bring-ontology.mp4`. Assembly 2:49 to 3:20.

This is the path when you bring the ontology. Documents stay as they arrived and are split into passages to cite. Extraction reads each passage in the types you brought.

A fact is kept only when the passage contains it. The Final Problem names Moriarty and the falls, so that fact stays. One vector is stored for each passage.

#### 7. Derive the ontology

Clip `05-derive-ontology.mp4`. Assembly 3:20 to 3:51.

This is the path when you do not bring an ontology. The documents come in. A sample is read, and the lab proposes the kinds of things they talk about. You publish that draft.

Then the same extraction runs. The graph and the vectors are built the same way. A fact still has to be in the passage.

#### 8. The chat

Clip `06-when-someone-asks.mp4`. Assembly 3:51 to 4:30.

Someone types in the chat. Where does Professor Moriarty appear goes from the person to the story, and the passage on that fact is read. The Final Problem does name him, so the statement stays. You see that story, with the passage beside it.

Ask where he was born. It meets a man of good birth, not a place. The chat declines. The sources do not say.

#### 9. What is better

Clip `07-what-is-better.mp4`. Assembly 4:30 to 5:07.

A graph and the vectors do different work. The graph holds what is connected to what, and of what kind. The vectors hold wording the question never used. A result comes back only when a passage supports it. The Final Problem stays, because that story says where Moriarty appears. Where he was born does not, because the collection never names a place. A sentence no longer gets a citation after it has been written.

#### 10. Try it

Clip `08-try-it.mp4`. Assembly 5:07 to 5:50.

Here is what we just covered. Nearest words can attach a citation to the wrong fact. A graph holds the connection, and vectors find the wording. A result stays only when a passage supports it. Professor Moriarty appears in The Final Problem, at the Reichenbach Falls. Where he was born, the sources do not say.

To try it, go to the public repository, github.com/patternode/knowledge-store. Clone it. It is open source. The deploy guide shows how to run it in your own AWS account, on your own documents.

## Facts that must stay accurate

### Holmes corpus

The example corpus is the three short-story collections: The Adventures of Sherlock Holmes, The Memoirs of Sherlock Holmes, and The Return of Sherlock Holmes. `examples/sherlock-holmes/fetch.py` downloads them from Project Gutenberg as books 1661, 834, and 108. The story files are gitignored (`examples/sherlock-holmes/stories/`). They are not in the repository.

The question on screen is the low sample on the Knowledge Store dashboard, in `patternode-platform` `deployments/knowledge-store/main.tf`: "Where does Professor Moriarty appear?" Professor Moriarty appears in The Final Problem (Memoirs, Gutenberg 834). That story brings him and Holmes to the Reichenbach Falls. The same story calls him "a man of good birth and excellent education" and "the Napoleon of crime." "Good birth" does not name a birthplace. That is why a nearest-words search can attach the wrong fact. The picture uses that phrase as the decline: where he was born, the sources do not say.

Do not use the dashboard's snake question, The Speckled Band, a swamp adder, or Holmes's mother. 221B Baker Street does appear in the stories. Do not use it as the decline.

The ontology on screen is Person, Story, and Place, with "appears in" and "meets at." The filled graph is Moriarty, appears in The Final Problem, meets at Reichenbach. The falls are where that story brings them. Do not claim the falls are the only place he is spoken of.

### Try it

The public repository is https://github.com/patternode/knowledge-store. It is open source. `docs/deploy/aws/README.md` is the deploy guide: Terraform in this repository, into the viewer's own AWS account, on their own documents. The ending says that in three steps: the public repo, clone it, your own AWS account.

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
python3 docs/explainer/narrate.py
```

The first command rewrites the three generated docs. The second also re-encodes the clips and `docs/explainer/media/assembly.mp4`, and that encode writes a silent track. The third puts the professional read back on. After a re-render, copy that assembly to `user-interfaces/site/public/media/knowledge-store-briefing.mp4` on the platform branch named above, and update pull request 421.

## What is left

- [x] The mixed voice is the professional read of `docs/explainer/voice-pro.md` (edge-tts, en-US-ChristopherNeural, rate -10%), re-synthesized for the Moriarty cut. The picture is 5:50. `docs/explainer/voice-record.md` is still there if Dermot wants to replace that mix with his own recording. Paragraph wavs are in `docs/explainer/assets/narration/`, and `python3 docs/explainer/narrate.py` rebuilds the mix from them.
- [ ] Treat `docs/explainer/comfy-shots.md` as optional atmosphere. It may be stale relative to the ten-clip cut. Do not ask an image model to draw words. ComfyUI is not in this workspace.
- [ ] Leave lab screen recordings out. Do not show the product being operated.
- [ ] After any palette or layout change, check the late frames of each clip. Do not commit `docs/explainer/media/stills/` or any `__pycache__`.
- [ ] If the assembly changes, replace `user-interfaces/site/public/media/knowledge-store-briefing.mp4` on patternode-platform branch `cursor/knowledge-store-briefing-link-e63b` and update https://github.com/patternode/patternode-platform/pull/421. On that repository: no em dashes inside a sentence, no bold mid-sentence, and never name Dermot's employer. Pull requests use the repository template, including Why and a release note with Visibility: internal. The base branch is `develop`.
- [ ] Keep this repository's pull request on base `main`. Commit style here is `docs: ...`. Stay on `cursor/knowledge-store-explainer-e63b` and update https://github.com/patternode/knowledge-store/pull/41. Leave that pull request a draft.
