# Deployments other than AWS

Each cloud's deployment code lives in its own folder here, next to nothing of another cloud's:

| Folder | Holds | Guide |
|---|---|---|
| [`azure/`](azure) | `bootstrap/` (Terraform state), `modules/knowledge-store/` (the module), `stack/` (the reference root), `function/` (the Function App) and `package_function.py` (its zip) | [azure-setup.md](../docs/architectures/azure-setup.md) |

Google Cloud will go in `gcp/`; for now it is a design, in [gcp.md](../docs/architectures/gcp.md).

AWS, the reference implementation, stays in [`infra/`](../infra), because deployments pin its
module path (`//infra/modules/knowledge-store`). Moving it would break every pinned deployment.

The core these deploy (the `knowledge_store` package, the portal, and the tests) is shared and
depends on no cloud's SDK. Each cloud's SDK is an extra in `pyproject.toml`.
