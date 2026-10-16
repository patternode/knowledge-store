# Agent notes

Patternode's live lab does not follow this repository. It runs the module pin in
patternode-platform `deployments/knowledge-store/main.tf` (`source` `ref=`) from the last
applied `deploy` revision. A merge to `main` here does not change the lab, and neither does
merging that pin, until the revision is promoted and Dermot applies it. The lab keeps the old
pages until then. This has been missed repeatedly, and the lab has looked broken each time.

When you merge a user-visible change to `main`, open that platform pull request in the same
piece of work. If the agent image changed, the platform change leaves `agent.runtime = false`
for one apply, then a following change sets it `true` once the image is in ECR
(`knowledge-store-agent`). The steps are in that deployment's README, under "For agents".

## Versions and releases

People run pinned releases of this repository, so every change is versioned. The full rules are in [CONTRIBUTING.md](CONTRIBUTING.md#releases); the ones an agent needs:

1. A pull request's title is a Conventional Commits subject, `type(scope): what changed`, written for someone reading the release notes: it becomes the squash subject, which is the change's line in `CHANGELOG.md` and the GitHub Release. `feat` bumps the minor version, `fix` the patch, and a `!` after the type (or a `BREAKING CHANGE:` footer in the description) marks a breaking change, which bumps the minor version until 1.0.0. `docs`, `build`, `ci`, `chore`, `refactor`, `test` and `style` never bump. The PR check fails a title or a commit subject in another form, and a description that cites no reason for the change.
2. Pull requests go into `main` and are squash merged with the title as the subject. `develop` is not a staging branch any more: the release pull request batches what has merged, so open nothing into `develop`.
3. Never edit the version by hand: not `version` in `pyproject.toml`, not `__version__` in `src/knowledge_store/__init__.py`, not `.release-please-manifest.json`, and not `CHANGELOG.md`. Release Please writes all four in the release pull request (`chore(main): release X.Y.Z`), which it keeps open against `main` and updates on every merge. Merging it is the release: the tag `vX.Y.Z` and the GitHub Release follow from the `Release Please` workflow, and nothing else tags.
4. A deployment pins a tag, never a commit: `ref=vX.Y.Z` in the module source, in `examples/deployment/main.tf` here and in patternode-platform `deployments/knowledge-store/main.tf`. Moving the platform pin is the step in the first section of this file, and it moves to a release, so a change reaches the lab only after the release pull request that carries it is merged.
