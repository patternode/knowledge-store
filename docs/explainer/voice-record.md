# Record yourself

Read each clip straight through, as if explaining it to a room. The paragraphs are the whole read for that picture. Pause between paragraphs. The clip is long enough for this read at a measured pace.

## 1. The usual path

Clip `01-usual-path.mp4`. Assembly 0:00 to 0:49.

An agent that answers from your own documents usually works like this. The documents are cut into chunks and stored as vectors, so a question can pull back the pieces nearest to it in meaning. The agent reads what came back and writes the answer.

That is enough when the question and the source use the same words. It gets unreliable when the answer depends on a relationship, on what kind of thing something is, or on a fact written in different words somewhere else. The model fills in what the chunks did not say. The sentence sounds finished. If there is a citation, it is attached after the sentence already exists.

## 2. Ontology and graph

Clip `02-ontology-and-graph.mp4`. Assembly 0:49 to 1:34.

An ontology is a shared vocabulary for a body of knowledge. It names the kinds of things that matter, and the relationships that are allowed between them. A contract has parties. A person reports to a role. A case has a client.

A knowledge graph is those facts, written in that vocabulary. Each fact is a small typed statement, and each one can point back to the passage it came from. An agent that can see the ontology does not have to guess which words to search for. It can ask what is connected to what, and of what kind.

## 3. Graph and vectors

Clip `03-graph-and-vectors.mp4`. Assembly 1:34 to 2:23.

The graph is what you want when a question names things. Many questions do not. They describe a situation, and they share no words with the page that answers them. Vector search finds that page by meaning.

On its own, vector search hands the model a passage and leaves the model to write. With the graph, the two stay joined. A search by meaning returns a passage. The facts in the graph cite passages. So a hit in the vectors leads back to the structured facts, and a fact in the graph leads back to the words. The graph holds the structure. The vectors hold the wording the question never used.

## 4. What improves

Clip `04-what-improves.mp4`. Assembly 2:23 to 3:08.

Two things get better, and they get better for different reasons. Consistency comes from the ontology. The same types and the same relationships are used when facts are taken from the documents and when a question is asked, so two questions about the same thing follow the same paths.

Accuracy comes from the tie to a source. The model can propose a statement. You see that statement only when a passage actually contains it. A statement that cannot be tied to a source is removed. When nothing is left, the agent says the sources do not answer. The citation is the condition for showing the sentence.

## 5. On the way in

Clip `05-on-the-way-in.mp4`. Assembly 3:08 to 4:07.

This lab is one way of doing that. On the way in, documents are kept as they arrived. They are divided into passages: pieces of text small enough to cite, and stable enough that the same document gives the same passages again.

An ontology defines the types for the collection. You can bring that ontology, or the lab can draft one from the documents and leave it for a person to review and publish. Extraction reads each document into those types. A proposed fact has to appear in the passage it cites. If the ontology has no place for a term, that term stays out of the graph until someone publishes a version that includes it. From that record the lab builds the two stores the agent uses: the knowledge graph, and a vector index with one vector for each passage.

## 6. When someone asks

Clip `06-when-someone-asks.mp4`. Assembly 4:07 to 5:11.

When someone asks a question, the agent is given that same ontology, and it plans in the collection's own types. If the question names something, it follows the graph. If the question describes a situation, it searches the passages by meaning, and comes back to the facts that cite what it found. It answers in statements, and each statement is tied to a passage. The page is built only from the statements that hold.

In the Sherlock Holmes stories loaded here, asking what killed Dr Grimesby Roylott can be answered from the passage that names the swamp adder. Asking for the name of Sherlock Holmes's mother cannot. The stories do not say, and the result is a decline. Putting documents in, and answering questions, are the same rule run in opposite directions. A fact goes in only when a passage supports it. An answer comes out only when a passage supports it.

