# Record yourself

Read each clip straight through, as if explaining the diagram to a room. Pause between the paragraphs. The clip is long enough for this read at a measured pace.

## 1. The usual path

Clip `01-usual-path.mp4`. Assembly 0:00 to 0:45.

An agent answering from your own documents usually works like this. The pages are cut into chunks and stored as vectors. A question pulls back the chunks nearest in meaning, and the agent writes a sentence.

Take a question the stories do not answer: the name of Sherlock Holmes's mother. Nothing in the collection says it. The nearest chunks are about other mothers, including Helen Stoner's. From those words the model can write a name, and a citation gets attached after the sentence exists. The words were there. They were about someone else.

## 2. Ontology and graph

Clip `02-ontology-and-graph.mp4`. Assembly 0:45 to 1:30.

An ontology is a picture of what these documents are allowed to mean. The kinds of things, and the links you permit. A person. A case. A cause. A person investigates a case. A person is killed by a cause.

The knowledge graph is that picture filled in. Holmes investigates the Speckled Band. Dr Roylott is killed by a swamp adder. Every fact points back to the passage it came from. The agent can follow a connection, instead of hoping the right words sit next to each other.

## 3. Graph and vectors

Clip `03-graph-and-vectors.mp4`. Assembly 1:30 to 2:12.

Ask what killed Dr Roylott, and the graph is enough. Person, killed by, cause, and the passage is already on the fact.

Ask it another way. A doctor dies of a snake in his own room, and the wording does not match the page. The vectors find that page by meaning. Because each fact cites a passage, the search leads back to the same fact. Structure in the graph. Wording in the vectors.

## 4. Bring the ontology

Clip `04-bring-ontology.mp4`. Assembly 2:12 to 2:49.

This is the path when you bring the ontology. Documents come in and stay as they arrived. They are split into passages you can cite. The ontology you brought sits beside that flow, and extraction reads each passage in those types.

A fact is kept only when the passage contains it. The Speckled Band names the swamp adder, so that fact enters the graph. Beside the graph, one vector for each passage.

## 5. Derive the ontology

Clip `05-derive-ontology.mp4`. Assembly 2:49 to 3:32.

This is the path when you do not bring an ontology. The same documents come in. A sample of them is read, and the lab proposes the kinds of things they talk about, and the links between those kinds. That becomes a draft. You look at it, and you publish it.

From there it is the same flow. Passages are read into the ontology that was derived from them. The graph and the vectors are built the same way, and a fact still has to be in the passage.

## 6. When someone asks

Clip `06-when-someone-asks.mp4`. Assembly 3:32 to 4:15.

Someone asks a question. The agent has the ontology, so it can plan in those types. Name a thing, and it walks the graph. Describe a situation, and it searches by meaning, then comes back to the facts on that passage. You only see a statement the passage supports.

Roylott is the swamp adder, from The Speckled Band. Holmes's mother is a decline. The stories do not say her name, and the answer does not borrow one.

