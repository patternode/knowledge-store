"""The structure ADR-046 sets, checked on every test run.

import-linter holds the layers inside each context and the contracts between them (its
configuration is in pyproject.toml). The checks below hold what it cannot express: where the
environment is read, which standard-library network clients a domain may use, that the contexts
depend on each other without a cycle, and that every name a contract publishes resolves.
"""

from __future__ import annotations

import ast
import importlib
import re
from pathlib import Path

import pytest

PKG = Path(__file__).resolve().parents[1] / "src" / "knowledge_store"
CONTEXTS = ["ingestion", "ontology", "extraction", "knowledge_graph", "answering", "access", "evaluation",
            "platform_services"]


def modules(under: Path):
    for p in sorted(under.rglob("*.py")):
        if "__pycache__" not in p.parts:
            yield p, ast.parse(p.read_text(encoding="utf-8"))


def imported(tree) -> set[str]:
    out = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.ImportFrom) and n.module and not n.level:
            out.add(n.module)
        elif isinstance(n, ast.Import):
            out.update(a.name for a in n.names)
    return out


def test_import_contracts_hold(monkeypatch, capsys):
    cli = pytest.importorskip("importlinter.cli", reason="import-linter is in the dev extra")
    monkeypatch.chdir(PKG.parents[1])
    code = cli.lint_imports(no_cache=True)
    assert code == 0, capsys.readouterr().out[-4000:]


def test_the_environment_is_read_only_in_adapters_composition_roots_and_settings():
    allowed = re.compile(r"^(apps/|kernel/settings\.py$|[a-z_]+/adapters/)")
    found = []
    for p, tree in modules(PKG):
        rel = p.relative_to(PKG).as_posix()
        if allowed.match(rel):
            continue
        for n in ast.walk(tree):
            if isinstance(n, ast.Attribute) and n.attr in ("environ", "getenv") and getattr(n.value, "id", "") == "os":
                found.append(f"{rel}:{n.lineno}")
    assert not found, f"read configuration in a composition root or adapter, or through kernel.settings: {found}"


def test_domains_use_no_network_client():
    banned = {"urllib.request", "http.client", "socket", "ssl"}
    found = [f"{p.relative_to(PKG)}: {sorted(imported(t) & banned)}" for c in CONTEXTS if (PKG / c / "domain").exists()
             for p, t in modules(PKG / c / "domain") if imported(t) & banned]
    assert not found, found


def context_graph() -> dict[str, set[str]]:
    deps = {c: set() for c in CONTEXTS}
    for c in CONTEXTS:
        for _, tree in modules(PKG / c):
            for m in imported(tree):
                parts = m.split(".")
                if len(parts) > 1 and parts[0] == "knowledge_store" and parts[1] in deps and parts[1] != c:
                    deps[c].add(parts[1])
    return deps


def test_contexts_depend_on_each_other_without_a_cycle():
    deps, state, path = context_graph(), {}, []

    def visit(c):
        state[c] = "open"
        path.append(c)
        for d in sorted(deps[c]):
            if state.get(d) == "open":
                raise AssertionError("cycle: " + " -> ".join(path[path.index(d):] + [d]))
            if d not in state:
                visit(d)
        path.pop()
        state[c] = "done"

    for c in CONTEXTS:
        if c not in state:
            visit(c)


@pytest.mark.parametrize("context", CONTEXTS)
def test_every_published_name_resolves(context):
    pkg = importlib.import_module(f"knowledge_store.{context}")
    for name in dir(pkg):
        try:
            getattr(pkg, name)
        except ModuleNotFoundError as e:  # an optional extra (boto3, strands, neo4j) is not installed here
            if (e.name or "").startswith("knowledge_store"):
                raise


LAMBDA_HANDLERS = ["knowledge_store.apps.portal_api", "knowledge_store.knowledge_graph.adapters.gateway",
                   "knowledge_store.access.adapters.gateway_interceptor"]
BLOCKER = """
import importlib.abc, sys
class Block(importlib.abc.MetaPathFinder):
    def find_spec(self, name, path=None, target=None):
        if name.split(".")[0] in {"rdflib", "pyshacl", "yaml", "pypdf", "anthropic", "strands", "pydantic", "mcp"}:
            raise ImportError(f"{name} is not in the Lambda package")
sys.meta_path.insert(0, Block())
import importlib
for m in sys.argv[1:]:
    importlib.import_module(m)
"""


def test_lambda_handlers_import_with_the_standard_library_and_boto3_only():
    """Terraform zips the source for the portal and tool Lambdas with no dependencies; the runtime
    provides boto3. A contract that imported rdflib eagerly would break them."""
    import subprocess
    import sys
    r = subprocess.run([sys.executable, "-c", BLOCKER, *LAMBDA_HANDLERS], capture_output=True, text=True,
                       cwd=PKG.parents[1], env={"PYTHONPATH": str(PKG.parent), "PATH": ""})
    assert r.returncode == 0, r.stderr[-3000:]
