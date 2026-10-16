# Permissions, protection and classification from the source

Status: a design. Part of it is implemented, and the rest is proposed here for a decision.

A document arrives with security requirements of its own: who may read it, how it is classified,
and how it may be handled. Those requirements belong to the document, not to the deployment, and
they must reach every place a piece of the document reaches: the passage that is quoted, the
fact extracted from it, the vector that finds it, the graph that links it, and the answer that
cites it. This note says how one such requirement, scope, travels today, and designs the rest so
that what the source said about a document is preserved against the passages the document
became, and enforced wherever they are read.

The design around this, boundary by boundary, is [Security design](security.md). The
vocabulary the controls would extend is the [core vocabulary](../core-vocabulary.md).

## The principle

A control originates where the document does and travels with its content. Nothing downstream
re-derives it, guesses it, or holds a separate list of who may read what. The rules:

1. A control is captured at ingest, from the source, with where it came from recorded beside it.
2. A passage inherits its document's controls. A passage may carry a tighter control of its own,
   never a looser one.
3. A fact's control is the most restrictive of the passages or cells it cites. It is computed from
   them, so it can never drift from them.
4. An answer's control is the most restrictive of what it cites, and the person sees it.
5. Every hop that serves content reads the control on the content and the entitlement on the
   caller's verified token, and decides there. A missing control means private, never public.
6. A change at the source reaches every layer at the next sweep, without a model call.

## What exists today: one control, `scope`

Each source has a `scope`, `public` or `private`, set in the deployment's configuration
(`collections.<id>.sources[].scope`). A caller is private when their token says so: a person in
the `private-readers` group, a person with one of `site_sign_in.private_roles`, or an application
with the `tools.private` scope ([`claims.py`](../../src/knowledge_store/claims.py)). The scope
travels with the content through every layer:

| Layer | Where the scope is held | Set by | Read by |
|---|---|---|---|
| Source configuration | `config/sources.json`, from Terraform | the deployer | ingest |
| Bronze | `meta.json` beside the bytes: `scope`, with `source`, `source_uri`, `source_key` and the adapter's `metadata` | [`pipeline/ingest.py`](../../src/knowledge_store/pipeline/ingest.py), from the source | refine |
| Silver | the document record's `scope`; passages belong to the document | [`pipeline/refine.py`](../../src/knowledge_store/pipeline/refine.py), copied from bronze | projection, the passage tools, the Knowledge Base sync |
| Gold | `ks:scope` on the `ks:Document` of each document's graph, and on each row and cell of a bound table | [`extract/rdf.py`](../../src/knowledge_store/extract/rdf.py), [`structured/bind.py`](../../src/knowledge_store/structured/bind.py) | projection, Neptune |
| Projection | each document, passage, entity name and candidate evidence tagged with its document's scope; a term seen only in private documents is private | [`pipeline/project.py`](../../src/knowledge_store/pipeline/project.py) | the portal API, the in-memory tools |
| Neptune | the document's `ks:scope` in its named graph; each name and type is answered with the scope of the graph that states it | the loader | the graph tools' fixed SPARQL ([`graph/sparql.py`](../../src/knowledge_store/graph/sparql.py)) |
| Knowledge Base | `scope` in each passage's metadata, with `collection`, `doc` and `passage_id` | [`pipeline/load.py`](../../src/knowledge_store/pipeline/load.py) | `Retrieve` with a `scope = public` filter for a public caller, and the hit checked again in code ([`tools/passages.py`](../../src/knowledge_store/tools/passages.py)) |
| Candidates and drafts | each piece of evidence tagged with its document's scope | projection | the portal withholds private evidence, and drafts and requests altogether, from public callers |
| The answer | each citation is read back as the caller; a passage the caller may not read fails the citation and the claim is dropped | [`agent/grounding.py`](../../src/knowledge_store/agent/grounding.py) | the person |
| A document link | the document's scope, checked before the link is signed | the portal API | the person |

The enforcement is one boolean, `caller_private`, written into every tool call by the Gateway's
interceptor from the verified token, and one function, `visible(item, private)`, applied at each
hop. Where the document's record is missing, the projection treats the document as private.

That is sound as far as it goes, and it goes exactly one step: a document is public or private
because its source is. Three things a source can say about a document are not captured:

- Who may read it. A source system has an access list (an S3 bucket policy or object tag, a
  SharePoint or Confluence permission, a Drive share), and two documents from one source can have
  different ones.
- How it is classified. Many documents carry a marking (`Internal`, `Confidential`, `Restricted`,
  or a scale of the organisation's own), in a header, a footer, a property or a label, and the
  marking can differ by paragraph.
- How it may be handled: not to be copied out, not to be given to a model, to be kept only until
  a date.

Today a deployer with such documents has one tool: put them in a private source, or in a stack
of their own. This design gives the document's own requirements a path of their own.

## Where a requirement originates

A control can come from four places. Each is recorded with its origin, so a curator can see why
a passage is restricted and a reviewer can check it against the source.

| Origin | Example | Captured by |
|---|---|---|
| The source's configuration | `scope = "private"`; a default classification or readers for the whole source | ingest, from `config/sources.json`, as today |
| The source system | an S3 object's tags or user metadata; a SharePoint sensitivity label and its permissions; a Confluence page restriction; a Drive file's sharing | the adapter, in `SourceItem.metadata`, under a reserved key `controls` |
| The document's own markings | `CONFIDENTIAL` in a header or footer; a classification line in front matter; a portion marking at the start of a paragraph | refine, by a marking detector configured per deployment (patterns on a scale) |
| The knowledge steward | an override that tightens a document, or a correction with a reason | the portal, as a request kept in the lake, like an ontology request |

The knowledge steward is the person who looks after a collection: the curator of the other
notes, a private reader who uploads and tags documents, publishes the ontology, and reads the
workbench. The flow below is written from where they sit.

Precedence is by restriction, not by origin: the effective control is the most restrictive of
everything that was said. A marking can tighten what the source system said and never loosen it.
A curator can tighten freely, and can loosen only with a reason that is kept, because a loosening
is a decision someone must be able to find later.

## The model

Three kinds of control, on a document and optionally on a passage:

| Kind | Value | Meaning |
|---|---|---|
| Classification | one level of a scale the deployment declares, ordered, such as `public < internal < confidential < restricted` | a caller needs a clearance at or above the level |
| Permission | a principal or group name, as the source states it, repeated | a caller needs to hold one of them; no permission stated means anyone within the classification |
| Handling | a caveat from a small fixed set, repeated | `no-export`: no document link and no table download; `no-model`: the text is held in bronze and never refined, extracted, embedded or quoted; `expires:<date>`: removed from every layer by the first sweep after the date; `quote-only`: shown only as a verbatim quote, never summarised in a claim's text |

Today's `scope` becomes the first two levels of the scale: `public` is the lowest level, and
`private` is the next. A deployment that declares no scale keeps exactly today's behaviour, and
`ks:scope` keeps its meaning.

In the core vocabulary, as a minor version (1.2.0), each control is a reified statement so that
its origin and evidence travel with it:

| Term | From, to | Meaning |
|---|---|---|
| `ks:Control` | class | One control on a document or a passage (a `prov:Entity`) |
| `ks:control` | Document or Passage, Control | The controls on it |
| `ks:controlKind` | Control, string | `classification`, `permission` or `handling` |
| `ks:controlValue` | Control, string | The level, the principal, or the caveat |
| `ks:controlOrigin` | Control, string | `source`, `system`, `marking` or `curator` |
| `ks:controlEvidence` | Control, Passage or string | For a marking, the passage that carries it; for a system control, the attribute it was read from |
| `ks:classification` | Document or Passage, string | The effective level, computed from the controls, so a store can filter on one value |
| `ks:readableBy` | Document or Passage, string | The effective permissions, repeated, for the same reason |

The core shapes gain two rules: every document has a classification, and every control names
its kind, value and origin. A graph without them fails the provenance gate, as a graph without a
cited passage does today.

Facts carry no control of their own. An assertion cites passages (`ks:extractedFrom`) or cells
(`ks:recordedIn`), and its effective control is computed from them at the hop that serves it.
Storing it would be a second copy that could drift.

## The metadata that comes with each source item: a specification

This is the contract between an adapter and ingest. An adapter yields one item per piece of
content with the envelope below, and ingest records it in bronze beside the bytes, unchanged.
Everything downstream reads bronze, so what an adapter does not say here is never known later.

### The envelope

Every item carries these, as [`adapters/base.py`](../../src/knowledge_store/adapters/base.py)
defines them today:

| Field | Required | Rule |
|---|---|---|
| `key` | yes | The item's stable identity within the source: an S3 key, a URL, a relative path. Never changes for the same item |
| `version` | yes | Changes whenever the content or the controls change. Ingest skips an item whose key and version it has stored, so a version that does not change with the controls hides a permission change (below) |
| `name` | yes | A file name, for the extension and as a fallback title |
| `uri` | yes | Where the item can be read at the source, for the document link and `ks:source` |
| `content_type` | no | The media type as the source states it; the extension decides the parser when it is absent |
| `metadata` | no | The descriptive metadata and the controls, as below. An empty mapping is valid |

### Descriptive metadata

`metadata` is a JSON object. These keys are reserved and read; any other key is kept as given,
shown to a curator, and never interpreted:

| Key | Type | Meaning |
|---|---|---|
| `title` | string | The title the source gives; the parser's title wins when the document carries one |
| `author`, `authors` | string, list of strings | Who wrote it, as the source states |
| `created`, `modified` | ISO 8601 timestamp | When it was written and last changed at the source |
| `language` | BCP 47 tag | Its language |
| `folder` | string | Its folder within the source (the S3 adapter sets this today) |
| `source_system` | string | The system it came from, such as `s3`, `sharepoint`, `confluence` |
| `source_id` | string | The system's own id for it, when that is not the key |
| `labels` | list of strings | Tags or labels the source attaches that are not controls |
| `controls` | list of control records | The security requirements, below |

The whole object is at most 32 KB as JSON, and a value is at most 4 KB; an item over either is
recorded in the run's manifest as `metadata_too_large` and ingested with its controls alone.

### A control record

```json
{
  "kind": "classification",
  "value": "confidential",
  "origin": "system",
  "evidence": "x-amz-meta-classification",
  "stated_at": "2026-10-02T14:05:00Z",
  "stated_by": "sharepoint:site-owner"
}
```

| Field | Required | Rule |
|---|---|---|
| `kind` | yes | `classification`, `permission` or `handling` |
| `value` | yes | For a classification, a level of the deployment's scale or one of its aliases, matched without case; for a permission, a principal as the source states it, which the deployment's mapping turns into a group name the token carries; for handling, one of `no-export`, `no-model`, `quote-only`, or `expires:<ISO 8601 date>` |
| `origin` | yes | `source` (the source's configured defaults), `system` (read from the source system), `marking` (read from the document's text), `curator` |
| `evidence` | no | What it was read from: an attribute or tag name, a property, or for a marking the passage id, which refine fills in |
| `stated_at` | no | When the source said it, ISO 8601; absent means at fetch time |
| `stated_by` | no | The principal at the source that set it, when the system says |

A value is trimmed and at most 256 characters, and an item carries at most 64 control records.
An adapter does not compute effective values: it reports every control it can see, and refine
computes the effective classification, permissions and handling from all of them, most
restrictive first, as [Where a requirement originates](#where-a-requirement-originates) says.

### Where each adapter reads them

| Adapter | Reads | As |
|---|---|---|
| `s3_landing` | the object's tags `classification`, `readers` (comma-separated) and `handling` (comma-separated); the same as user metadata (`x-amz-meta-classification`, `x-amz-meta-readers`, `x-amz-meta-handling`), which a console upload or `aws s3 cp --metadata` can set | `origin = "system"`, `evidence` the tag or header name, `stated_at` the object's last-modified time |
| `s3_landing` | a folder's defaults in `.controls.json` beside the files (a name starting with a dot is never a document); the nearest folder up to the source's prefix applies | `origin = "system"`, `evidence` the file's key |
| `s3_landing` | a per-file sidecar `<name>.controls.json` beside the file, for an upload tool that cannot set tags; the sidecar is not a document | `origin = "system"`, `evidence` the sidecar's key |
| `http_urls` | nothing from the page; the source's configured defaults alone | `origin = "source"` |
| `local_dir` | `.controls.json` folders and `<name>.controls.json` sidecars, for development and tests | as for `s3_landing` |
| a source-system adapter (SharePoint, Confluence, Drive) | the item's sensitivity label, its permissions as principals, and its retention label, through the system's API | `origin = "system"`, `evidence` the API field, `stated_by` the label's or permission's grantor when the API gives one |

A `.controls.json` file is a JSON object with a `controls` list in the form above, and may also
carry the descriptive keys, which apply to every file in the folder that does not state its own.

When an adapter can see several of these for one item, it reports all of them: the source's
defaults, the folder's, the object's. Nothing is dropped as redundant, since the record of what
each one said is the point, and refine applies the most restrictive.

### The version rule

An item's `version` is the content stamp the source gives (an etag, a modified time) joined with
a digest of its control records, in a fixed order, so that a permission or label changed at the
source makes the item new to ingest although its bytes are the same. The S3 adapter's version is
therefore `<etag>+<sha256 of the sorted controls>[:16]`, and the same rule holds for any adapter
that reads controls. Ingest sees the same digest, stores nothing new under bronze's content key,
and rewrites `meta.json`.

### What bronze records

`meta.json` beside the bytes keeps the envelope and the metadata as received, with what ingest
adds:

```json
{
  "doc_id": "<sha256 of the bytes>",
  "source": "policies", "adapter": "s3_landing", "scope": "private",
  "source_key": "landing/policies/hr/leave.pdf", "source_uri": "s3://<lake>/landing/policies/hr/leave.pdf",
  "source_version": "\"9b2f...\"+3c1d0a7e5b9f4e2a", "source_keys": ["landing/policies/hr/leave.pdf"],
  "name": "leave.pdf", "ext": ".pdf", "content_type": "application/pdf", "bytes": 184320,
  "metadata": {
    "folder": "hr", "modified": "2026-09-30T09:12:00Z",
    "controls": [
      {"kind": "classification", "value": "internal", "origin": "source"},
      {"kind": "classification", "value": "confidential", "origin": "system",
       "evidence": "x-amz-meta-classification", "stated_at": "2026-09-30T09:12:00Z"},
      {"kind": "permission", "value": "hr-staff", "origin": "system", "evidence": "readers"},
      {"kind": "handling", "value": "no-export", "origin": "system", "evidence": "handling"}
    ]
  },
  "controls_digest": "3c1d0a7e5b9f4e2a",
  "fetched_at": "2026-10-16T02:40:11Z"
}
```

`scope` stays, derived from the effective classification so that everything reading bronze today
keeps working: `public` for the lowest level, `private` for any other. The effective values are
not written here; refine computes them into the silver record, so bronze stays what the source
said and nothing more.

### Validation at ingest

| Finding | What ingest does |
|---|---|
| A control with an unknown `kind` or `origin`, a classification value on no level or alias of the scale, a handling value outside the set, or a malformed date | The item is ingested with the control replaced by `classification = <the scale's highest level>`, `origin = "source"`, `evidence = "invalid control"`, and the run's manifest records `controls_invalid` with the original. A document is never made public by a control that could not be read |
| A permission value the deployment's mapping does not know | Kept as given and recorded as `permission_unmapped`. It matches no caller until the mapping names it, so while it is the document's only permission nobody can read the document, and the manifest says why |
| An `expires` date in the past | The item is ingested, recorded as `expired`, and the first sweep removes it from every layer but bronze |
| `.controls.json` that does not parse | The folder's files are ingested as if it were absent, with `controls_file_invalid` in the manifest |
| Metadata over the size limits | As above: `metadata_too_large`, the controls kept |

The manifest row for an item (`manifests/ingest/<run>.jsonl`) carries these findings beside its
status, so a curator can list what a sweep could not read, and the workbench can show it.

### Configuration

The deployment declares the scale and the mappings once, in Terraform beside the sources:

```hcl
controls = {
  scale   = ["public", "internal", "confidential", "restricted"]
  aliases = { "official" = "internal", "secret" = "restricted" }
  # a source's permission values to the groups the token carries
  groups  = { "HR Staff" = "hr-staff", "sharepoint:hr-site-members" = "hr-staff" }
  # the clearance a token's groups or roles give
  clearance = { "private-readers" = "internal", "executives" = "restricted" }
}
```

Each source keeps `scope`, and may add `controls`: a list of records in the form above, with
`origin = "source"`, as its defaults. A deployment that declares no `controls` block has the
two-level scale and today's mapping, and every adapter's reading of tags and sidecars still
lands in bronze, so the record is kept from the first sweep even before the scale is declared.

## How the specification is used: from the steward to the enforced answer

The specification above is the first link of one chain. Each stage reads what the stage before
wrote and adds its own, and nothing after the adapter goes back to the source. This section
follows the chain end to end, with the `leave.pdf` of the bronze example above, and two people
who ask about it afterwards: one in HR, whose token carries the group `hr-staff` and a
clearance of `confidential`, and one outside HR, with a clearance of `internal`.

### Who does what

| Who | Does | Through |
|---|---|---|
| The deployer | Declares the scale, the aliases, the group mapping and the clearances once; sets each source's defaults | Terraform (`controls`, `sources[].controls`) |
| The knowledge steward | Puts documents in, with their controls: tags at upload, a folder's `.controls.json`, or a sidecar; reads what a sweep could not read; overrides with a reason; watches the workbench | the lake's `landing/`, the portal |
| The source system | States labels and permissions of its own, which an adapter reads | its API or its object metadata |
| The adapter | Turns what it sees into control records, and folds them into the version | `SourceItem.metadata.controls` |
| Ingest | Records the item as received, and what it could not read | bronze `meta.json`, the manifest |
| Refine | Computes the effective controls; reads markings | the silver record, the passages |
| Extraction | Extracts facts from the text; code writes the controls beside them; the shapes refuse a graph without a classification | gold |
| Projection and load | Carry the controls into the projection, Neptune and the Knowledge Base | the index, the named graphs, the passage metadata |
| The interceptor | Writes the caller's entitlement into every tool call | the Gateway |
| The tools and the portal API | Serve only what the entitlement allows | `visible(item, caller)` |
| The grounding check | Drops any claim citing a passage the caller may not read | the agent |
| The page | Shows the answer's classification, and refuses a link the handling forbids | the chat page |

### The flow

```
 the steward                           the pipeline (a sweep)                       the lake
 ───────────                           ──────────────────────                       ────────
 uploads hr/leave.pdf with tags  ──▶  adapter: tags + hr/.controls.json + source   landing/
 (classification, readers,            defaults -> control records; version =
  handling), or a sidecar             etag + digest of the controls
                                           │
                                      ingest: bronze meta.json as received;         bronze/
                                      a manifest row with any finding
     ▲ reads the findings                  │
     │ (controls_invalid, ...)        refine: effective classification,             silver/
     │ overrides with a reason        permissions, handling -> the document
     │                                record; markings -> passage controls
     │                                     │
     │                                extract: the model sees text only; code       gold/
     │                                writes ks:Control beside the facts;
     │                                the shapes refuse a graph without one
     │                                     │
     │                                project and load: the index, Neptune's         index, Neptune,
     │                                named graph, the passage's KB metadata         the Knowledge Base
     │
 a person asks ──▶ portal API: entitlement from the verified token; quota
                       │
                   agent (Runtime): the same token
                       │
                   Gateway: the interceptor writes {clearance, groups} into the call
                       │
                   tools: Neptune filtered by the graph's controls; the Knowledge
                   Base filtered by the passage's metadata; each hit checked again
                       │
                   grounding: every citation read back as the caller; a passage
                   the caller may not read fails, and its claim is dropped
                       │
                   the answer, with the most restrictive classification it cites;
                   a document link only where the handling allows it
```

### Step by step, with `leave.pdf`

1. The deployer has declared the scale `public < internal < confidential < restricted`, mapped
   the source system's `HR Staff` to the group `hr-staff`, and given the source `policies` a
   default of `internal` (`scope = "private"`, and a `controls` record with `origin = "source"`).
2. The steward uploads `hr/leave.pdf` to the source's landing folder with the tags
   `classification = confidential`, `readers = HR Staff` and `handling = no-export`, or with
   `hr/leave.pdf.controls.json` beside it saying the same. The upload starts a sweep.
3. The adapter lists the item. It reads the tags (or the sidecar), the folder's `.controls.json`
   if there is one, and the source's defaults, and yields the item with four control records in
   `metadata.controls`, each with its origin and evidence, and a version of the object's etag
   joined with the digest of those records.
4. Ingest stores the bytes once under their hash and writes `meta.json` as the specification
   shows: the records as received, `controls_digest`, and `scope = "private"` derived for
   compatibility. Every record is valid, so the manifest row says `stored` and nothing else. Had
   the tag said `top secret`, a level the scale does not have, the row would say
   `controls_invalid`, and the document would be treated as `restricted` until the steward
   corrected the tag or added the alias.
5. Refine parses the text into passages and computes the effective controls from all four
   records, most restrictive first: classification `confidential` (the tag over the source's
   `internal`), permission `hr-staff` (the mapping of `HR Staff`), handling `no-export`. The
   silver record carries them, and every passage inherits them. The marking detector finds no
   portion marking, so no passage carries a control of its own.
6. Extraction sends the passages to the model with the ontology, and the model knows nothing of
   the controls. Code adds the `ks:Control` nodes, `ks:classification` and `ks:readableBy` to
   the document's graph beside the model's facts, and the SHACL gate passes it because the
   classification is there.
7. Projection tags the document, its passages, its entity names and its candidate evidence with
   the effective controls. The loader writes the graph to Neptune as it is, and writes each
   passage to the Knowledge Base with `classification = confidential` and
   `readable_by = ["hr-staff"]` in its metadata.
8. The HR person asks how much leave carries over. The portal API reads their entitlement
   (`clearance = confidential`, `groups = ["hr-staff"]`) from the token, takes a question from
   their quota, and passes the question to the agent with the same token. The interceptor
   writes the entitlement into every tool call. The Knowledge Base filter allows the passage,
   the graph tools answer from the document's graph, the citation check reads the passage back
   as the caller and passes, and the answer shows, marked `Confidential`. The sources panel lists
   the passage; the Open document button is absent, because the handling says `no-export`.
9. The person outside HR asks the same question. Their entitlement is `clearance = internal`
   with no HR group. The Knowledge Base filter excludes the passage, the graph tools filter the
   document's graph out of every name, fact and path, and nothing the model could ask for
   returns it. Had anything slipped through, the citation check would fail the passage and drop
   the claim. The agent answers that the sources cannot answer the question, and the workbench
   shows the steps that found nothing, with no trace of the passage's text.
10. The steward opens the collection's status and sees the sweep's findings: none for this
    document. For another, `controls_invalid` names the tag that could not be read, and
    `permission_unmapped` names a principal the deployer must add to the mapping. The steward
    fixes the tag at the source, or asks the deployer for the mapping, and the next sweep clears
    the finding.
11. Later, HR decides the policy is for everyone. The steward changes the tag to
    `classification = internal` and removes `readers`. The object's etag is unchanged but the
    controls' digest is not, so the adapter yields a new version; ingest rewrites `meta.json`;
    refine, projection and load take the new controls without a model call, since the bytes and
    the facts are the same. From the next sweep, both people's questions are answered from it.
12. If instead the steward tightens a document the source has marked too loosely, they keep an
    override in the portal with a reason. It is stored like an ontology request, with
    `origin = "curator"`, and refine applies it on the next sweep as one more record, most
    restrictive first. A loosening override is applied the same way, and its reason is the
    record of the decision.

### What each stage trusts

The chain holds because each stage trusts exactly one thing from the stage before:

| Stage | Trusts | Never trusts |
|---|---|---|
| The adapter | the source system's own statements | the document's text |
| Ingest | the adapter's records, which it validates | a record it cannot read, which becomes the highest level |
| Refine | bronze | the model, which it has not called |
| Extraction | the silver record's effective controls, written by code | the model's output, which is checked for grounding and never writes a control |
| The tools | the entitlement the interceptor wrote | an entitlement in the request, which the interceptor overwrites |
| The grounding check | the passage read back as the caller | what a tool returned |
| The page | the answer's classification and handling, from the agent | nothing it computes itself |

## How it travels

| Layer | What changes |
|---|---|
| Adapters | `SourceItem.metadata["controls"]`: a list of `{kind, value, origin, evidence}` the adapter read from the source system. The S3 adapter reads object tags and user metadata under a configured prefix (`x-amz-meta-classification`, `x-amz-meta-readers`). An adapter that knows nothing contributes nothing, and the source's configured defaults apply. The item's `version` includes the controls, so a permission change at the source is a changed item and is re-ingested, although the bytes are the same |
| Bronze | `meta.json` keeps `controls` as given, beside today's `scope`. Because the document's id is the hash of its bytes, a control change rewrites `meta.json` and nothing else |
| Refine | the document record carries the effective classification, permissions and handling. The marking detector runs over the text with the deployment's patterns and adds `marking` controls with the passage as evidence; a portion marking becomes a control on that passage. A `no-model` document stops here: its record says so, and no passages are written |
| Gold | the document's graph carries its `ks:Control` nodes and effective values; a passage with a control of its own carries them too. Extraction does not see the controls; they are written by code beside the model's result, as `ks:scope` is today |
| Projection | each document, passage and piece of evidence carries `classification`, `readable_by` and `handling`; `visible(item, caller)` replaces `visible(item, private)` |
| Neptune | the controls are triples in the document's named graph, and the fixed SPARQL filters a name, a type or a passage by the classification and permissions of the graph that states it, against the caller's clearance and groups |
| Knowledge Base | the passage's metadata gains `classification` and `readable_by` (a list), and the `Retrieve` filter asks for levels at or below the caller's clearance and, where permissions are stated, a group the caller holds; the hit is checked again in code, as today |
| Candidates and drafts | evidence carries its passage's controls; a term's own control is the least restrictive of its evidence, as a term seen only in private documents is private today |
| The workbench | a step that reads a passage shows the passage's classification, so a curator watching a question can see what it touched |
| The answer | the answer carries the most restrictive classification of what it cites, and the page shows it as a pill beside the sources. A `quote-only` passage can be cited and quoted; a claim whose text restates it without quoting fails the check |
| Document links | refused for a `no-export` document, as for a document outside the caller's scope today |
| Removal | the first sweep after an `expires` date deletes the document from silver, gold, the projection, Neptune and the Knowledge Base; bronze keeps the bytes under the lake's own lifecycle, since the record of what was ingested is not the document's to withdraw |

## Enforcement: the entitlement replaces the boolean

The caller's side of the check is an entitlement read from the verified token at each hop, in
place of `caller_private`:

```
{ "clearance": "confidential", "groups": ["finance", "legal"], "subject": "..." }
```

How a token yields it is configuration, as the claim names are today
([`claims.py`](../../src/knowledge_store/claims.py)): a mapping from Cognito groups, website roles
or application scopes to a clearance level, and the groups as they are. A deployment that
declares no scale maps `private-readers`, the private roles and `tools.private` to the second
level and everyone else to the first, which is today's rule exactly.

The interceptor writes the entitlement into every tool call, overwriting whatever the model or
the caller put there, as it writes `caller_private` now. The tools trust that argument alone. One
function decides visibility everywhere:

```
visible(item, caller) =
    level(item.classification) <= level(caller.clearance)
    and (item.readable_by is empty or item.readable_by intersects caller.groups)
    and "no-model" not in item.handling
```

It is applied at the same hops as today: every portal API view, the graph tools, the passage
tools, the structured tools, the Knowledge Base filter, the citation check, and the document
link. The citation check is what makes the rest safe to get wrong once: a claim citing a passage
the caller may not read is dropped before the answer is shown, whatever a tool returned.

The two service clients of website sign-in carry an entitlement each, as they carry a scope
each today: a deployment with more than two kinds of reader on its website adds clients, one per
entitlement, and the portal picks the client by the person's roles.

## What a change at the source does

| Event | Effect | When |
|---|---|---|
| A document's permission or label changes at the source | the adapter sees a new version; ingest rewrites bronze `meta.json`; refine, gold, the projection, Neptune and the Knowledge Base take the new controls without a model call | the next sweep: an upload event, or the schedule (`rate(6 hours)` by default) |
| A document is removed at the source | as today: it leaves the sweep's set, and the loader drops its graph and passages | the next sweep |
| A person's group changes | their next token carries it; a token already issued lasts up to 60 minutes | at most an hour |
| An answer already shown cited a passage since restricted | it stays in the person's chat state until its TTL; a new question cannot cite the passage | the chat table's TTL |

Revocation is therefore bounded by the sweep interval plus the token lifetime, and a deployment
that needs it tighter shortens the schedule. A document that must be gone at once is deleted from
the lake by an administrator, and the next sweep removes it everywhere.

## What this does not do

- It does not make a hard boundary. One lake, one graph and one index hold everything, and the
  tools' roles can read all of it; code enforces the controls. Content that must be separated by
  IAM belongs in a stack or an account of its own, as [SECURITY.md](../../SECURITY.md) says.
- It does not classify documents by their content. A marking is read where the document carries
  one; nothing infers a level from what the text says. Inference is a deployment's own step,
  before upload, with its own accountability.
- It does not screen questions or answers for classified content. The guardrail screens for
  attacks and harm; a person with a clearance sees what their clearance allows.
- It does not reconcile two sources' scales. A deployment declares one scale, and each source's
  values are mapped onto it in configuration.

## Open decisions

| Decision | Options | A recommendation |
|---|---|---|
| The scale | fixed (`public < private`, as now) against declared per deployment | declared per deployment, with the two-level default, so that nothing changes for an existing deployment |
| Where group membership comes from | the token's groups alone, against a lookup at the source system | the token alone; a lookup makes every question wait on another system, and the sweep already re-reads the source |
| Portion markings | in the first version, against later | later: they need the marking detector and per-passage controls in every layer, and most corpora mark whole documents |
| Handling caveats | the four above, against only `no-export` and `expires` | all four; `no-model` is the one a deployer with a regulated corpus asks for first |
| The vocabulary | a core minor version against a deployment's own terms | the core, so every deployment and every tool reads the same terms |

## Implementation, in order

Each step is testable without AWS, against the fake model and the in-memory stores, and each
leaves a deployment with no controls declared behaving as it does today.

1. The scale and the mapping in configuration; `claims.py` yields an entitlement, and
   `caller_private` is derived from it for compatibility.
2. `controls` in `SourceItem.metadata`, bronze `meta.json` and the silver document record; the
   S3 adapter reads tags and user metadata; the effective values computed in refine.
3. Core vocabulary 1.2.0 and its shapes; `extract/rdf.py` and `structured/bind.py` write the
   controls; the provenance gate requires a classification.
4. The projection and `visible(item, caller)`; the portal API views; the in-memory tools.
5. The interceptor writes the entitlement; the Gateway's tool schemas declare it; the graph and
   passage tools read it; the fixed SPARQL filters on it.
6. Knowledge Base metadata and filter.
7. Handling: `no-export` on links, `no-model` in refine, `expires` in the sweep, `quote-only` in
   the citation check.
8. The answer's classification in the agent's result and on the page; the workbench's steps.
9. The steward's view: a sweep's findings in the collection's status for private readers, and
   overrides kept as requests, with their reasons, applied by refine.
10. The marking detector and portion markings.
11. An evaluation set with controlled documents: questions that a cleared person can have
    answered and an uncleared one must be refused, scored like the others.
