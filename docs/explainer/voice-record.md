# Record yourself

Read each clip straight through, as if explaining the diagram to a room. Pause between the paragraphs. The clip is long enough for this read at a measured pace.

## 1. The purpose

Clip `00-purpose.mp4`. Assembly 0:00 to 0:21.

This briefing shows how an agent can answer from your own documents without inventing what they never said. The usual way fails. A graph and a vector search belong together. Then, how to try this open-source store yourself.

## 2. The collection

Clip `00-the-collection.mp4`. Assembly 0:21 to 0:56.

These examples use one collection. A collection, sometimes called a corpus, is the set of documents an agent is allowed to answer from. Here, that set is three Sherlock Holmes books: the Adventures, the Memoirs, and the Return.

It is a stand-in for your own documents. The usual way, then why a graph belongs with the vectors, then how a collection becomes that graph, then what to do next.

## 3. The usual path

Clip `01-usual-path.mp4`. Assembly 0:56 to 1:36.

An agent answering from your own documents usually works like this. The pages are cut into chunks and stored as vectors. A question pulls back the nearest chunks, and the agent writes a sentence.

Ask where Professor Moriarty was born. The stories never say. The nearest chunk calls him a man of good birth. From those words the model can write that phrase, and a citation gets attached afterwards. The words were there. They do not name a place.

## 4. Ontology and graph

Clip `02-ontology-and-graph.mp4`. Assembly 1:36 to 2:13.

An ontology is a picture of what these documents are allowed to mean. The kinds of things, and the links you permit. A person. A story. A place. A person appears in a story. A person meets someone at a place.

The knowledge graph is that picture filled in. Professor Moriarty appears in The Final Problem. That story brings him and Holmes to the Reichenbach Falls. Every fact points at a passage.

## 5. Graph and vectors

Clip `03-graph-and-vectors.mp4`. Assembly 2:13 to 2:49.

Ask where Professor Moriarty appears, and the graph is enough. Person, appears in, story, meets at the falls, and the passage is already on the fact.

Instead, two rivals fall together at a waterfall. The vectors find that passage by meaning and return to the same fact. The graph holds the connection. The vectors hold the wording the question never used.

## 6. Bring the ontology

Clip `04-bring-ontology.mp4`. Assembly 2:49 to 3:20.

This is the path when you bring the ontology. Documents stay as they arrived and are split into passages to cite. Extraction reads each passage in the types you brought.

A fact is kept only when the passage contains it. The Final Problem names Moriarty and the falls, so that fact stays. One vector is stored for each passage.

## 7. Derive the ontology

Clip `05-derive-ontology.mp4`. Assembly 3:20 to 3:51.

This is the path when you do not bring an ontology. The documents come in. A sample is read, and the lab proposes the kinds of things they talk about. You publish that draft.

Then the same extraction runs. The graph and the vectors are built the same way. A fact still has to be in the passage.

## 8. The chat

Clip `06-when-someone-asks.mp4`. Assembly 3:51 to 4:30.

Someone types in the chat. Where does Professor Moriarty appear goes from the person to the story, and the passage on that fact is read. The Final Problem does name him, so the statement stays. You see that story, with the passage beside it.

Ask where he was born. It meets a man of good birth, not a place. The chat declines. The sources do not say.

## 9. What is better

Clip `07-what-is-better.mp4`. Assembly 4:30 to 5:07.

A graph and the vectors do different work. The graph holds what is connected to what, and of what kind. The vectors hold wording the question never used. A result comes back only when a passage supports it. The Final Problem stays, because that story says where Moriarty appears. Where he was born does not, because the collection never names a place. A sentence no longer gets a citation after it has been written.

## 10. Try it

Clip `08-try-it.mp4`. Assembly 5:07 to 5:50.

Here is what we just covered. Nearest words can attach a citation to the wrong fact. A graph holds the connection, and vectors find the wording. A result stays only when a passage supports it. Professor Moriarty appears in The Final Problem, at the Reichenbach Falls. Where he was born, the sources do not say.

To try it, go to the public repository, github.com/patternode/knowledge-store. Clone it. It is open source. The deploy guide shows how to run it in your own AWS account, on your own documents.

