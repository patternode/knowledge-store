# Voice script

Record each section as its own take. The picture files have no narration.

Pace is about 160 words a minute. Each line is one sentence. Start the line at the cue. If you finish a line early, wait for the next cue rather than rushing the next sentence.

Say sha-256 as “sha two fifty-six”. Say SHACL as “shackle”. Say RDF as “R D F”. Say Turtle as the word for the format. Say the layer names bronze, silver, and gold as the metals: they are the names in the system, and the picture says what each one holds.

Leave the room tone at the start of each file for the half-second before the first cue.

## 1. The failure

File: `01-open.mp4`
Assembly: 0:00 to 0:22.

Voice only. The picture is the generated open.

Read:

`0:00.5` A retrieval system can still invent.

`0:02.8` It finds nearby text, and then the model writes the answer.

`0:06.8` That sentence is a paraphrase.

`0:08.8` A figure shifts.

`0:10.0` A relation appears that no passage stated.

`0:12.7` If a citation is added, it is attached afterwards.

`0:16.0` Knowing the model does not remove that step.

`0:19.0` The failure is the order of operations.

## 2. The rule

File: `02-rule.mp4`
Assembly: 0:22 to 0:39.

Voice only. The picture is the generated rule.

Read:

`0:00.5` Knowledge Store keeps the statement and the source together.

`0:03.8` A result is shown only when a passage contains it.

`0:07.5` The model proposes.

`0:08.8` Code checks that proposal against the text, and against the ontology.

`0:12.8` What fails is removed.

`0:14.4` If nothing remains, the system says so.

## 3. Ingestion

File: `03-ingestion.mp4`
Assembly: 0:39 to 2:45.

Voice only. The picture is the generated pipeline.

Read:

`0:00.5` Documents arrive as documents.

`0:02.0` An adapter lists them and fetches the bytes. It does not parse them, and it leaves the upload unchanged.

`0:08.9` Ingest stores each distinct file once, under the hash of its bytes.

`0:13.3` Two names for the same file are one object, and a version that has not changed is skipped.

`0:19.8` That copy is bronze, the immutable source.

`0:22.4` Refine writes silver: passages cut on a fixed rule, about eighteen hundred characters.

`0:27.2` The identifier is the document hash plus the hash of the passage, so a rerun keeps the same identifiers.

`0:34.0` Every fact cites one of those passages. That passage is the unit of evidence.

`0:39.1` What the documents are about is a separate ontology.

`0:42.5` A core vocabulary, shared by every collection, records only where a fact came from: the document, the passage, and the extraction run.

`0:50.4` You bring the domain ontology as Turtle, or the system drafts one once five documents are refined.

`0:56.5` It asks for classes, relations, and attributes, and each example has to be copied from a passage.

`1:02.7` An example that is not in the text is dropped.

`1:06.4` A person edits the draft and publishes it. Published versions are immutable.

`1:10.8` A label change does not re-extract.

`1:13.1` A new term is extracted only where it is likely to apply.

`1:17.5` A change of meaning is a major version, and the documents are extracted again.

`1:22.6` Extraction is a tool call whose schema comes from the ontology, so a missing type cannot be recorded.

`1:29.1` Each entity, attribute, and relation names its passages.

`1:32.1` Code checks shape, domain and range, and grounding: the name and the value occur in the cited passage.

`1:38.6` SHACL requires every assertion to cite at least one passage and exactly one run.

`1:43.7` After a short repair, what still fails is dropped one item at a time.

`1:48.8` A term with no place in the ontology stays a candidate, outside the graph, until a person publishes it.

`1:55.6` The record is the RDF for that document at that ontology version.

`2:00.0` The graph database, the passage index, and the portal are projections rebuilt from it.

## 4. Chat

File: `04-chat.mp4`
Assembly: 2:45 to 3:59.

Voice only. The picture is the generated chat mechanism.

Read:

`0:00.5` A question comes back under the same rule. The released ontology is in the prompt, so the agent plans in those types, relations, and attributes.

`0:09.4` The tools are fixed and read-only: search for an entity, read its facts, walk a neighbourhood, find a path, search passages, read passages.

`0:17.6` The model cannot write a query of its own.

`0:21.0` A named thing follows the graph. Each fact brings the passage it was extracted from, and that passage is read before the fact is used.

`0:29.9` A question that describes a situation searches passages by meaning. One vector is one passage, so the hit leads back to the facts which cite it.

`0:39.2` Private sources follow the caller's token. The model cannot widen that.

`0:43.3` The agent returns claims: one statement, a passage identifier, and a quote copied from that passage.

`0:49.1` Code then reads the passage again. The quote has to be in it. Too short, or not actually there, it fails. A claim with no citation left is removed.

`0:59.4` Failed citations are sent back once. A guardrail can also reject a claim that does not follow from its quotes.

`1:06.6` The page is built only from what passed.

`1:09.6` If nothing passed, the answer declines and names what was missing.

## 5. On the lab

File: `05-lab-answer.mp4`
Assembly: 3:59 to 4:34.

Record this picture on the lab, and record this voice with it. Replace 05-lab-answer.mp4 in the cut.

Director, not spoken:

If the space-missions collection is loaded, ask: “What launched Voyager 1, and when?” The source card should highlight words from that document. On another collection, pick a fact you can point at in one passage.

Shots, while this voice plays:

- Window wider than 1,100 pixels, so the workbench sits beside the chat.
- Ask a question the collection can answer. Do not read the answer out before it arrives.
- Leave the workbench visible: a search, a read, then the citation check.
- When the answer lands, open source 1. The highlight in the passage is the quote.

Read:

`0:00.5` On the lab, ask a question the collection can answer.

`0:04.2` Leave the workbench open.

`0:05.8` The steps are the tool calls: a type searched, an entity read, then the citation check.

`0:11.6` The answer that lands is a set of statements.

`0:14.9` Each one carries a number.

`0:16.9` Open the number.

`0:18.1` That is the passage, and the words highlighted in it are the quote taken from it.

`0:23.9` It is the same identifier that was written when the document was extracted.

`0:28.7` The source was required when the claim was made, and the page kept only the ones that matched.

## 6. The decline

File: `06-lab-decline.mp4`
Assembly: 4:34 to 5:00.

Record this picture on the lab, and record this voice with it. Replace 06-lab-decline.mp4 in the cut.

Director, not spoken:

If the space-missions collection is loaded, ask: “Who is the current project manager for Voyager 1?” That is not in the documents. The line on screen should be: I can't answer that from the sources in this collection.

Shots, while this voice plays:

- Ask something the documents do not contain. Let the answer finish.
- Show the decline, and the list under “What the sources don't cover”.
- Do not rephrase until the model guesses. The decline is the result.

Read:

`0:00.5` Now ask something the sources do not contain.

`0:03.5` The result on screen is a decline.

`0:06.1` It names what is missing.

`0:08.0` There is no unchecked sentence beside it.

`0:10.7` The passages do not move, and the ontology is versioned, so the same question meets the same record.

`0:17.2` What reaches a person has already been tied to a passage.

`0:21.2` A result that cannot be tied to one is not shown.

