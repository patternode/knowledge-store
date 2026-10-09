# Briefing

An architecture briefing for people who know what an AI agent is. It opens by saying why the briefing is worth hearing, then names the collection the examples use: three books of Sherlock Holmes stories, a stand-in for any documents. The picture shows the usual way an agent answers from documents, what an ontology and a knowledge graph add, why vector search stays beside the graph, and the two ways this lab builds that graph. It closes on how to try the public repository. It is drawn in the Patternode brand: Midnight Terminal on the navy ground, IBM Plex, and the mark.

It opens with why the briefing is worth hearing, then names the collection. One path brings an ontology with the documents. Extraction reads the passages through it. The other path starts from documents alone: a sample proposes the vocabulary, a person publishes it, and the same extraction runs. The chat uses a question from the Knowledge Store dashboard: where Professor Moriarty appears. The Final Problem stays, because that story says so. Where he was born, the sources do not say. The close says what is better with a graph and the vectors together. The last clip says how to try the public repository: clone it, and run it in your own AWS account.

It does not show the product being operated.

A new agent should start at [HANDOFF.md](HANDOFF.md). That file holds both voice scripts, the facts and brand the picture has to keep, and the checklist of what is still left.

| File | What it is |
|---|---|
| [script.md](script.md) | Timeline and what is on screen |
| [voice-pro.md](voice-pro.md) | The read for a professional technical narrator. Continuous prose, one block per clip |
| [voice-record.md](voice-record.md) | The same clips, written to record yourself |
| [media/assembly.mp4](media/assembly.mp4) | The picture, in order, with the professional narration mixed on |

Read a clip straight through. Pause between its paragraphs. The picture is timed to the longer of the two reads.

The voice on the assembly is the professional read of [voice-pro.md](voice-pro.md), spoken with the Microsoft Edge neural voice en-US-ChristopherNeural through edge-tts, a little slower than that voice's default. [voice-record.md](voice-record.md) is still there if Dermot wants to replace that mix with his own recording.

The site serves `media/assembly.mp4` as `/media/knowledge-store-briefing.mp4`, linked from the Knowledge Store lab page. After a re-render, copy the assembly there.

```bash
python docs/explainer/build.py --docs
python docs/explainer/build.py
python docs/explainer/narrate.py
```

The first command rewrites the docs. The second redraws the clips, with a silent track. The third puts the saved narration back on.

The Holmes examples are from the three collections fetched by `examples/sherlock-holmes/fetch.py`. The question on screen is the first sample on the Knowledge Store dashboard: where Professor Moriarty appears. He appears in *The Final Problem*, and that story brings him to the Reichenbach Falls. The same story calls him “a man of good birth and excellent education” and does not name a birthplace, which is why a search by nearby words can attach the wrong fact.
