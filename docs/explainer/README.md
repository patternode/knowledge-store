# Briefing

A conceptual cut for people who know what an AI agent is, and not much more than that. It starts with the usual way an agent answers from documents, explains why an ontology and a knowledge graph change the questions an agent can ask, why vector search still belongs beside the graph, and then what this lab does. On the way in. And when someone asks.

It does not show the product being operated, and it does not walk the checks one by one.

| File | What it is |
|---|---|
| [script.md](script.md) | Timeline and what is on screen |
| [voice-pro.md](voice-pro.md) | The read for a professional technical narrator. Continuous prose, one block per clip |
| [voice-record.md](voice-record.md) | The same clips, written to record yourself |
| [media/assembly.mp4](media/assembly.mp4) | The picture, in order |

Read a clip straight through. Pause between its paragraphs. The picture is timed to the longer of the two reads.

```bash
python docs/explainer/build.py --docs
python docs/explainer/build.py
```

The Holmes examples in the last clip are from the three collections fetched by `examples/sherlock-holmes/fetch.py`. Roylott’s death is in *The Adventure of the Speckled Band*. None of those stories names Sherlock Holmes’s mother.
