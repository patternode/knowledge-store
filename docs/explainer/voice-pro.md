# Professional voice

For a narrator in the style of a serious technical film: unhurried, precise, no sales language. Read each clip as continuous prose. Pause between the paragraphs. Do not break it into the sentences on screen.

## 1. The usual path

Clip `01-usual-path.mp4`. Assembly 0:00 to 0:49.

An agent that answers from a company's own documents usually takes one path. The documents are cut into chunks and stored as vectors, so that a question can retrieve the pieces nearest to it in meaning. The agent reads what came back and writes the answer.

That is enough when the question and the source use the same words. It becomes unreliable when the answer depends on a relationship, on what kind of thing something is, or on a fact that was written in different words somewhere else. The model supplies what the chunks did not. The sentence sounds complete. A citation, when there is one, is attached after the sentence has already been written.

## 2. Ontology and graph

Clip `02-ontology-and-graph.mp4`. Assembly 0:49 to 1:34.

An ontology is the shared vocabulary for a body of knowledge. It names the kinds of things that matter in that domain, and the relationships that are allowed between them. A contract has parties. A person reports to a role. A case has a client.

A knowledge graph is the facts, written in that vocabulary. Each fact is a small typed statement, and each one can point back to the passage of text it came from. An agent that can see the ontology no longer has to guess which words to search for. It can ask what is connected to what, and of what kind.

## 3. Graph and vectors

Clip `03-graph-and-vectors.mp4`. Assembly 1:34 to 2:23.

The graph is the right instrument when a question names things. Many questions do not. They describe a situation, and they share no wording with the page that answers them. Vector search finds that page by meaning.

Used on its own, vector search hands the model a passage and leaves the model to write. Used with the graph, the two stay joined. A search by meaning returns a passage. The facts in the graph cite passages. A hit among the vectors is a way back to the structured facts, and a fact in the graph is a way back to the words. The graph holds the structure. The vectors hold the wording the question never used.

## 4. What improves

Clip `04-what-improves.mp4`. Assembly 2:23 to 3:08.

Two things improve, and they improve for different reasons. Consistency comes from the ontology. The same types and the same relationships are used when facts are taken from the documents and when a question is asked, so two questions about the same thing follow the same paths.

Accuracy comes from the tie to a source. The model may propose a statement. A person sees that statement only when a passage actually contains it. A statement that cannot be tied to a source is removed. When nothing remains, the agent says that the sources do not answer. The citation is the condition for the sentence being shown.

## 5. On the way in

Clip `05-on-the-way-in.mp4`. Assembly 3:08 to 4:07.

The knowledge store is one implementation of that idea. On the way in, documents are kept as they arrived. They are divided into passages: stable pieces of text, small enough to cite, and stable enough that the same document produces the same passages again.

An ontology defines the types for that collection. You can bring the ontology with you, or the lab can draft one from the documents for a person to review and publish. Extraction reads each document into those types. A proposed fact has to be present in the passage it cites. Something the ontology has no place for stays out of the graph until a person publishes a version that includes it. From that record the lab builds the two stores the agent will use: the knowledge graph, and a vector index with one vector for each passage.

## 6. When someone asks

Clip `06-when-someone-asks.mp4`. Assembly 4:07 to 5:11.

When a person asks a question, the agent is given that same ontology, and it plans in the collection's own types. A question that names something follows the graph. A question that describes a situation searches the passages by meaning, and returns to the facts that cite what it found. The agent answers in statements. Each statement is tied to a passage. The page is built only from the statements that hold.

In the Sherlock Holmes stories this lab can be loaded with, a question about what killed Dr Grimesby Roylott can be answered from the passage that names the swamp adder. A question about the name of Sherlock Holmes's mother cannot. The stories do not say, and the result is a decline. Ingestion and questions are the same rule, run in opposite directions. A fact enters only when a passage supports it. An answer leaves only when a passage supports it.

