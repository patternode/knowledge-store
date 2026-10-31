# Standard: subdomains, bounded contexts, feature slices, ports and tests

Status: written at the owner's request on 20 October 2026. The owner accepted its text, and the decisions it rests on, patternode-architecture ADR-046, ADR-047 and ADR-048, on 31 October 2026, on the architecture master session's recommendation. The decisions behind it are patternode-architecture ADR-046 (contexts, slices and ports), ADR-044 (features as deployable slices), ADR-035 (independently deployable contexts, rule 1 as amended), ADR-047 (knowledge contexts on Knowledge Store) and ADR-048 (evaluation).

This standard says how code is cut, organised, deployed and tested in every Patternode repository, and what an agent does before, during and after a change. The same text sits in patternode-architecture (the source, `governance/standards/contexts-slices-and-ports.md`), patternode-platform (`docs/engineering-standard.md`) and knowledge-store (`docs/engineering-standard.md`). Each repository's copy ends with an appendix naming its own subdomains, contexts and checks. When the text and an appendix disagree, the text wins and the appendix is fixed. To change the text, change it in patternode-architecture first and copy it to the other two in the same week.

## 1. The words

| Word | Meaning | Where it is recorded |
|---|---|---|
| Subdomain | A part of the problem the business solves. Core: where Patternode differs. Supporting: needed, not differentiating. Generic: bought or shared. | The target state in patternode-architecture, and the repository's appendix |
| Bounded context | One model, consistent inside its boundary, with one published contract and the stores it alone writes. The unit of decomposition. In code, one package or Gradle project. | The target state; a context page in the repository that owns it |
| Contract | The one module other contexts may import: the names, types, read models, commands and events a context publishes. | The context's `__init__.py`, or its `-contract` module in Java |
| Feature slice | One use case or one feature inside a context, from its entry point to its data, over the context's domain. A slice with a UI or mounted by a host is also a feature (`FT-NNN`). | A module in the context's `slices/`; `runtime/features.csv` for a feature |
| Domain | The context's model and rules: pure code, no I/O, no environment, no SDK, no clock it did not receive. | The context's `domain/` |
| Port | An interface the context owns, shaped by what its domain needs, added only where an adapter varies. | The context's `ports.py` |
| Adapter | An implementation of a port, or a handler that drives a slice. The only place an SDK, driver, network call or file system access appears. | The context's `adapters/` |
| Kernel | Value types, helpers and a published vocabulary that several contexts share, and nothing else. It depends on no context. | `kernel/` |
| Composition root | The one module per deployable that reads configuration, builds adapters and wires slices. Nothing imports it. | `apps/` |
| Service | A deployable unit (a C4 container): one or more contexts of one product, each a separate module. | `runtime/services.csv` as `SV-NNN` |
| Product | What someone outside uses. It composes contexts through their contracts and owns no domain rule. | `products/` |

## 2. Before you write code

1. Name the subdomain and the bounded context the change belongs to. Read the repository's appendix and the context's page. If the change fits no context, stop and say so: a new context is a design change, recorded in patternode-architecture first (a consideration or a decision record), then built.
2. Name the slice. A change to an existing use case goes in its slice. A new use case is a new slice. A change that touches several contexts goes through their contracts, never into their internals.
3. Decide whether a port is needed. Add one only when an adapter varies today or is planned: a second store, a second provider, a test double the slice tests need. If nothing varies, the slice calls a plain function.
4. Decide what tests the change needs (section 7) before writing it.

## 3. Where code goes

| The code | Goes in |
|---|---|
| A rule, a calculation, a validation, a model type | The context's `domain/` |
| A use case: read through ports, apply the domain, write through ports | A module in the context's `slices/` |
| An interface for something that varies | The context's `ports.py` |
| A call to AWS, GCP, a database, a model provider, HTTP, the file system | A module in the context's `adapters/` |
| A Lambda handler, an AgentCore entry point, a CLI command or a job that drives one context | That context's `adapters/` |
| An entry point that composes several contexts, or reads configuration for a deployable | `apps/` |
| A value type or vocabulary several contexts need | `kernel/` |
| Logic two slices share | The context's `domain/`, never a copy in each slice |
| A tunable number or name that a rule uses (a limit, a model id) | Read through `kernel/settings.py`; nowhere else outside adapters and `apps/` |
| A page or UI the product shows | The product's package (for example `analyst_site/`), or a feature's `pn-` element |

## 4. Inside a context

```
<context>/
  __init__.py     the contract: the names other contexts may import, loaded on first use
  domain/         pure: the model and its rules
  ports.py        Protocols, only where an adapter varies
  slices/         one module per use case
  adapters/       implementations of the ports, and the handlers that drive slices
```

1. Imports run one way: adapters may use slices, slices may use ports, ports may use the domain. Never the reverse.
2. Another context imports only from the contract: `from <package>.<context> import Name`. Never from its `domain`, `slices`, `ports` or `adapters`.
3. A context's contract lists every name it publishes and the module it lives in. Add a name when another context needs it; remove one only after its last user has moved (expand, then contract).
4. Contexts depend on each other without a cycle. When two contexts need each other, one of them owns the shared language and the other conforms, or the shared part moves to the kernel as a vocabulary. Record the relationship (customer and supplier, conformist, published language, open host, anti-corruption layer) on both context pages.
5. A foreign model (a vendor API, a broker, a regulator's filings) enters through an anti-corruption layer in an adapter. The domain never sees the foreign shape.
6. Configuration is read once, in a composition root or an adapter, and passed in. Time comes from an injected clock.
7. In Java the same rules apply with the platform's modules: `{bc}-domain` (domain and ports), `{bc}-service` (slices as packages), `{bc}-adapters`, and a `{bc}-contract` module where a context publishes to others.

## 5. Between contexts and products

1. A product composes contexts through their contracts and owns no domain rule. No context imports a product's package.
2. A context reads another context's data only through a published read model, an API or an event. No context reads or writes another's store.
3. A context that several products use (Knowledge Store's contexts, the Product Platform) is used by contract, pinned to a release tag, never copied. A file copied into another image is listed in the appendix and tested to import with what that image carries.

## 6. Deployment

1. Every context can be deployed on its own: extracting it into a service is a change to infrastructure, never to its code or its data.
2. A context is deployed on its own only when an ADR-044 trigger applies: it needs another runtime, two hosts need it at different versions, its failure must be isolated, or its scaling or cost profile differs. Otherwise the contexts of one product that share a runtime run in one service.
3. A pull request that splits a context into its own service names the trigger, and updates `runtime/services.csv`.
4. Every deployable has one composition root in `apps/` (or the Java application module), and its handler path, image command and Terraform name it.

## 7. Tests

Tests are organised by context and level, and each level has one job.

| Level | What it proves | Where | Rules |
|---|---|---|---|
| Unit | Each domain rule, one behaviour per test | `tests/<context>/unit/test_<module>.py` | Pure: no I/O, network, environment or real clock. Every domain module has a unit test file. Fast: the whole level runs in seconds. |
| Slice | Each use case does what it promises through its ports | `tests/<context>/slices/test_<slice>.py` | The ports are in-memory fakes (a local folder lake, a fake model client), not mocks of internals. Every slice has a test file. Arrange, act, assert. |
| Port contract | Every adapter honours its port the same way | `tests/<context>/contracts/test_<port>.py` | One parametrised contract per port, run against every adapter. An adapter that needs a service (Neo4j, MongoDB) runs against its emulator and skips cleanly without it. |
| Context contract | What a consumer relies on from another context's contract still holds | `tests/contracts/test_<provider>_for_<consumer>.py` | Written by the consumer, naming each published name and behaviour it uses. A provider change that breaks one fails the provider's build. |
| Architecture | The boundaries hold | `tests/test_architecture.py` and import-linter (ArchUnit or Spring Modulith in Java) | Never loosened to make a change pass. A failure is a design question. |
| Deployable | Each composition root starts and serves one request end to end, with fakes behind its ports | `tests/apps/test_<app>.py` | One happy path and one refusal per deployable. Imports with only what its image carries. |
| Evaluation | The deployed system gives right answers | The Evaluation context's sets (ADR-048) | Run before a release and against a baseline; costs money, so a person starts it. |

Rules for every level:

1. A change in behaviour comes with a test at the lowest level that can show it, and a slice test when the use case changes.
2. A bug fix comes with a test that fails before the fix.
3. Test names state the behaviour in plain words (`test_a_cited_hedge_is_a_right_decline`), not the function under test.
4. Prefer fakes that implement a port over mocks that patch internals. Patch a module only at an adapter boundary.
5. Tests are offline by default. Anything that needs a network, a cloud account or a paid model is marked and skipped without it.
6. Markers: `unit`, `slice`, `contract`, `architecture`, `deployable`. `pytest -m unit` runs one level.
7. Coverage is measured per context and per layer, and each has a floor in the repository's configuration. The floor only rises: a change that lowers a context's coverage below its floor fails. Targets: domain 95%, slices 90%, adapters 80% (with emulator-backed ones counted where emulators run).
8. A test that fails before a change and still fails after it is recorded in the appendix's known-failures list with its cause, never deleted or skipped to make a run green.

## 8. Keeping it that way

1. `pytest` runs the architecture tests and import-linter's contracts with everything else. A pull request with a failing check is not ready.
2. When a context gains or loses a layer, regenerate the import-linter contracts in the same pull request.
3. When a check fails, fix the design: move the code to where it belongs, publish the name in the contract, or invert the dependency. Never add an exception to make a check pass without a decision record that names it.
4. Keep the context pages, the services register and the appendix in step with the code in the same pull request.

## 9. Pull request checklist

- [ ] The subdomain, context and slice the change belongs to are named in the description.
- [ ] No context imports another's internals; new cross-context needs are in the provider's contract.
- [ ] No SDK, network or environment read in a domain; configuration read in a composition root, an adapter or `kernel/settings.py`.
- [ ] Tests at each level the change touches; a failing test first for a bug fix.
- [ ] `pytest` passes, including the architecture tests; coverage floors hold.
- [ ] Context pages, the services register and the appendix updated if the structure changed.
- [ ] A new context, a split into a service, or an exception to this standard has a decision record.

## Example: import-linter contracts

```toml
[tool.importlinter]
root_package = "knowledge_store"
include_external_packages = true
exclude_type_checking_imports = true

[[tool.importlinter.contracts]]
name = "answering: adapters, slices, ports, domain, in that order"
type = "layers"
layers = ["knowledge_store.answering.adapters", "knowledge_store.answering.slices", "knowledge_store.answering.ports", "knowledge_store.answering.domain"]

[[tool.importlinter.contracts]]
name = "answering: other contexts use only its contract"
type = "forbidden"
source_modules = ["knowledge_store.ingestion", "knowledge_store.ontology"]
forbidden_modules = ["knowledge_store.answering.domain", "knowledge_store.answering.slices", "knowledge_store.answering.ports", "knowledge_store.answering.adapters"]
allow_indirect_imports = true

[[tool.importlinter.contracts]]
name = "Domains import no SDK or driver"
type = "forbidden"
source_modules = ["knowledge_store.answering.domain"]
forbidden_modules = ["boto3", "botocore", "anthropic", "neo4j"]
allow_indirect_imports = true
```

A repository runs its contracts from a test (`tests/test_architecture.py`), in a subprocess, so a violation fails the same `pytest` run as everything else.

## Appendix: knowledge-store

### Subdomains and contexts

| Context | Kind | Package | Contract highlights | Composition roots that use it |
|---|---|---|---|---|
| BC-001 Ingestion | Supporting | `ingestion` | `ingest_source`, `bronze_objects`, `load_doc`, `load_passages`, `silver_doc_ids`, `Passage` | `apps/sweep.py`, `apps/cli.py` |
| BC-002 Ontology | Core | `ontology` | the model, renditions, versions, the tool schema, mappings | the sweep, the CLI |
| BC-003 Extraction | Core | `extraction` | table bindings, `mapped_doc_ids`, `data_base` | the sweep, the CLI |
| BC-004 Knowledge graph | Core | `knowledge_graph` | `ReadModel`, `GraphStore`, `SparqlStore`, `PassageSearch`, the read tools | the sweep, `apps/portal_api.py`, the tools Lambda |
| BC-005 Answering | Core | `answering` | `ClaimVerifier`, `QuestionScreen`, `answer_locally`, `run`, `Guardrail` | `apps/agent.py`, `apps/portal_api.py` |
| BC-006 Access | Supporting | `access` | `agent_quota`; claims, state and the interceptor are used by their deployables | `apps/agent.py`, `apps/portal_api.py`, the interceptor Lambda |
| BC-007 Evaluation | Supporting | `evaluation` | the set model, scoring, `run`, `gate`, the answerers, verifiers and runners | `apps/evaluate.py` |
| BC-008 Platform services | Generic | `platform_services` | `Store`, `ModelClient`, `layout`, `llm`, `ledger`, collections and configuration | every deployable |

The contexts page, `docs/architecture/solution/contexts/README.md`, has the view and each context's page.

### Checks

- `pytest` runs everything, including `tests/test_architecture.py` (import-linter's contracts from `pyproject.toml`, configuration reads, no network client in a domain, no cycle between contexts, every published name resolves, the Lambdas import with the standard library and boto3 alone).
- `pytest -m unit`, `-m slice`, `-m contract`, `-m architecture`, `-m deployable` run one level; the markers come from each test's folder.
- Coverage floors per context and layer are in `tests/coverage-floors.json`, checked by `tests/check_coverage.py` after a run with `--cov`.

### What other images carry

The portal and tool Lambdas are zips of the source with no dependencies; the runtime provides boto3. Every context's contract loads its names on first use so that importing it there does not pull in rdflib.

### Known failures

None.

### Exceptions

- The model client port (`platform_services.ports.ModelClient`) still speaks Bedrock's Converse shape (ADR-011 records it as a follow-up).
- The plug-in entry point group for source adapters stays `knowledge_store.adapters`, a published name, not a module path.
