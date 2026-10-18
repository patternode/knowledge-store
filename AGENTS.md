# Agent notes

A live deployment does not follow this repository. It runs the module pin (`source` `ref=`) in
its own Terraform, and a merge to `main` here does not change it. The deployment keeps the old
pages until a release carrying the change is tagged, the deployment moves its pin to that tag,
and the change is applied there. A user-visible change is not live anywhere until all three have
happened.

If the agent image changed, a deployment that moves its pin leaves `agent.runtime = false` for
one apply, then sets it `true` once the image is in ECR (`knowledge-store-agent`). The steps are
in the [deployment guide](docs/deploy/aws/README.md).

## Versions and releases

People run pinned releases of this repository, so every change is versioned. The full rules are in [CONTRIBUTING.md](CONTRIBUTING.md#releases); the ones an agent needs:

1. A pull request's title is a Conventional Commits subject, `type(scope): what changed`, written for someone reading the release notes: it becomes the squash subject, which is the change's line in `CHANGELOG.md` and the GitHub Release. `feat` bumps the minor version, `fix` the patch, and a `!` after the type (or a `BREAKING CHANGE:` footer in the description) marks a breaking change, which bumps the minor version until 1.0.0. `docs`, `build`, `ci`, `chore`, `refactor`, `test` and `style` never bump. The PR check fails a title or a commit subject in another form, and a description that cites no reason for the change.
2. Pull requests go into `main` and are squash merged with the title as the subject. `develop` is not a staging branch any more: the release pull request batches what has merged, so open nothing into `develop`.
3. Never edit the version by hand: not `version` in `pyproject.toml`, not `__version__` in `src/knowledge_store/__init__.py`, not `.release-please-manifest.json`, and not `CHANGELOG.md`. Release Please writes all four in the release pull request (`chore(main): release X.Y.Z`), which it keeps open against `main` and updates on every merge. Merging it is the release: the tag `vX.Y.Z` and the GitHub Release follow from the `Release Please` workflow, and nothing else tags.
4. A deployment pins a tag, never a commit: `ref=vX.Y.Z` in the module source, in `examples/deployment/main.tf` here and in any deployment's own Terraform. Moving a deployment's pin is the step in the first section of this file, and it moves to a release, so a change reaches a deployment only after the release pull request that carries it is merged.

## Architecture

The architecture lives in this repository, under [docs/architecture](docs/architecture/README.md), in the layout every repository on the architecture continuum uses (the platform and landscape, then `demand/`, `solution/`, `runtime/`, `decisions/` and `registers/`); the design notes behind it are under [docs/design](docs/design/README.md). The catalogue is expressed with the continuum: outcomes, use cases, capabilities, the product and its features, bounded contexts, building blocks, architecture patterns and reference architectures, contracts, services, nodes, stores, decisions and considerations, each with an identifier (`PL`, `OC`, `UC`, `CAP`, `PRD`, `FE`, `BC`, `ABB`, `SBB`, `AP`, `RA`, `CT`, `SV`, `DN`, `ST`, `ADR`, `CN`) and a register. `.agents/skills.json` declares the skills that write and check it and `.agents/skill-bindings.toml` says where each kind lives.

1. A change that adds or changes a deployable, a store, a contract or a context updates the matching register and page in the same pull request. The services register is what a reconcile check will read.
2. A design question with more than one credible answer is a consideration (`CN-NNN`); settling it is a decision record (`ADR-NNN`). Write the note where the reasoning is long and the record where the register points.
3. Keep the prose rules: no em dashes or bold inside sentences, one paragraph per line, British spelling.
4. The architecture skills are optional, and nothing else in this repository needs them: the site build, the tests and the deployment checks read no skill, and no workflow runs the architecture check. Dermot checks the architecture at checkpoints of his choosing: `npm run skills` installs the skills once (`node scripts/skills.mjs sync --locked --copy`, the installer copied from AI-Assisted Work, fetching the releases `.agents/skills.json` declares at the commits `.agents/skills.lock.json` pins; the installed folders are not committed), and `npm run check:architecture` runs the `aaa-continuum` check over `docs/architecture`, failing on any finding. Without the skills installed it says so in one line and exits 0, so a clone without them is complete; `node scripts/skills.mjs check` reports a missing or changed skill.
