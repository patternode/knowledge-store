# Record yourself

Read each clip straight through, as if explaining the diagram to a room. Pause between the paragraphs. The clip is long enough for this read at a measured pace.

## 1. The collection

Clip `00-the-collection.mp4`. Assembly 0:00 to 0:35.

These examples use one collection. A collection, sometimes called a corpus, is the set of documents an agent is allowed to answer from. Here, that set is three Sherlock Holmes books: the Adventures, the Memoirs, and the Return.

It is a stand-in. The same pictures apply to your own documents, a research library, or any other collection. Nothing in the method depends on these particular stories.

## 2. The usual path

Clip `01-usual-path.mp4`. Assembly 0:35 to 1:20.

An agent answering from your own documents usually works like this. The pages are cut into chunks and stored as vectors. A question pulls back the chunks nearest in meaning, and the agent writes a sentence.

Take a question the stories do not answer: the name of Sherlock Holmes's mother. Nothing in the collection says it. The nearest chunks are about other mothers, including Helen Stoner's. From those words the model can write a name, and a citation gets attached after the sentence exists. The words were there. They were about someone else.

## 3. Ontology and graph

Clip `02-ontology-and-graph.mp4`. Assembly 1:20 to 2:04.

An ontology is a picture of what these documents are allowed to mean. The kinds of things, and the links you permit. A person. A case. A cause. A person investigates a case. A person is killed by a cause.

The knowledge graph is that picture filled in. Holmes investigates the Speckled Band. Dr Roylott is killed by a swamp adder. Every fact points back to the passage it came from. The agent can follow a connection, instead of hoping the right words sit next to each other.

## 4. Graph and vectors

Clip `03-graph-and-vectors.mp4`. Assembly 2:04 to 2:46.

Ask what killed Dr Roylott, and the graph is enough. Person, killed by, cause, and the passage is already on the fact.

Ask it another way. A doctor dies of a snake in his own room, and the wording does not match the page. The vectors find that page by meaning. Because each fact cites a passage, the search leads back to the same fact. Structure in the graph. Wording in the vectors.

## 5. Bring the ontology

Clip `04-bring-ontology.mp4`. Assembly 2:46 to 3:23.

This is the path when you bring the ontology. Documents come in and stay as they arrived. They are split into passages you can cite. The ontology you brought sits beside that flow, and extraction reads each passage in those types.

A fact is kept only when the passage contains it. The Speckled Band names the swamp adder, so that fact enters the graph. Beside the graph, one vector for each passage.

## 6. Derive the ontology

Clip `05-derive-ontology.mp4`. Assembly 3:23 to 4:07.

This is the path when you do not bring an ontology. The same documents come in. A sample of them is read, and the lab proposes the kinds of things they talk about, and the links between those kinds. That becomes a draft. You look at it, and you publish it.

From there it is the same flow. Passages are read into the ontology that was derived from them. The graph and the vectors are built the same way, and a fact still has to be in the passage.

## 7. The chat

Clip `06-when-someone-asks.mp4`. Assembly 4:07 to 5:07.

Someone types in the chat. The agent has the ontology, so it plans in those types. If the message names something, it follows the graph. What killed Dr Roylott goes from the person to the cause, and the passage on that fact is read.

The agent offers a statement and a quote from the passage. The quote is checked. The Speckled Band does say swamp adder, so that statement stays. What you see in the chat is the swamp adder, and the passage it came from.

Type the other question, and it is the same path. Holmes's mother's name meets other mothers, not his. Nothing survives the check. The chat declines.

