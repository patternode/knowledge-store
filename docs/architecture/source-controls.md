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
| A curator | an override that tightens a document, or a correction with a reason | the portal, as a request kept in the lake, like an ontology request |

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
9. The marking detector and portion markings.
10. An evaluation set with controlled documents: questions that a cleared person can have
    answered and an uncleared one must be refused, scored like the others.
