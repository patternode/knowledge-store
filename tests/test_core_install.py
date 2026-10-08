"""The core runs without any cloud's SDK. Each SDK is an extra (aws, and the backends'), so
every module must import with none of them installed, and import a cloud SDK only inside the
code that uses it. CI also runs the whole suite on an install with no extras."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src"

CLOUD_SDKS = ("boto3", "botocore", "pymongo", "neo4j", "psycopg", "jwt")

PROBE = f"""
import importlib, pkgutil, sys
class Block:
    def find_spec(self, name, path=None, target=None):
        if name.split(".")[0] in {CLOUD_SDKS!r}:
            raise ImportError("blocked " + name)
sys.meta_path.insert(0, Block())
import knowledge_store
failed = []
for m in pkgutil.walk_packages(knowledge_store.__path__, "knowledge_store."):
    try:
        importlib.import_module(m.name)
    except ImportError as e:
        failed.append(m.name + ": " + str(e))
print("\\n".join(failed))
"""


def test_every_module_imports_without_a_cloud_sdk():
    env = {**os.environ, "PYTHONPATH": str(SRC)}
    r = subprocess.run([sys.executable, "-c", PROBE], capture_output=True, text=True, env=env)
    assert r.returncode == 0, r.stderr
    assert r.stdout.strip() == ""
