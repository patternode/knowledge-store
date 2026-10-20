"""Test levels come from folders (docs/engineering-standard.md, section 7).

tests/<context>/unit, tests/<context>/slices and tests/<context>/contracts hold one context's
unit, slice and port contract tests; tests/contracts holds context contracts; tests/apps the
deployables; tests/test_architecture.py the boundaries. Each test gets its level's marker, so
`pytest -m unit` runs one level, and its context's marker (`ctx_<context>`).
"""

import sys
from pathlib import Path

import pytest

HERE = Path(__file__).parent

# Shared fixtures and helpers live in test modules other tests import by name (fake_llm,
# test_lifecycle, test_review_fixes): every test folder is importable.
for folder in sorted({p.parent for p in HERE.rglob("test_*.py")} | {HERE}):
    if str(folder) not in sys.path:
        sys.path.insert(0, str(folder))

LEVELS = {"unit": "unit", "slices": "slice", "contracts": "contract"}


def level_of(path: Path) -> tuple[str, str | None]:
    parts = path.relative_to(HERE).parts
    if parts[0] == "test_architecture.py":
        return "architecture", None
    if parts[0] == "apps":
        return "deployable", None
    if parts[0] == "contracts":
        return "contract", None
    if len(parts) >= 3 and parts[1] in LEVELS:
        return LEVELS[parts[1]], parts[0]
    raise pytest.UsageError(f"{path}: a test belongs in tests/<context>/(unit|slices|contracts), tests/contracts or tests/apps")


def pytest_collection_modifyitems(config, items):
    for item in items:
        level, context = level_of(Path(str(item.path)))
        item.add_marker(getattr(pytest.mark, level))
        if context:
            item.add_marker(getattr(pytest.mark, f"ctx_{context}"))
