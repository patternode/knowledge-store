# Five-minute briefing

A picture-and-voice cut that explains how Knowledge Store keeps a query result tied to a source. After it, a viewer who already knows retrieval and language models should be able to say why a statement reaches the page, and why a statement that cannot be tied to a passage does not.

The picture is generated. The voice is not. Two slots are left open for a recording of the portal on the lab.

| File | What it is |
|---|---|
| [script.md](script.md) | The whole cut: timeline, picture, and voice, with assembly timecodes |
| [voice-script.md](voice-script.md) | The same voice, one section per take, for recording |
| [comfy-shots.md](comfy-shots.md) | Optional atmospheric shots for the ComfyUI pipeline |
| [build.py](build.py) | Renders the picture from the same cues as the script |
| [media/](media/) | The rendered sections and `assembly.mp4` |

## What is generated, and what you record

Generated, voice recorded against the picture:

1. The failure. A retrieval system writes the answer, then attaches a source.
2. The rule. Something is shown only when a passage contains it.
3. Ingestion. Landing, bronze, silver passages, the ontology, extraction, the RDF record.
4. Chat. Ontology in the prompt, fixed tools, the two routes in, claims, and the check that drops anything the passage does not support.

Record on the lab, picture and voice:

5. Ask a question the collection can answer. Workbench open. Open source 1 and show the highlighted quote.
6. Ask something the documents do not contain. Show the decline.

Replace `05-lab-answer.mp4` and `06-lab-decline.mp4` in the cut. Those files are caption guides so the assembly can be watched before the lab picture exists. The badge on them says so.

## Recording the voice

Use [voice-script.md](voice-script.md). About 160 words a minute. Each line is one sentence; start it at the cue. Assembly timecode is in the bottom right of every frame, and a gold hairline shows progress through the section.

Say sha-256 as “sha two fifty-six”, SHACL as “shackle”, and RDF as the three letters. Bronze, silver, and gold are the layer names.

Suggested lab questions, if the space-missions collection is loaded, are in the voice script. They are director notes, not lines to read. On another collection, use one fact you can point at in a passage, and one fact the documents do not contain.

For the answer take, keep the window wider than 1,100 pixels so the workbench stays beside the chat.

## Render again

```bash
python docs/explainer/build.py --docs          # script and voice only
python docs/explainer/build.py --stills        # one frame per stage, for a look
python docs/explainer/build.py                 # the section files and assembly.mp4
python docs/explainer/build.py --section chat  # one section
```

The cues live in `build.py`. The script and the voice script are written from those cues, so the timecodes match the picture.

The background plate is `assets/bg-network.jpg`. Labels are drawn in code, so terms such as SHACL, the passage identifier, and the decline sentence stay exact.
