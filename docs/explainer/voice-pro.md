# Professional voice

For a narrator in the style of a serious technical film: unhurried, precise, no sales language. Read each clip as continuous prose. Pause between the paragraphs.

## 1. The purpose

Clip `00-purpose.mp4`. Assembly 0:00 to 0:21.

This briefing shows how an agent can answer from documents without inventing what they never said. The usual way fails. A graph and a vector search belong together. Then, how to try this open-source store on your own documents.

## 2. The collection

Clip `00-the-collection.mp4`. Assembly 0:21 to 0:56.

The examples that follow use one collection. A collection, sometimes called a corpus, is the set of documents an agent is allowed to answer from. Here that set is three Sherlock Holmes books: the Adventures, the Memoirs, and the Return.

It is a stand-in for any documents. The usual way, then why a graph belongs with the vectors, then how a collection becomes that graph, then what to do next.

## 3. The usual path

Clip `01-usual-path.mp4`. Assembly 0:56 to 1:36.

An agent that answers from a company's own documents usually takes one path. The documents are cut into chunks and stored as vectors. A question retrieves the nearest chunks, and the agent writes a sentence.

The question is where Professor Moriarty was born. The stories never say. The nearest chunk calls him a man of good birth and excellent education. The model can still write that phrase, and attach a citation afterwards. The words were there. They do not name a place.

## 4. Ontology and graph

Clip `02-ontology-and-graph.mp4`. Assembly 1:36 to 2:13.

An ontology is the picture of what a collection is allowed to say. It names the kinds of things, and the links between them. A person. A story. A place. A person appears in a story. A person meets someone at a place.

A knowledge graph is that picture, filled in. Professor Moriarty appears in The Final Problem. That story brings him and Holmes to the Reichenbach Falls. Each fact points at a passage.

## 5. Graph and vectors

Clip `03-graph-and-vectors.mp4`. Assembly 2:13 to 2:49.

When a question names things, the graph is the path. Where does Professor Moriarty appear walks from the person, along appears in, to the story, and on to the falls. The passage comes with the fact.

Instead, two rivals fall together at a waterfall. The vectors find that passage by meaning and return to the same fact. The graph holds the connection. The vectors hold the wording the question never used.

## 6. Bring the ontology

Clip `04-bring-ontology.mp4`. Assembly 2:49 to 3:20.

If you already have the vocabulary, you bring the ontology with the documents. They are divided into passages. Extraction reads each passage through the ontology you brought.

A fact is kept only when the passage contains it. The Final Problem names Moriarty and the Reichenbach Falls, so that fact stays. The lab builds the graph, and one vector for each passage.

## 7. Derive the ontology

Clip `05-derive-ontology.mp4`. Assembly 3:20 to 3:51.

If you do not bring an ontology, the documents arrive on their own. The lab reads a sample and proposes the kinds of things they mention, and the links that should be allowed. A person publishes that draft.

Then the same extraction runs. The graph and the vectors are built the same way. A fact still has to be in the passage.

## 8. The chat

Clip `06-when-someone-asks.mp4`. Assembly 3:51 to 4:30.

A person types a message in the chat. Where does Professor Moriarty appear walks from the person to the story, and the cited passage is read. It is in The Final Problem, so the statement stays. The result is that story, with the passage beside it.

Where he was born takes the same path. It meets the phrase a man of good birth, and nothing that names a place. The result is a decline. The sources do not say.

## 9. What is better

Clip `07-what-is-better.mp4`. Assembly 4:30 to 5:07.

A graph and the vectors do different work. The graph holds what is connected to what, and of what kind. The vectors hold wording the question never used. A result comes back only when a passage supports it. The Final Problem stays, because that story says where Moriarty appears. Where he was born does not, because the collection never names a place. A sentence no longer receives a citation after it has been written.

## 10. Try it

Clip `08-try-it.mp4`. Assembly 5:07 to 5:50.

Here is what we just covered. Nearest words can attach a citation to the wrong fact. A graph holds the connection, and vectors find the wording. A result stays only when a passage supports it. Professor Moriarty appears in The Final Problem, at the Reichenbach Falls. Where he was born, the sources do not say.

To try it, go to the public repository, github.com/patternode/knowledge-store. Clone it. It is open source. The deploy guide shows how to run it in your own AWS account, on your own documents.

