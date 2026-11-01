# Agent notes

A live deployment does not follow this repository. It runs the module pin (`source` `ref=`) in
its own Terraform, and a merge to `main` here does not change it. The deployment keeps the old
pages until a release carrying the change is tagged, the deployment moves its pin to that tag,
and the change is applied there. A user-visible change is not live anywhere until all three have
happened.

If the agent image changed, a deployment that moves its pin leaves `agent.runtime = false` for
one apply, then sets it `true` once the image is in ECR (`knowledge-store-agent`). The steps are
in the [deployment guide](docs/deploy/aws/README.md).

<!-- playbook:begin 1.1.0 sha256:44aae636393c49d7: generated from patternode-architecture governance/playbook/agents-block.md by playbook.mjs sync. Do not edit here. -->

## The Patternode playbook

One playbook governs how change moves in every Patternode repository: improvements, branches, commits, pull requests, merging, contracts, versions, releases, deploys, and who may do what. It wins over every other page on those topics, this file included. A repository's own documents add facts and procedures only.

Read it before you branch, open or merge a pull request, change a contract, release or deploy. It is the same file in three places; use the first you can reach:

1. `.agents/skills/patternode-playbook/SKILL.md`, the installed copy.
2. `../patternode-architecture/governance/playbook/SKILL.md`, a sibling clone.
3. https://github.com/patternode/patternode-architecture/blob/main/governance/playbook/SKILL.md

This repository's facts (its trunk, who merges, who releases, where its procedures are) are in `.agents/playbook.yaml`.

Even before you have read it:

- Trunk-based development, never Git Flow. No release, hotfix or long-lived feature branches. Branch from the remote trunk named in `.agents/playbook.yaml`. A branch called `develop`, `deploy` or `master` does not mean Git Flow: the profile says which branch is the trunk, and a production pointer or mirror is never a branch to work on.
- One change, one short-lived branch, one pull request into the trunk, citing its reason (`IMP-NNN`, an issue, a thread, an ADR, or `No reference:` and why). Push before your session ends.
- Merge, deploy, release or apply infrastructure only if `.agents/playbook.yaml` names your role. Otherwise send the ready note to the role that does, and stop.
- Units meet only through contracts. A contract change is its own pull request in the provider's repository, before any code that uses it, and never breaks a consumer.
- New behaviour ships switched off. Turning it on is a release: a change of its own, reversible.

<!-- playbook:end -->

## Versions and releases

People run pinned releases of this repository, so every change is versioned. The full rules are in [CONTRIBUTING.md](CONTRIBUTING.md#releases); the ones an agent needs:

1. A pull request's title is a Conventional Commits subject, `type(scope): what changed`, written for someone reading the release notes: it becomes the squash subject, which is the change's line in `CHANGELOG.md` and the GitHub Release. `feat` bumps the minor version, `fix` the patch, and a `!` after the type (or a `BREAKING CHANGE:` footer in the description) marks a breaking change, which bumps the minor version until 1.0.0. `docs`, `build`, `ci`, `chore`, `refactor`, `test` and `style` never bump. The PR check fails a title or a commit subject in another form, and a description that cites no reason for the change.
2. Pull requests go into `main` and are squash merged with the title as the subject. `develop` is not a staging branch any more: the release pull request batches what has merged, so open nothing into `develop`.
3. Never edit the version by hand: not `version` in `pyproject.toml`, not `__version__` in `src/knowledge_store/__init__.py`, not `.release-please-manifest.json`, and not `CHANGELOG.md`. Release Please writes all four in the release pull request (`chore(main): release X.Y.Z`), which it keeps open against `main` and updates on every merge. Merging it is the release: the tag `vX.Y.Z` and the GitHub Release follow from the `Release Please` workflow, and nothing else tags.
4. A deployment pins a tag, never a commit: `ref=vX.Y.Z` in the module source, in `examples/deployment/main.tf` here and in any deployment's own Terraform. Moving a deployment's pin is the step in the first section of this file, and it moves to a release, so a change reaches a deployment only after the release pull request that carries it is merged.

## Code layout

Follow [the engineering standard](docs/engineering-standard.md) for every change: name the subdomain, bounded context and slice first, put the code where its section 3 says, and add tests at the levels its section 7 sets. Its appendix lists this repository's contexts and checks. The points below are the ones agents most often need.

The code is cut by bounded context, as patternode-architecture ADR-046 sets out, and the tests hold it there. Read [the contexts page](docs/architecture/solution/contexts/README.md) before moving code.

1. Each context is a package in `src/knowledge_store/` (`ingestion`, `ontology`, `extraction`, `knowledge_graph`, `answering`, `access`, `evaluation`, `platform_services`). Its `__init__` is its contract: the names other contexts may import, loaded on first use. Another context imports only from that package, never from its `domain`, `slices`, `ports` or `adapters`.
2. Inside a context: `domain/` is pure (no I/O, no environment, no SDK), `slices/` holds one module per use case, `ports.py` holds the Protocols where an adapter varies, and `adapters/` is the only place an SDK, a driver or a network call appears. Imports run adapters, then slices, then ports, then domain, never the other way.
3. Composition roots, one per deployable, are in `apps/`: the sweep, the portal API, the agent, the command line, the local portal and the evaluation runner. They read configuration and wire adapters; nothing imports them. Tunable limits that domain rules use are read through `kernel/settings.py`, and nowhere else outside adapters and `apps/`.
4. `kernel/` holds value types and helpers several contexts share, and depends on no context.
5. `pytest` runs the checks: import-linter's contracts (in `pyproject.toml`, regenerated when a context gains or loses a layer) and `tests/test_architecture.py` (configuration reads, network clients in domains, no cycle between contexts, every published name resolves, the Lambdas import with the standard library and boto3 alone). A failing check is a design question, not a test to loosen.
6. The plug-in entry point group for source adapters stays `knowledge_store.adapters`; it is a published name, not a module path.

## Architecture

The architecture lives in this repository, under [docs/architecture](docs/architecture/README.md), in the layout every repository on the architecture continuum uses (the platform and landscape, then `demand/`, `solution/`, `runtime/`, `decisions/` and `registers/`); the design notes behind it are under [docs/design](docs/design/README.md). The catalogue is expressed with the continuum: outcomes, use cases, capabilities, the product and its features, bounded contexts, building blocks, architecture patterns and reference architectures, contracts, services, nodes, stores, decisions and considerations, each with an identifier (`PL`, `OC`, `UC`, `CAP`, `PRD`, `FE`, `BC`, `ABB`, `SBB`, `AP`, `RA`, `CT`, `SV`, `DN`, `ST`, `ADR`, `CN`) and a register. `.agents/skills.json` declares the skills that write and check it and `.agents/skill-bindings.toml` says where each kind lives.

1. A change that adds or changes a deployable, a store, a contract or a context updates the matching register and page in the same pull request. The services register is what a reconcile check will read.
2. A design question with more than one credible answer is a consideration (`CN-NNN`); settling it is a decision record (`ADR-NNN`). Write the note where the reasoning is long and the record where the register points.
3. Keep the prose rules: no em dashes or bold inside sentences, one paragraph per line, British spelling.
4. The architecture skills are optional, and nothing else in this repository needs them: the site build, the tests and the deployment checks read no skill, and no workflow runs the architecture check. Dermot checks the architecture at checkpoints of his choosing: `npm run skills` installs the skills once (`node scripts/skills.mjs sync --locked --copy`, the installer copied from AI-Assisted Work, fetching the releases `.agents/skills.json` declares at the commits `.agents/skills.lock.json` pins; the installed folders are not committed), and `npm run check:architecture` runs the `aaa-continuum` check over `docs/architecture`, failing on any finding. Without the skills installed it says so in one line and exits 0, so a clone without them is complete; `node scripts/skills.mjs check` reports a missing or changed skill.
