# Professional voice

For a narrator in the style of a serious technical film: unhurried, precise, no sales language. Read each clip as continuous prose. Pause between the paragraphs.

## 1. The purpose

Clip `00-purpose.mp4`. Assembly 0:00 to 0:31.

This briefing introduces the concepts behind the Patternode Knowledge Store lab, provided as open source on GitHub. It shows how an agent can answer from source content without inventing what was never said in the source text. We discuss how the usual approach fails, how graph and vector search belong together and how to try this open-source store on your own documents.

## 2. The collection

Clip `00-the-collection.mp4`. Assembly 0:31 to 1:06.

A collection, sometimes called a corpus, is the set of documents an agent is allowed to answer from. Here we use the full text of three Sherlock Holmes books: the Adventures, the Memoirs, and the Return. These are provided in the Knowledge Store lab. This example collection is a stand-in for any set of documents.

## 3. The usual path

Clip `01-usual-path.mp4`. Assembly 1:06 to 1:59.

An agent that answers from a company's own documents usually takes one path. The documents are cut into chunks and stored as vectors. A question retrieves the nearest chunks, and the agent writes a sentence. A naive or blunt force approach is to have the agent retrieve unindexed text via tools an ad hoc manner.

Say a user in a chat session asks where Professor Moriarty was born. The stories never say where. The nearest chunk calls him a man of good birth and excellent education. The model can still write that phrase, and attach a citation afterwards. The words were there. But they do not name a place.

## 4. Ontology and graph

Clip `02-ontology-and-graph.mp4`. Assembly 1:59 to 2:41.

An ontology is the picture of what concepts a collection contains. It names the kinds of things, and the links between them. A person. A story. A place. A person appears in a story. A person meets someone at a place.

A knowledge graph is that picture, filled in. Professor Moriarty appears in The Final Problem. That story brings him and Holmes to the Reichenbach Falls. Each fact points to a passage. In a knowledge graph, facts are expressed as nodes and relationships as links between nodes.

## 5. Graph and vectors

Clip `03-graph-and-vectors.mp4`. Assembly 2:41 to 3:52.

The same fact can be reached by walking the names in the graph, or by matching a description of the scene to the passage.

When a question includes names that are in the graph, the agent can walk the graph. A search for "Where does Professor Moriarty appear?" starts at the person node, follows the "appears in" link to the story node, and continues to Reichenbach Falls as a location type fact. The passage is already attached to that final fact.

That walk can start only when the question contains those names. Someone who does not remember them might describe the scene instead, and ask about two rivals falling at a waterfall. Those words are not nodes. The agent compares them with the passages by meaning, and the passage about the Reichenbach Falls matches. That passage is already linked to Moriarty, so the answer is the same fact.

## 6. Bring the ontology

Clip `04-bring-ontology.mp4`. Assembly 3:52 to 4:24.

If you already have the vocabulary, you bring the ontology with the documents. They are divided into passages. Extraction reads each passage through the ontology you brought.

A fact is kept in the graph only when a passage contains it. The Final Problem names Moriarty and the Reichenbach Falls, so that fact stays. The lab builds the graph, and one vector for each passage.

## 7. Derive the ontology

Clip `05-derive-ontology.mp4`. Assembly 4:24 to 4:56.

If you do not bring an ontology, the documents arrive on their own. The lab reads a sample and proposes the kinds of things they mention, and the links that should be allowed. A person publishes that draft.

Then the same extraction runs. The graph and the vectors are built the same way. A fact still has to be in the passage.

## 8. The chat

Clip `06-when-someone-asks.mp4`. Assembly 4:56 to 5:38.

A person types a message in the chat as "Where does Professor Moriarty appear?". The agent walks from the person to the story, and the cited passage is read. It is in The Final Problem, so the statement stays. The result is that story, with the passage beside it.

Where he was born takes the same path. It meets the phrase a man of good birth, and nothing that names a place. The result is a decline. The sources do not say. So no hallucination results.

## 9. What is better

Clip `07-what-is-better.mp4`. Assembly 5:38 to 6:15.

A graph and the vectors do different work. The graph holds what is connected to what, and of what kind. The vectors hold wording that the question never used. A result comes back only when a passage supports it. The Final Problem stays in the results, because that story says where Moriarty appears. Where he was born does not, because the collection never names a place.

## 10. Try it

Clip `08-try-it.mp4`. Assembly 6:15 to 7:05.

Here is what we just covered. Nearest words can attach a citation to the wrong fact. A graph holds the connection, and vectors find the wording. A result stays only when a passage supports it. Professor Moriarty appears in The Final Problem, at the Reichenbach Falls. Where he was born, the sources do not say. Try it out in your own AWS infrastructure using the Knowledge Store lab from Patternode on GitHub.

To try it, go to the public repository, github.com/patternode/knowledge-store. Clone it. It is open source. The deploy guide shows how to run it in your own AWS account, on your own documents.

