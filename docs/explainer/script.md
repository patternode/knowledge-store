# Knowledge Store briefing

Ten clips. The picture is an architecture diagram of the flow.

Two complete reads, one per clip, in prose:

- [voice-pro.md](voice-pro.md) for a professional technical narrator.
- [voice-record.md](voice-record.md) to record yourself. Read the paragraphs for that clip straight through.

The clips are timed to the longer of the two reads, at about 130 words a minute, with a short breath at each end.

## Timeline

| In | Out | Clip | Picture |
|---|---|---|---|
| 0:00 | 0:21 | `00-purpose.mp4` | The purpose |
| 0:21 | 0:56 | `00-the-collection.mp4` | The collection |
| 0:56 | 1:36 | `01-usual-path.mp4` | The usual path |
| 1:36 | 2:13 | `02-ontology-and-graph.mp4` | Ontology and graph |
| 2:13 | 2:49 | `03-graph-and-vectors.mp4` | Graph and vectors |
| 2:49 | 3:20 | `04-bring-ontology.mp4` | Bring the ontology |
| 3:20 | 3:51 | `05-derive-ontology.mp4` | Derive the ontology |
| 3:51 | 4:30 | `06-when-someone-asks.mp4` | The chat |
| 4:30 | 5:07 | `07-what-is-better.mp4` | What is better |
| 5:07 | 5:50 | `08-try-it.mp4` | Try it |

Total picture: 5:50 (349.7 seconds).

## 1. The purpose

`00-purpose.mp4`, 0:00 to 0:21.

Picture:

- One line: an agent that does not invent what the documents never said.
- Three beats: the usual way, a graph with vectors, then how to try the open-source store.

## 2. The collection

`00-the-collection.mp4`, 0:21 to 0:56.

Picture:

- Three story pages: Adventures, Memoirs, and Return, labeled as the collection used in this briefing.
- A short line: a collection, also called a corpus, is the set of documents an agent answers from.
- A quieter mark: this set is a stand-in, and the same pictures apply to any documents.

## 3. The usual path

`01-usual-path.mp4`, 0:56 to 1:36.

Picture:

- Three story collections become a field of vectors. The question is where Professor Moriarty was born.
- The lit chunk says he is a man of good birth. A sentence is written from it, and a citation is pinned on afterwards.

## 4. Ontology and graph

`02-ontology-and-graph.mp4`, 1:36 to 2:13.

Picture:

- Left, an ontology draws itself: Person, Story, Place, and the two links that are allowed.
- Right, the same picture filled in. Moriarty appears in The Final Problem, and meets Holmes at the Reichenbach Falls. A passage sits on the fact.

## 5. Graph and vectors

`03-graph-and-vectors.mp4`, 2:13 to 2:49.

Picture:

- A question that names Moriarty walks the graph to The Final Problem and the passage.
- A question that only describes the waterfall searches the vectors, lands on the same passage, and returns to the same fact.

## 6. Bring the ontology

`04-bring-ontology.mp4`, 2:49 to 3:20.

Picture:

- Normal ingestion. Documents are divided into passages. An ontology you bring drops into extraction.
- A fact enters the graph only when the passage contains it. One vector is stored for each passage.

## 7. Derive the ontology

`05-derive-ontology.mp4`, 3:20 to 3:51.

Picture:

- The other ingestion. Documents arrive with no ontology. A sample proposes Person, Story, and Place.
- The proposals become a draft, a person publishes it, and that ontology drops into the same extraction. The graph and the vectors are built the same way.

## 8. The chat

`06-when-someone-asks.mp4`, 3:51 to 4:30.

Picture:

- A chat message, Where does Professor Moriarty appear, enters an agent that holds the ontology. The agent walks the graph, reads the cited passage, and a check keeps the statement because the quote is in the passage.
- The result returns in the chat: The Final Problem, with that passage.
- A second message, where he was born, takes the same path. Nothing survives the check. The result in the chat is a decline.

## 9. What is better

`07-what-is-better.mp4`, 4:30 to 5:07.

Picture:

- Left, the kept result: The Final Problem, with that passage, in cyan.
- Beside it, the declined result: the sources do not say, in danger.
- One line: the graph is for the connection, and the vectors are for the wording.

## 10. Try it

`08-try-it.mp4`, 5:07 to 5:50.

Picture:

- A one-line recap: Moriarty appears in The Final Problem. His birthplace is not in the sources.
- Three steps: the public repository, clone it, your own AWS account.

