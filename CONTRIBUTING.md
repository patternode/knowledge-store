# Contributing

Thanks for your interest. Issues and pull requests are welcome.

## Before you start

- For anything larger than a small fix, open an issue first so the approach can be agreed.
- Keep the core domain-agnostic: no code may name a term from any one domain's ontology. Domain behaviour belongs in an ontology, a profile, or an adapter package.
- New source types belong in their own package, registered through the `knowledge_store.ingestion.adapters.registry` entry point, unless they are generally useful.

## Development

```bash
python -m venv .venv && . .venv/bin/activate
pip install -e ".[dev]"
pytest
cd infra/stack && terraform init -backend=false && terraform validate
```

The stack itself is the module in `infra/modules/knowledge-store`; `infra/stack` and `examples/deployment` are roots that call it. When you move or rename a resource inside the module, add a `moved` block so existing deployments plan cleanly.

The documentation site is built with [Docusaurus](https://docusaurus.io/) from the repository's own Markdown (`npm ci`, then `npm run build`; `npm run start` previews it). The build is strict: a broken link, anchor or image fails it, and CI builds it on every pull request. A relative link to a file that is not a page (code, Terraform, a sample document) becomes a link to that file on GitHub, so write links as they read on GitHub. Which Markdown files are pages is decided in `site/src/remark-repo-links.cjs`; a merge to `main` publishes the site.

The tests run offline with a fake model (`tests/fake_llm.py`). Please add a test with every change in behaviour.

## Pull requests

- One change per pull request, into `main`, with the template filled in: what, why (with the issue, thread or decision it serves, or `No reference:` and the reason), how it was verified, and what a deployment needs.
- The title is a Conventional Commits subject (`feat(scope): what changed`), and so is every commit subject. The title becomes the squash subject, which is the change's line in the release notes and decides the next version (see Releases below). The PR check fails a title, a commit subject or a description that does not follow this.
- CI must pass: the tests and `terraform validate`.
- Contributions are licensed under the Apache License 2.0, as the rest of the project is (inbound equals outbound), and no separate agreement is needed. Please sign off your commits (`git commit -s`) to certify the [Developer Certificate of Origin](https://developercertificate.org/).

## Releases

Releases are made from the pull requests merged to `main`, by [Release Please](https://github.com/googleapis/release-please) in the `Release Please` workflow. Versions follow [semantic versioning](https://semver.org/) and tags are `vX.Y.Z`.

| What | Rule |
|---|---|
| The next version | From the squash subjects merged since the last tag: `feat` bumps the minor version, `fix` the patch, and a `!` after the type or a `BREAKING CHANGE:` footer marks a breaking change, which bumps the minor version until 1.0.0 and the major after. `docs`, `build`, `ci`, `chore`, `refactor`, `test`, `style` and `perf` never bump on their own |
| The changelog | One section per release in `CHANGELOG.md`, written by Release Please: `feat` lines under Added, `fix` under Fixed, `perf` under Changed, `docs` under Documentation, and breaking changes first. The other types are kept out. A pull request's title is its line, so write the title for a reader of the notes |
| The release pull request | Release Please keeps one open against `main`, `chore(main): release X.Y.Z`, and updates it on every merge. It bumps `version` in `pyproject.toml`, `__version__` in `src/knowledge_store/__init__.py`, `.release-please-manifest.json` and `CHANGELOG.md`. Merging it is the release: the workflow creates the tag and the GitHub Release with that section as its notes. Nothing else tags, and nobody edits those four files by hand |
| Pins | A deployment pins a tag, `ref=vX.Y.Z` in the module source (`examples/deployment/main.tf`), never a commit. To upgrade, move the tag, read the release's notes, plan and apply |
| 1.0.0 | A deliberate decision, made by adding `"release-as": "1.0.0"` to `release-please-config.json` for one release, not a consequence of a breaking change |

Before Release Please, versions were tagged by hand and `CHANGELOG.md` was written by hand. 0.2.0 was the last of those, cut from everything merged since 0.1.2. The workflow publishes a version the manifest names but no tag carries, from its `CHANGELOG.md` section, so a hand-cut version is possible but should not be needed again.

Settings the maintainer keeps (nothing in the repository can set them): the repository secret `RELEASE_PLEASE_TOKEN`, a fine-grained token scoped to this repository with contents and pull requests write, which the workflow uses to open the release pull request so that it gets CI runs (a pull request opened with the workflow's own token starts no other workflow, and the organisation may not allow Actions to open pull requests at all); and, under Pull Requests, the default squash message set to the pull request title. Without the secret the workflow falls back to its own token, which needs "Allow GitHub Actions to create and approve pull requests" on under Actions, and the release pull request then has no CI run until it is closed and reopened.

## Writing style

Prose in docs and comments avoids em dashes inside sentences and bold inside sentences. Use a comma, a colon, parentheses or two sentences instead.
