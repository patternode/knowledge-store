# Knowledge Store briefing

Ten clips. The picture is an architecture diagram of the flow.

Two complete reads, one per clip, in prose:

- [voice-pro.md](voice-pro.md) for a professional technical narrator.
- [voice-record.md](voice-record.md) to record yourself. Read the paragraphs for that clip straight through.

The clips are timed to the longer of the two reads, at about 130 words a minute, with a short breath at each end.

## Timeline

| In | Out | Clip | Picture |
|---|---|---|---|
| 0:00 | 0:31 | `00-purpose.mp4` | The purpose |
| 0:31 | 1:06 | `00-the-collection.mp4` | The collection |
| 1:06 | 1:59 | `01-usual-path.mp4` | The usual path |
| 1:59 | 2:41 | `02-ontology-and-graph.mp4` | Ontology and graph |
| 2:41 | 3:52 | `03-graph-and-vectors.mp4` | Graph and vectors |
| 3:52 | 4:24 | `04-bring-ontology.mp4` | Bring the ontology |
| 4:24 | 4:56 | `05-derive-ontology.mp4` | Derive the ontology |
| 4:56 | 5:38 | `06-when-someone-asks.mp4` | The chat |
| 5:38 | 6:15 | `07-what-is-better.mp4` | What is better |
| 6:15 | 7:05 | `08-try-it.mp4` | Try it |

Total picture: 7:05 (425.2 seconds).

## 1. The purpose

`00-purpose.mp4`, 0:00 to 0:31.

Picture:

- One line: an agent that does not invent what the documents never said.
- Three beats: the usual way, a graph with vectors, then how to try the open-source store.

## 2. The collection

`00-the-collection.mp4`, 0:31 to 1:06.

Picture:

- Three story pages: Adventures, Memoirs, and Return, labeled as the collection used in this briefing.
- A short line: a collection, also called a corpus, is the set of documents an agent answers from.
- A quieter mark: this set is a stand-in, and the same pictures apply to any documents.

## 3. The usual path

`01-usual-path.mp4`, 1:06 to 1:59.

Picture:

- Three story collections become a field of vectors. The question is where Professor Moriarty was born.
- The lit chunk says he is a man of good birth. A sentence is written from it, and a citation is pinned on afterwards.

## 4. Ontology and graph

`02-ontology-and-graph.mp4`, 1:59 to 2:41.

Picture:

- Left, an ontology draws itself: Person, Story, Place, and the two links that are allowed.
- Right, the same picture filled in. Moriarty appears in The Final Problem, and meets Holmes at the Reichenbach Falls. A passage sits on the fact.

## 5. Graph and vectors

`03-graph-and-vectors.mp4`, 2:41 to 3:52.

Picture:

- One line: the same fact can be reached by walking the names, or by matching a description to the passage.
- A question that names Moriarty walks the person node, along appears in, to the story and the falls. The passage is already on that fact.
- A question that only describes two rivals at a waterfall is matched to the Reichenbach passage, which is already linked to Moriarty.

## 6. Bring the ontology

`04-bring-ontology.mp4`, 3:52 to 4:24.

Picture:

- Normal ingestion. Documents are divided into passages. An ontology you bring drops into extraction.
- A fact enters the graph only when the passage contains it. One vector is stored for each passage.

## 7. Derive the ontology

`05-derive-ontology.mp4`, 4:24 to 4:56.

Picture:

- The other ingestion. Documents arrive with no ontology. A sample proposes Person, Story, and Place.
- The proposals become a draft, a person publishes it, and that ontology drops into the same extraction. The graph and the vectors are built the same way.

## 8. The chat

`06-when-someone-asks.mp4`, 4:56 to 5:38.

Picture:

- A chat message, Where does Professor Moriarty appear, enters an agent that holds the ontology. The agent walks the graph, reads the cited passage, and a check keeps the statement because the quote is in the passage.
- The result returns in the chat: The Final Problem, with that passage.
- A second message, where he was born, takes the same path. Nothing survives the check. The result in the chat is a decline.

## 9. What is better

`07-what-is-better.mp4`, 5:38 to 6:15.

Picture:

- Left, the kept result: The Final Problem, with that passage, in cyan.
- Beside it, the declined result: the sources do not say, in danger.
- One line: the graph is for the connection, and the vectors are for the wording.

## 10. Try it

`08-try-it.mp4`, 6:15 to 7:05.

Picture:

- A one-line recap: Moriarty appears in The Final Problem. His birthplace is not in the sources.
- Three steps: the public repository, clone it, your own AWS account.

