# Architecture building blocks

Logical, technology-agnostic, each inside one bounded context, each with published interfaces and the three cross-cutting sections the standard requires. Fourteen at container grain, recalibrated on 2026-10-17 under the [building block calibration standard](https://github.com/dermot-obrien/architecture-continuum/blob/main/standards/building-blocks/standard-building-block-calibration.md): every block is one C4 container, a separately deployable unit that executes code or stores data, and nothing smaller. The register is [../abbs.csv](../abbs.csv), which also lists the retired identifiers; each page names the code that holds it today and the components it absorbed.

<div className="ks-cards">
<div className="ks-card">

<p className="ks-card__head"><span className="ks-card__id">ABB-002</span> <span className="ks-card__tag">BC-001</span> <span className="ks-card__tag">Data</span></p>

#### [Lake](ABB-002-lake/index.md)

The record of everything: one object store behind one port, with a stated layout of layers, the ontology versions, the candidate register and the ledger, so that every other store is a projection that can be rebuilt from it.

<dl className="ks-card__facts"><dt>Realises</dt><dd>CAP-002, CAP-003</dd><dt>Realised by</dt><dd>SBB-001</dd></dl>

</div>
<div className="ks-card">

<p className="ks-card__head"><span className="ks-card__id">ABB-024</span> <span className="ks-card__tag">BC-001</span> <span className="ks-card__tag">Processing</span></p>

#### [Ingestion and extraction pipeline](ABB-024-ingestion-and-extraction-pipeline/index.md)

One container that takes a collection from uploaded bytes to published, checkable facts: it acquires, refines, discovers and reviews an ontology, extracts with provenance, binds tables, projects and loads, in one idempotent sweep under a lock. It composes four bounded contexts today (CN-006).

<dl className="ks-card__facts"><dt>Realises</dt><dd>CAP-002, CAP-003, CAP-004, CAP-005, CAP-006, CAP-007</dd><dt>Realised by</dt><dd>SBB-002</dd></dl>

</div>
<div className="ks-card">

<p className="ks-card__head"><span className="ks-card__id">ABB-011</span> <span className="ks-card__tag">BC-004</span> <span className="ks-card__tag">Knowledge graph</span></p>

#### [Knowledge graph](ABB-011-knowledge-graph/index.md)

The graph projection of the gold record: one named graph per document per ontology version plus the T-Box, in a SPARQL store the graph tools query read-only, rebuilt from the lake whenever needed.

<dl className="ks-card__facts"><dt>Realises</dt><dd>CAP-005</dd><dt>Realised by</dt><dd>SBB-003, SBB-011</dd></dl>

</div>
<div className="ks-card">

<p className="ks-card__head"><span className="ks-card__id">ABB-013</span> <span className="ks-card__tag">BC-004</span> <span className="ks-card__tag">Knowledge graph</span></p>

#### [Passage index](ABB-013-passage-index/index.md)

Search of passages by meaning as its own store: one vector per passage, synced from the lake, so that a hit is a passage id the checks can re-read.

<dl className="ks-card__facts"><dt>Realises</dt><dd>CAP-006</dd><dt>Realised by</dt><dd>SBB-004</dd></dl>

</div>
<div className="ks-card">

<p className="ks-card__head"><span className="ks-card__id">ABB-012</span> <span className="ks-card__tag">BC-004</span> <span className="ks-card__tag">Knowledge graph</span></p>

#### [Graph tools](ABB-012-graph-tools/index.md)

The fixed, read-only tools over the graph and the bound tables, in the ontology's terms, as one function behind the gateway: no free query reaches a store, and every result is filtered by the caller's scope.

<dl className="ks-card__facts"><dt>Realises</dt><dd>CAP-005, CAP-007, CAP-009</dd><dt>Realised by</dt><dd>SBB-005</dd></dl>

</div>
<div className="ks-card">

<p className="ks-card__head"><span className="ks-card__id">ABB-025</span> <span className="ks-card__tag">BC-004</span> <span className="ks-card__tag">Knowledge graph</span></p>

#### [Passage tools](ABB-025-passage-tools/index.md)

Search and read of passages as one function behind the gateway: by meaning through the index when there is one, by keyword otherwise, always returning passage ids the checks can re-read.

<dl className="ks-card__facts"><dt>Realises</dt><dd>CAP-006, CAP-009</dd><dt>Realised by</dt><dd>SBB-015</dd></dl>

</div>
<div className="ks-card">

<p className="ks-card__head"><span className="ks-card__id">ABB-026</span> <span className="ks-card__tag">BC-004</span> <span className="ks-card__tag">Knowledge graph</span></p>

#### [Tool gateway](ABB-026-tool-gateway/index.md)

The one MCP front over the tools: it verifies the caller's token, runs the interceptor on every call, and routes to the graph tools or the passage tools, so that the agent never addresses a function directly.

<dl className="ks-card__facts"><dt>Realises</dt><dd>CAP-009</dd><dt>Realised by</dt><dd>SBB-016</dd></dl>

</div>
<div className="ks-card">

<p className="ks-card__head"><span className="ks-card__id">ABB-027</span> <span className="ks-card__tag">BC-006</span> <span className="ks-card__tag">Security</span></p>

#### [Call interceptor](ABB-027-call-interceptor/index.md)

The function the gateway runs on every tool call, which turns the caller's identity into the one access decision the store makes today: whether private sources are visible (ADR-010).

<dl className="ks-card__facts"><dt>Realises</dt><dd>CAP-009</dd><dt>Realised by</dt><dd>SBB-017</dd></dl>

</div>
<div className="ks-card">

<p className="ks-card__head"><span className="ks-card__id">ABB-014</span> <span className="ks-card__tag">BC-005</span> <span className="ks-card__tag">Answering</span></p>

#### [Answering agent](ABB-014-answering-agent/index.md)

The container that answers: it plans in the ontology's terms, calls the fixed tools as the person asking, proposes claims with citations, re-reads and checks every citation, repairs once, applies the guardrail, and shows nothing unchecked, under valves and with every step recorded and priced.

<dl className="ks-card__facts"><dt>Realises</dt><dd>CAP-008, CAP-010, CAP-012</dd><dt>Realised by</dt><dd>SBB-006</dd></dl>

</div>
<div className="ks-card">

<p className="ks-card__head"><span className="ks-card__id">ABB-019</span> <span className="ks-card__tag">BC-006</span> <span className="ks-card__tag">Portal</span></p>

#### [Chat API](ABB-019-chat-api/index.md)

The one HTTP door into the store: it verifies who is asking, takes the quota, dispatches the question to the agent as that person, keeps the answer and the steps, serves the index-backed views, and signs links into the lake.

<dl className="ks-card__facts"><dt>Realises</dt><dd>CAP-009, CAP-010, CAP-012</dd><dt>Realised by</dt><dd>SBB-007</dd></dl>

</div>
<div className="ks-card">

<p className="ks-card__head"><span className="ks-card__id">ABB-018</span> <span className="ks-card__tag">BC-006</span> <span className="ks-card__tag">Portal</span></p>

#### [Chat page](ABB-018-chat-page/index.md)

The static site a reader uses: the question, the answer with its claims, sources and steps, the ontology page, and the workbench panel for curators, embedded by a host website or served on its own.

<dl className="ks-card__facts"><dt>Realises</dt><dd>CAP-009, CAP-012</dd><dt>Realised by</dt><dd>SBB-018</dd></dl>

</div>
<div className="ks-card">

<p className="ks-card__head"><span className="ks-card__id">ABB-020</span> <span className="ks-card__tag">BC-006</span> <span className="ks-card__tag">Security</span></p>

#### [Identity](ABB-020-identity/index.md)

The identity provider: the people and the service clients, the private-readers group, and the tokens every other container verifies, so that the person's identity goes all the way down (ADR-003).

<dl className="ks-card__facts"><dt>Realises</dt><dd>CAP-009</dd><dt>Realised by</dt><dd>SBB-008</dd></dl>

</div>
<div className="ks-card">

<p className="ks-card__head"><span className="ks-card__id">ABB-028</span> <span className="ks-card__tag">BC-008</span> <span className="ks-card__tag">Platform services</span></p>

#### [Command line](ABB-028-command-line/index.md)

The command an operator or curator runs: the whole pipeline in one process over a folder or the bucket, the ontology release commands that publish, activate and propose versions under the release controls, the ledger report, and a local portal server.

<dl className="ks-card__facts"><dt>Realises</dt><dd>CAP-002, CAP-003, CAP-004, CAP-005, CAP-007, CAP-008, CAP-010, CAP-013</dd><dt>Realised by</dt><dd>SBB-013</dd></dl>

</div>
<div className="ks-card">

<p className="ks-card__head"><span className="ks-card__id">ABB-021</span> <span className="ks-card__tag">BC-007</span> <span className="ks-card__tag">Evaluation</span></p>

#### [Evaluation runner](ABB-021-evaluation-runner/index.md)

The command that runs a set of questions against a lake or a deployed chat, scores each answer deterministically against the facts it must and must not state and the sources it should cite, and reports.

<dl className="ks-card__facts"><dt>Realises</dt><dd>CAP-011</dd><dt>Realised by</dt><dd>SBB-019</dd></dl>

</div>
</div>
The first pass had twenty-three blocks, nine of which were components of the pipeline container and four of the agent. The calibration folded them: ABB-001 Source adapters into ABB-024, ABB-003 Document refinement into ABB-024, ABB-004 Sweep orchestration into ABB-024, ABB-005 Ontology discovery and review into ABB-024, ABB-006 Ontology versioning and renditions into ABB-024, ABB-007 Candidate register and revision proposal into ABB-024, ABB-008 Table mapping definition into ABB-024, ABB-009 Ontology-guided extraction into ABB-024, ABB-010 Table binding into ABB-024, ABB-015 Claim grounding and checks into ABB-014, ABB-016 Valves and quotas into ABB-014, ABB-017 Workbench into ABB-014, ABB-022 Model access and ledger into ABB-014, ABB-023 Deployment automation with no container. Their pages are gone; the register keeps each identifier as retired, with the container it folded into, so it is never reused.

ABB-024 composes four bounded contexts in one container today (CN-006): the ontology and extraction contexts, BC-002 and BC-003, have no container of their own, and their components run inside it. The requires relations still form a directed graph with no cycles: the lake at the bottom, the pipeline and the stores above it, the tools behind the gateway above those, the agent, the API and the page at the top, with identity, the interceptor and the operator commands beside.
