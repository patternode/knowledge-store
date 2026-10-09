# Professional voice

For a narrator in the style of a serious technical film: unhurried, precise, no sales language. Read each clip as continuous prose. Pause between the paragraphs.

## 1. The collection

Clip `00-the-collection.mp4`. Assembly 0:00 to 0:35.

The examples that follow use one collection. A collection, sometimes called a corpus, is the set of documents an agent is allowed to answer from. Here that set is three Sherlock Holmes books: the Adventures, the Memoirs, and the Return.

It is a stand-in for any documents. The usual way, then why a graph belongs with the vectors, then how a collection becomes that graph, then what to do next.

## 2. The usual path

Clip `01-usual-path.mp4`. Assembly 0:35 to 1:15.

An agent that answers from a company's own documents usually takes one path. The documents are cut into chunks and stored as vectors. A question retrieves the nearest chunks, and the agent writes a sentence.

The question is the name of Sherlock Holmes's mother. The stories never give it. The nearest chunks are about other mothers, including Helen Stoner's mother, Mrs Stoner. The model can still write that name, and attach a citation afterwards. The words were there. The relationship was not.

## 3. Ontology and graph

Clip `02-ontology-and-graph.mp4`. Assembly 1:15 to 1:50.

An ontology is the picture of what a collection is allowed to say. It names the kinds of things, and the links between them. A person. A case. A cause. A person investigates a case. A person is killed by a cause.

A knowledge graph is that picture, filled in. Holmes investigates the Speckled Band. Dr Roylott is killed by a swamp adder. Each fact points at a passage.

## 4. Graph and vectors

Clip `03-graph-and-vectors.mp4`. Assembly 1:50 to 2:24.

When a question names things, the graph is the path. What killed Dr Roylott walks from the person, along killed by, to the cause. The passage comes with the fact.

Instead, a doctor dies of a snake in his own room. The vectors find that passage by meaning and return to the same fact. The graph holds the connection. The vectors hold the wording the question never used.

## 5. Bring the ontology

Clip `04-bring-ontology.mp4`. Assembly 2:24 to 2:54.

If you already have the vocabulary, you bring the ontology with the documents. They are divided into passages. Extraction reads each passage through the ontology you brought.

A fact is kept only when the passage contains it. The swamp adder stays, because The Speckled Band says so. The lab builds the graph, and one vector for each passage.

## 6. Derive the ontology

Clip `05-derive-ontology.mp4`. Assembly 2:54 to 3:25.

If you do not bring an ontology, the documents arrive on their own. The lab reads a sample and proposes the kinds of things they mention, and the links that should be allowed. A person publishes that draft.

Then the same extraction runs. The graph and the vectors are built the same way. A fact still has to be in the passage.

## 7. The chat

Clip `06-when-someone-asks.mp4`. Assembly 3:25 to 4:01.

A person types a message in the chat. What killed Dr Roylott walks from the person to the cause, and the cited passage is read. It is in The Speckled Band, so the statement stays. The result is a swamp adder, with that passage beside it.

Holmes's mother's name takes the same path. It meets other mothers, and nothing that names his. The result is a decline. The sources do not say.

## 8. What is better

Clip `07-what-is-better.mp4`. Assembly 4:01 to 4:57.

A graph and the vectors do different work. The graph holds what is connected to what, and of what kind. The vectors hold wording the question never used. A result comes back only when a passage supports it. The swamp adder stays, because the Speckled Band says so. Holmes's mother's name does not, because the collection never gives it. A sentence no longer receives a citation after it has been written.

The next step is the same on any collection. Bring an ontology, or let the documents propose one and have a person publish it. Then ask. What the sources support is returned, with the passage beside it. What they do not say is left unsaid.

