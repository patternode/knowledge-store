# Record yourself

Read each clip straight through, as if explaining the diagram to a room. Pause between the paragraphs. The clip is long enough for this read at a measured pace.

## 1. The collection

Clip `00-the-collection.mp4`. Assembly 0:00 to 0:35.

These examples use one collection. A collection, sometimes called a corpus, is the set of documents an agent is allowed to answer from. Here, that set is three Sherlock Holmes books: the Adventures, the Memoirs, and the Return.

It is a stand-in for your own documents. The usual way, then why a graph belongs with the vectors, then how a collection becomes that graph, then what to do next.

## 2. The usual path

Clip `01-usual-path.mp4`. Assembly 0:35 to 1:15.

An agent answering from your own documents usually works like this. The pages are cut into chunks and stored as vectors. A question pulls back the nearest chunks, and the agent writes a sentence.

The stories never name Sherlock Holmes's mother. The nearest chunks are about other mothers, including Helen Stoner's mother, Mrs Stoner. From those words the model can write that name, and a citation gets attached afterwards. The words were there. They were about someone else.

## 3. Ontology and graph

Clip `02-ontology-and-graph.mp4`. Assembly 1:15 to 1:50.

An ontology is a picture of what these documents are allowed to mean. The kinds of things, and the links you permit. A person. A case. A cause. A person investigates a case. A person is killed by a cause.

The knowledge graph is that picture filled in. Holmes investigates the Speckled Band. Dr Roylott is killed by a swamp adder. Every fact points at a passage.

## 4. Graph and vectors

Clip `03-graph-and-vectors.mp4`. Assembly 1:50 to 2:24.

Ask what killed Dr Roylott, and the graph is enough. Person, killed by, cause, and the passage is already on the fact.

Instead, a doctor dies of a snake in his own room. The vectors find that passage by meaning and return to the same fact. The graph holds the connection. The vectors hold the wording the question never used.

## 5. Bring the ontology

Clip `04-bring-ontology.mp4`. Assembly 2:24 to 2:54.

This is the path when you bring the ontology. Documents stay as they arrived and are split into passages to cite. Extraction reads each passage in the types you brought.

A fact is kept only when the passage contains it. The Speckled Band names the swamp adder, so that fact stays. One vector is stored for each passage.

## 6. Derive the ontology

Clip `05-derive-ontology.mp4`. Assembly 2:54 to 3:25.

This is the path when you do not bring an ontology. The documents come in. A sample is read, and the lab proposes the kinds of things they talk about. You publish that draft.

Then the same extraction runs. The graph and the vectors are built the same way. A fact still has to be in the passage.

## 7. The chat

Clip `06-when-someone-asks.mp4`. Assembly 3:25 to 4:01.

Someone types in the chat. What killed Dr Roylott goes from the person to the cause, and the passage on that fact is read. The Speckled Band says swamp adder, so the statement stays. You see a swamp adder, with that passage beside it.

Ask for Holmes's mother's name. It meets other mothers, not his. The chat declines. The sources do not say.

## 8. What is better

Clip `07-what-is-better.mp4`. Assembly 4:01 to 4:57.

A graph and the vectors do different work. The graph holds what is connected to what, and of what kind. The vectors hold wording the question never used. A result comes back only when a passage supports it. The swamp adder stays, because the Speckled Band says so. Holmes's mother's name does not, because the collection never gives it. A sentence no longer gets a citation after it has been written.

The next step is the same for your own documents. Bring an ontology, or let the documents propose one and you publish it. Then ask. What the sources support comes back, with the passage beside it. What they do not say is left unsaid.

