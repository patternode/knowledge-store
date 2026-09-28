"""Fail if the tree about to be published holds anything that identifies a private deployment.

    PREPUBLISH_TERMS="term one,term two" python scripts/prepublish_check.py [root]

Checks every file git would publish (tracked or not ignored) for:

    AWS account ids      12-digit numbers, except the documentation placeholder 123456789012
    email addresses      except example.org / example.com addresses
    credentials          AWS access keys, Anthropic and GitHub tokens, private keys
    local paths          Windows drive paths and home directories
    private terms        whatever PREPUBLISH_TERMS lists (comma-separated, case-insensitive)

The private terms are passed in, never written here, so the published repository does not carry
the list of what it must not contain. Exit status 1 on any finding.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

CHECKS = {
    "account id": re.compile(r"(?<![0-9a-f])(?!123456789012)\d{12}(?![0-9])"),
    "email": re.compile(r"[A-Za-z0-9._%+-]+@(?!example\.(?:org|com)\b)[A-Za-z0-9.-]+\.[A-Za-z]{2,}"),
    "credential": re.compile(r"AKIA[0-9A-Z]{16}|sk-ant-[A-Za-z0-9_-]{10,}|gh[pousr]_[A-Za-z0-9]{20,}|-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    "local path": re.compile(r"\b[A-Z]:\\\\?[A-Za-z]|/Users/[a-z]|/home/[a-z]"),
}
SKIP_SUFFIXES = (".lock.hcl",)          # provider hashes look like ids
SKIP_NAMES = ("LICENSE",)


def files(root: Path) -> list[Path]:
    out = subprocess.run(["git", "ls-files", "--cached", "--others", "--exclude-standard", "."],
                         cwd=root, capture_output=True, text=True, check=True).stdout.split("\n")
    return [root / f for f in out if f and (root / f).is_file()]


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
    terms = [t.strip().lower() for t in os.environ.get("PREPUBLISH_TERMS", "").split(",") if t.strip()]
    if not terms:
        print("note: PREPUBLISH_TERMS is empty, so only the generic checks run", file=sys.stderr)
    findings = []
    for f in files(root):
        rel = f.relative_to(root).as_posix()
        if rel.endswith(SKIP_SUFFIXES) or f.name in SKIP_NAMES:
            continue
        try:
            text = f.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for n, line in enumerate(text.splitlines(), 1):
            for kind, rx in CHECKS.items():
                if rx.search(line):
                    findings.append((rel, n, kind, line.strip()[:100]))
            low = line.lower()
            for t in terms:
                if t in low:
                    findings.append((rel, n, "private term", "(term withheld)"))
    for rel, n, kind, text in findings:
        print(f"{rel}:{n}: {kind}: {text}")
    print(f"{len(findings)} finding(s) in {root}")
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
