"""Build the Function App's zip: functions/azure, the knowledge_store package, and its
dependencies as Linux wheels under .python_packages (what Flex Consumption runs without a
remote build). Works from Windows, macOS or Linux, because pip is told the target platform.

Terraform runs it as an external data source: it reads {"repo_root", "out_dir"} on stdin and
prints {"path", "sha256"}. The zip is named by a hash of everything that goes into it, so an
unchanged source is not rebuilt and an apply redeploys only when something changed.

    python infra/azure/package_function.py < <(echo '{"repo_root": ".", "out_dir": "build"}')
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

SKIP = {"__pycache__", ".pytest_cache"}
PLATFORM = ["--platform", "manylinux2014_x86_64", "--platform", "manylinux_2_28_x86_64",
            "--python-version", "3.12", "--implementation", "cp", "--only-binary=:all:"]


def files(root: Path, rel_to: Path):
    for p in sorted(root.rglob("*")):
        if p.is_file() and not SKIP & set(p.parts) and p.suffix != ".pyc":
            yield p, p.relative_to(rel_to).as_posix()


def main() -> None:
    q = json.load(sys.stdin)
    repo = Path(q["repo_root"]).resolve()
    out = Path(q["out_dir"]).resolve()
    app, pkg = repo / "functions" / "azure", repo / "src" / "knowledge_store"
    sources = [*files(app, app), *((p, "knowledge_store/" + r) for p, r in files(pkg, pkg))]
    h = hashlib.sha256()
    for p, arc in sources:
        h.update(arc.encode())
        h.update(p.read_bytes())
    digest = h.hexdigest()[:16]
    zpath = out / f"function-{digest}.zip"
    if not zpath.exists():
        out.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory() as tmp:
            site = Path(tmp) / ".python_packages" / "lib" / "site-packages"
            subprocess.run([sys.executable, "-m", "pip", "install", "--quiet", "--disable-pip-version-check",
                            "--target", str(site), *PLATFORM, "-r", str(app / "requirements.txt")],
                           check=True, stdout=sys.stderr)
            part = zpath.with_suffix(".part")
            with zipfile.ZipFile(part, "w", zipfile.ZIP_DEFLATED) as z:
                for p, arc in sources:
                    z.write(p, arc)
                for p, arc in files(site, Path(tmp)):
                    z.write(p, arc)
            part.replace(zpath)
    print(json.dumps({"path": str(zpath), "sha256": hashlib.sha256(zpath.read_bytes()).hexdigest()}))


if __name__ == "__main__":
    main()
