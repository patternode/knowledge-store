# Contributing

Thanks for your interest. Issues and pull requests are welcome.

## Before you start

- For anything larger than a small fix, open an issue first so the approach can be agreed.
- Keep the core domain-agnostic: no code may name a term from any one domain's ontology. Domain behaviour belongs in an ontology, a profile, or an adapter package.
- New source types belong in their own package, registered through the `knowledge_store.adapters` entry point, unless they are generally useful.

## Development

```bash
python -m venv .venv && . .venv/bin/activate
pip install -e ".[dev]"
pytest
cd infra/stack && terraform init -backend=false && terraform validate
```

The tests run offline with a fake model (`tests/fake_llm.py`). Please add a test with every change in behaviour.

## Pull requests

- One change per pull request, with a clear description of what and why.
- Commit messages follow Conventional Commits (`feat:`, `fix:`, `docs:` and so on).
- CI must pass: the tests and `terraform validate`.
- Contributions are licensed under the Apache License 2.0, as the rest of the project is (inbound equals outbound), and no separate agreement is needed. Please sign off your commits (`git commit -s`) to certify the [Developer Certificate of Origin](https://developercertificate.org/).

## Writing style

Prose in docs and comments avoids em dashes inside sentences and bold inside sentences. Use a comma, a colon, parentheses or two sentences instead.
