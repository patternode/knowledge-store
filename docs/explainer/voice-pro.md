# Professional voice

For a narrator in the style of a serious technical film: unhurried, precise, no sales language. Read each clip as continuous prose. Pause between the paragraphs.

## 1. The usual path

Clip `01-usual-path.mp4`. Assembly 0:00 to 0:45.

An agent that answers from a company's own documents usually takes one path. The documents are cut into chunks and stored as vectors. A question retrieves the chunks nearest to it in meaning, and the agent writes a sentence from them.

Here the question is the name of Sherlock Holmes's mother. The stories never give it. The nearest chunks are about other mothers, including Helen Stoner's. The model can still write her mother's name, and attach a citation once the sentence exists. The words were in the collection. The relationship was not.

## 2. Ontology and graph

Clip `02-ontology-and-graph.mp4`. Assembly 0:45 to 1:30.

An ontology is the picture of what a collection is allowed to say. It names the kinds of things, and the links between them. A person. A case. A cause. A person investigates a case. A person is killed by a cause.

A knowledge graph is that picture, filled in from the documents. Holmes investigates the Speckled Band. Dr Grimesby Roylott is killed by a swamp adder. Each fact points back to the passage that said it. The agent can ask what is connected to what, and of what kind.

## 3. Graph and vectors

Clip `03-graph-and-vectors.mp4`. Assembly 1:30 to 2:12.

When a question names things, the graph is the path. What killed Dr Roylott walks from the person, along killed by, to the cause, and the passage comes with the fact.

When a question describes a situation, the words may not match. A doctor dies of a snake in his own room. Vector search finds the passage by meaning. The facts cite passages, so that hit leads back to the same fact. The graph holds the structure. The vectors hold the wording the question never used.

## 4. Bring the ontology

Clip `04-bring-ontology.mp4`. Assembly 2:12 to 2:49.

If you already have the vocabulary, you bring the ontology with the documents. The documents are kept as they arrived, and divided into passages small enough to cite. Extraction reads each passage through the ontology you brought.

A fact is kept only when that passage contains it. Roylott, killed by, a swamp adder, stays, because The Speckled Band says so. From that record the lab builds the graph, and one vector for each passage.

## 5. Derive the ontology

Clip `05-derive-ontology.mp4`. Assembly 2:49 to 3:32.

If you do not bring an ontology, the documents arrive on their own. The lab reads a sample and proposes the kinds of things they keep mentioning, and the links that should be allowed. Those proposals become a draft. A person reviews it and publishes it.

Then the same extraction runs. Passages are read into the vocabulary that came from the documents, and the graph and the vectors are built in the same way. The ontology was derived. A fact still has to be in the passage.

## 6. The chat

Clip `06-when-someone-asks.mp4`. Assembly 3:32 to 4:33.

A person types a message in the chat. The agent is given the collection's ontology, and it plans in those types. A message that names something follows the graph. What killed Dr Roylott walks from the person to the cause, and the passage cited by that fact is read.

The agent proposes a statement, with a quote taken from the passage. The quote is checked. It is in The Speckled Band, so the statement stays. The result in the chat is the swamp adder, with that passage beside it.

A second message takes the same path. The name of Sherlock Holmes's mother meets other mothers in the stories, and nothing that names his. No statement survives the check. The result in the chat is a decline.

