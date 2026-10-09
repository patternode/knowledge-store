# Knowledge Store — five-minute briefing

Picture and voice for one cut of about five minutes. The generated picture covers the failure, the rule, the ingestion pipeline, and the chat check. Two slots are left for a recording of the portal on the lab.

The voice is not in the picture files. Record it from [voice-script.md](voice-script.md). Speak at about 160 words a minute, with a short breath at each sentence. The cues are timed to that pace.

Assembly timecode is burned into the bottom right of every frame. A gold hairline along the footer shows progress through the current section.

## Timeline

| In | Out | Section | Picture | You record |
|---|---|---|---|---|
| 0:00 | 0:22 | The failure | `01-open.mp4` | Voice only. The picture is the generated open. |
| 0:22 | 0:39 | The rule | `02-rule.mp4` | Voice only. The picture is the generated rule. |
| 0:39 | 2:45 | Ingestion | `03-ingestion.mp4` | Voice only. The picture is the generated pipeline. |
| 2:45 | 3:59 | Chat | `04-chat.mp4` | Voice only. The picture is the generated chat mechanism. |
| 3:59 | 4:34 | On the lab | `05-lab-answer.mp4` | Record this picture on the lab, and record this voice with it. Replace 05-lab-answer.mp4 in the cut. |
| 4:34 | 5:00 | The decline | `06-lab-decline.mp4` | Record this picture on the lab, and record this voice with it. Replace 06-lab-decline.mp4 in the cut. |

Total picture: 5:00 (300.1 seconds).

## 1. The failure

Picture `01-open.mp4`, from 0:00 to 0:22.

Voice only. The picture is the generated open.

### Picture

- Title lockup, then the line: the model writes the answer.
- Three failures arrive with the voice: a figure shifts, a relation appears, a citation is attached afterwards.
- The section ends on: the failure is the order of operations.

### Voice

- `0:00.5` A retrieval system can still invent.
- `0:02.8` It finds nearby text, and then the model writes the answer.
- `0:06.8` That sentence is a paraphrase.
- `0:08.8` A figure shifts.
- `0:10.0` A relation appears that no passage stated.
- `0:12.7` If a citation is added, it is attached afterwards.
- `0:16.0` Knowing the model does not remove that step.
- `0:19.0` The failure is the order of operations.

## 2. The rule

Picture `02-rule.mp4`, from 0:22 to 0:39.

Voice only. The picture is the generated rule.

### Picture

- The rule, in one line: shown only when a passage contains it.
- Three columns land with the voice: Propose, Check, Remove.
- The last line adds the decline: if nothing remains, the system says so.

### Voice

- `0:22.4` Knowledge Store keeps the statement and the source together.
- `0:25.8` A result is shown only when a passage contains it.
- `0:29.5` The model proposes.
- `0:30.8` Code checks that proposal against the text, and against the ontology.
- `0:34.8` What fails is removed.
- `0:36.4` If nothing remains, the system says so.

## 3. Ingestion

Picture `03-ingestion.mp4`, from 0:39 to 2:45.

Voice only. The picture is the generated pipeline.

### Picture

- Landing: uploads, pages, and an adapter. The bytes are fetched. Nothing is parsed, and nothing uploaded is rewritten.
- Bronze: two names, one object, addressed by the sha256 of the bytes. An unchanged version is skipped.
- Silver: passages with stable identifiers. About 1,800 characters. The passage is the unit of evidence.
- Ontology: the core vocabulary records provenance only. The domain ontology is brought as Turtle, or drafted once five documents are refined. Examples not in the passage are dropped. A person publishes. Patch, minor, and major versions decide whether anything is extracted again.
- Extract: a tool call whose schema comes from the ontology. Shape, domain and range, grounding, and SHACL. A short repair, then drop the item. Candidates stay outside the graph.
- Record: the RDF is the record. The graph database, the passage index, and the portal are projections.

### Voice

- `0:39.9` Documents arrive as documents.
- `0:41.5` An adapter lists them and fetches the bytes. It does not parse them, and it leaves the upload unchanged.
- `0:48.3` Ingest stores each distinct file once, under the hash of its bytes.
- `0:52.7` Two names for the same file are one object, and a version that has not changed is skipped.
- `0:59.2` That copy is bronze, the immutable source.
- `1:01.9` Refine writes silver: passages cut on a fixed rule, about eighteen hundred characters.
- `1:06.6` The identifier is the document hash plus the hash of the passage, so a rerun keeps the same identifiers.
- `1:13.5` Every fact cites one of those passages. That passage is the unit of evidence.
- `1:18.6` What the documents are about is a separate ontology.
- `1:21.9` A core vocabulary, shared by every collection, records only where a fact came from: the document, the passage, and the extraction run.
- `1:29.8` You bring the domain ontology as Turtle, or the system drafts one once five documents are refined.
- `1:36.0` It asks for classes, relations, and attributes, and each example has to be copied from a passage.
- `1:42.1` An example that is not in the text is dropped.
- `1:45.8` A person edits the draft and publishes it. Published versions are immutable.
- `1:50.2` A label change does not re-extract.
- `1:52.5` A new term is extracted only where it is likely to apply.
- `1:56.9` A change of meaning is a major version, and the documents are extracted again.
- `2:02.0` Extraction is a tool call whose schema comes from the ontology, so a missing type cannot be recorded.
- `2:08.5` Each entity, attribute, and relation names its passages.
- `2:11.5` Code checks shape, domain and range, and grounding: the name and the value occur in the cited passage.
- `2:18.0` SHACL requires every assertion to cite at least one passage and exactly one run.
- `2:23.1` After a short repair, what still fails is dropped one item at a time.
- `2:28.2` A term with no place in the ontology stays a candidate, outside the graph, until a person publishes it.
- `2:35.0` The record is the RDF for that document at that ontology version.
- `2:39.4` The graph database, the passage index, and the portal are projections rebuilt from it.

## 4. Chat

Picture `04-chat.mp4`, from 2:45 to 3:59.

Voice only. The picture is the generated chat mechanism.

### Picture

- The released ontology sits in the prompt. The agent plans in those terms.
- Six read-only tools. No query language for the model to write.
- Two routes. A named thing follows the graph, and every fact carries passage ids. A described situation searches by meaning: one vector is one passage.
- Private sources follow the caller's token.
- A claim is a statement, a passage id, and a quote copied from that passage.
- Code reads the passage back. The quote must be in it. Too short fails. No citation left, the claim is removed. Failed citations go back once. A guardrail can reject a claim that does not follow from its quotes. Nothing left: the decline.

### Voice

- `2:45.3` A question comes back under the same rule. The released ontology is in the prompt, so the agent plans in those types, relations, and attributes.
- `2:54.3` The tools are fixed and read-only: search for an entity, read its facts, walk a neighbourhood, find a path, search passages, read passages.
- `3:02.5` The model cannot write a query of its own.
- `3:05.9` A named thing follows the graph. Each fact brings the passage it was extracted from, and that passage is read before the fact is used.
- `3:14.8` A question that describes a situation searches passages by meaning. One vector is one passage, so the hit leads back to the facts which cite it.
- `3:24.1` Private sources follow the caller's token. The model cannot widen that.
- `3:28.2` The agent returns claims: one statement, a passage identifier, and a quote copied from that passage.
- `3:34.0` Code then reads the passage again. The quote has to be in it. Too short, or not actually there, it fails. A claim with no citation left is removed.
- `3:44.3` Failed citations are sent back once. A guardrail can also reject a claim that does not follow from its quotes.
- `3:51.5` The page is built only from what passed.
- `3:54.5` If nothing passed, the answer declines and names what was missing.

## 5. On the lab

Picture `05-lab-answer.mp4`, from 3:59 to 4:34.

Record this picture on the lab, and record this voice with it. Replace 05-lab-answer.mp4 in the cut.

### Picture

- This slot is a caption guide. Replace it with the portal recording.
- The on-screen sentence follows the voice, so the slot can be watched before the lab picture exists.


### Lab shots

- Window wider than 1,100 pixels, so the workbench sits beside the chat.
- Ask a question the collection can answer. Do not read the answer out before it arrives.
- Leave the workbench visible: a search, a read, then the citation check.
- When the answer lands, open source 1. The highlight in the passage is the quote.

If the space-missions collection is loaded, ask: “What launched Voyager 1, and when?” The source card should highlight words from that document. On another collection, pick a fact you can point at in one passage.

### Voice

- `3:59.4` On the lab, ask a question the collection can answer.
- `4:03.1` Leave the workbench open.
- `4:04.7` The steps are the tool calls: a type searched, an entity read, then the citation check.
- `4:10.5` The answer that lands is a set of statements.
- `4:13.8` Each one carries a number.
- `4:15.8` Open the number.
- `4:17.0` That is the passage, and the words highlighted in it are the quote taken from it.
- `4:22.8` It is the same identifier that was written when the document was extracted.
- `4:27.6` The source was required when the claim was made, and the page kept only the ones that matched.

## 6. The decline

Picture `06-lab-decline.mp4`, from 4:34 to 5:00.

Record this picture on the lab, and record this voice with it. Replace 06-lab-decline.mp4 in the cut.

### Picture

- This slot is a caption guide. Replace it with the decline on the portal.


### Lab shots

- Ask something the documents do not contain. Let the answer finish.
- Show the decline, and the list under “What the sources don't cover”.
- Do not rephrase until the model guesses. The decline is the result.

If the space-missions collection is loaded, ask: “Who is the current project manager for Voyager 1?” That is not in the documents. The line on screen should be: I can't answer that from the sources in this collection.

### Voice

- `4:34.9` Now ask something the sources do not contain.
- `4:37.9` The result on screen is a decline.
- `4:40.6` It names what is missing.
- `4:42.5` There is no unchecked sentence beside it.
- `4:45.1` The passages do not move, and the ontology is versioned, so the same question meets the same record.
- `4:51.6` What reaches a person has already been tied to a passage.
- `4:55.7` A result that cannot be tied to one is not shown.

