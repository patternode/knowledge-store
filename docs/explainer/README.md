# Briefing

An architecture briefing for people who know what an AI agent is. The picture shows the usual way an agent answers from documents, what an ontology and a knowledge graph add, why vector search stays beside the graph, and the two ways this lab builds that graph.

One path brings an ontology with the documents. Extraction reads the passages through it. The other path starts from documents alone: a sample proposes the vocabulary, a person publishes it, and the same extraction runs. The last clip is the chat: a message goes in, the agent follows the graph and the passages, and the result comes back only when a passage supports it.

It does not show the product being operated.

| File | What it is |
|---|---|
| [script.md](script.md) | Timeline and what is on screen |
| [voice-pro.md](voice-pro.md) | The read for a professional technical narrator. Continuous prose, one block per clip |
| [voice-record.md](voice-record.md) | The same clips, written to record yourself |
| [media/assembly.mp4](media/assembly.mp4) | The picture, in order |

Read a clip straight through. Pause between its paragraphs. The picture is timed to the longer of the two reads.

The site serves `media/assembly.mp4` as `/media/knowledge-store-briefing.mp4`, linked from the Knowledge Store lab page. After a re-render, copy the assembly there.

```bash
python docs/explainer/build.py --docs
python docs/explainer/build.py
```

The Holmes examples are from the three collections fetched by `examples/sherlock-holmes/fetch.py`. Roylott’s death is in *The Adventure of the Speckled Band*. None of those stories names Sherlock Holmes’s mother. Helen Stoner’s mother is named, which is why a search by nearby words can attach the wrong person.
