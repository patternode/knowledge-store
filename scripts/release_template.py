"""Fill a release's launch template with its zip's URL and sha256.

python scripts/release_template.py <template> <url> <sha256>

Rewrites the Default of SourceUrl and SourceSha256 in place, so the template attached to a GitHub
release deploys exactly the zip attached beside it, and refuses any other.
"""

from __future__ import annotations

import re
import sys


def fill(text: str, url: str, sha: str) -> str:
    if not re.fullmatch(r"[0-9a-f]{64}", sha):
        raise ValueError("sha256 must be 64 hexadecimal digits")
    out, n1 = re.subn(r"(\n  SourceUrl:\n    Type: String\n    Default: )\S+[^\n]*", lambda m: m.group(1) + url, text, count=1)
    out, n2 = re.subn(r'(\n  SourceSha256:\n    Type: String\n    Default: )""', lambda m: m.group(1) + f'"{sha}"', out, count=1)
    if n1 != 1 or n2 != 1:
        raise ValueError("the template's SourceUrl or SourceSha256 default was not found")
    return out


if __name__ == "__main__":
    path, url, sha = sys.argv[1:4]
    with open(path, encoding="utf-8") as f:
        text = f.read()
    with open(path, "w", encoding="utf-8") as f:
        f.write(fill(text, url, sha))
