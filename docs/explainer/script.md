# Knowledge Store briefing

Eight clips. The picture is an architecture diagram of the flow.

Two complete reads, one per clip, in prose:

- [voice-pro.md](voice-pro.md) for a professional technical narrator.
- [voice-record.md](voice-record.md) to record yourself. Read the paragraphs for that clip straight through.

The clips are timed to the longer of the two reads, at about 130 words a minute, with a short breath at each end.

## Timeline

| In | Out | Clip | Picture |
|---|---|---|---|
| 0:00 | 0:35 | `00-the-collection.mp4` | The collection |
| 0:35 | 1:15 | `01-usual-path.mp4` | The usual path |
| 1:15 | 1:50 | `02-ontology-and-graph.mp4` | Ontology and graph |
| 1:50 | 2:24 | `03-graph-and-vectors.mp4` | Graph and vectors |
| 2:24 | 2:54 | `04-bring-ontology.mp4` | Bring the ontology |
| 2:54 | 3:25 | `05-derive-ontology.mp4` | Derive the ontology |
| 3:25 | 4:01 | `06-when-someone-asks.mp4` | The chat |
| 4:01 | 4:57 | `07-what-is-better.mp4` | What is better |

Total picture: 4:57 (297.0 seconds).

## 1. The collection

`00-the-collection.mp4`, 0:00 to 0:35.

Picture:

- Three story pages: Adventures, Memoirs, and Return, labeled as the collection used in this briefing.
- A short line: a collection, also called a corpus, is the set of documents an agent answers from.
- A quieter mark: this set is a stand-in, and the same pictures apply to any documents.

## 2. The usual path

`01-usual-path.mp4`, 0:35 to 1:15.

Picture:

- Three story collections become a field of vectors. The question is Holmes's mother's name.
- The lit chunks are about Helen Stoner's mother. A sentence is written from them, and a citation is pinned on afterwards.

## 3. Ontology and graph

`02-ontology-and-graph.mp4`, 1:15 to 1:50.

Picture:

- Left, an ontology draws itself: Person, Case, Cause, and the two links that are allowed.
- Right, the same picture filled in. Holmes investigates the Speckled Band. Roylott is killed by a swamp adder. A passage sits on the fact.

## 4. Graph and vectors

`03-graph-and-vectors.mp4`, 1:50 to 2:24.

Picture:

- A question that names Roylott walks the graph to the swamp adder and the passage.
- A question that only describes the death searches the vectors, lands on the same passage, and returns to the same fact.

## 5. Bring the ontology

`04-bring-ontology.mp4`, 2:24 to 2:54.

Picture:

- Normal ingestion. Documents are divided into passages. An ontology you bring drops into extraction.
- A fact enters the graph only when the passage contains it. One vector is stored for each passage.

## 6. Derive the ontology

`05-derive-ontology.mp4`, 2:54 to 3:25.

Picture:

- The other ingestion. Documents arrive with no ontology. A sample proposes Person, Case, and Cause.
- The proposals become a draft, a person publishes it, and that ontology drops into the same extraction. The graph and the vectors are built the same way.

## 7. The chat

`06-when-someone-asks.mp4`, 3:25 to 4:01.

Picture:

- A chat message, What killed Dr Roylott, enters an agent that holds the ontology. The agent walks the graph, reads the cited passage, and a check keeps the statement because the quote is in the passage.
- The result returns in the chat: a swamp adder, with the Speckled Band passage.
- A second message, Holmes's mother's name, takes the same path. Nothing survives the check. The result in the chat is a decline.

## 8. What is better

`07-what-is-better.mp4`, 4:01 to 4:57.

Picture:

- Left, the kept result: a swamp adder, with a small Speckled Band passage, in cyan.
- Beside it, the declined result: the sources do not say, in danger.
- One line: the graph is for the connection, and the vectors are for the wording.
- Then two steps: bring or publish an ontology, and ask, keeping only what a passage supports.

