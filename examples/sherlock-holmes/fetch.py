"""Fetch the Sherlock Holmes short stories from Project Gutenberg and split them into one file
per story, ready to upload to landing/.

    python examples/sherlock-holmes/fetch.py [out_dir]     # default: examples/sherlock-holmes/stories

The three collections (The Adventures, The Memoirs, The Return) are in the public domain. The
Project Gutenberg header and footer are removed, as Project Gutenberg's licence asks when the
plain text is redistributed without its trademark: what remains is the public-domain text alone.
The files are fetched once, three requests two seconds apart, with a User-Agent that says what
this is; nothing is crawled.
"""

from __future__ import annotations

import re
import sys
import time
import urllib.request
from pathlib import Path

BOOKS = {
    "the-adventures-of-sherlock-holmes": (1661, [
        "A Scandal in Bohemia", "The Red-Headed League", "A Case of Identity", "The Boscombe Valley Mystery",
        "The Five Orange Pips", "The Man with the Twisted Lip", "The Adventure of the Blue Carbuncle",
        "The Adventure of the Speckled Band", "The Adventure of the Engineer's Thumb",
        "The Adventure of the Noble Bachelor", "The Adventure of the Beryl Coronet",
        "The Adventure of the Copper Beeches"]),
    "the-memoirs-of-sherlock-holmes": (834, [
        "Silver Blaze", "The Adventure of the Cardboard Box", "The Yellow Face", "The Stockbroker's Clerk",
        "The Gloria Scott",
        "The Musgrave Ritual", "The Reigate Squires", "The Crooked Man", "The Resident Patient",
        "The Greek Interpreter", "The Naval Treaty", "The Final Problem"]),
    "the-return-of-sherlock-holmes": (108, [
        "The Adventure of the Empty House", "The Adventure of the Norwood Builder",
        "The Adventure of the Dancing Men", "The Adventure of the Solitary Cyclist",
        "The Adventure of the Priory School", "The Adventure of Black Peter",
        "The Adventure of Charles Augustus Milverton", "The Adventure of the Six Napoleons",
        "The Adventure of the Three Students", "The Adventure of the Golden Pince-Nez",
        "The Adventure of the Missing Three-Quarter", "The Adventure of the Abbey Grange",
        "The Adventure of the Second Stain"]),
}
UA = "knowledge-store-demo/0.1 (one-off fetch of three public-domain books for a demo corpus)"


def strip_gutenberg(text: str) -> str:
    start = re.search(r"\*\*\* ?START OF (THE|THIS) PROJECT GUTENBERG EBOOK[^\n]*\n", text, re.I)
    end = re.search(r"\*\*\* ?END OF (THE|THIS) PROJECT GUTENBERG EBOOK", text, re.I)
    return text[start.end() if start else 0:end.start() if end else len(text)].strip()


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", s.lower().replace("’", "").replace("'", "")).strip()


def split_stories(body: str, titles: list[str]) -> list[tuple[str, str]]:
    """Each story starts at the last line in the book that is its title alone (the first
    occurrences are the table of contents), optionally numbered ("I. A SCANDAL IN BOHEMIA")."""
    lines = body.splitlines()
    starts = []
    for title in titles:
        want = _norm(title)
        hits = [i for i, line in enumerate(lines)
                if _norm(re.sub(r"^\s*(?:[IVXLC]+\.|\d+\.|ADVENTURE [IVXLC]+\.)\s*", "", line)) == want]
        if not hits:
            raise ValueError(f"cannot find the start of {title!r}")
        starts.append((hits[-1], title))
    starts.sort()
    out = []
    for n, (i, title) in enumerate(starts):
        j = starts[n + 1][0] if n + 1 < len(starts) else len(lines)
        text = "\n".join(lines[i + 1:j]).strip()
        out.append((title, text))
    return out


def slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", _norm(s)).strip("-")


def main() -> None:
    out = Path(sys.argv[1] if len(sys.argv) > 1 else Path(__file__).parent / "stories")
    for i, (book, (gid, titles)) in enumerate(BOOKS.items()):
        if i:
            time.sleep(2)
        url = f"https://www.gutenberg.org/cache/epub/{gid}/pg{gid}.txt"
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=60) as r:
            raw = r.read().decode("utf-8-sig").replace("\r\n", "\n")
        stories = split_stories(strip_gutenberg(raw), titles)
        for n, (title, text) in enumerate(stories, 1):
            p = out / book / f"{n:02d}-{slug(title)}.txt"
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(f"{title}\n\nFrom {book.replace('-', ' ').title()}, by Arthur Conan Doyle.\n\n{text}\n",
                         encoding="utf-8")
            print(f"{p}  {len(text):>7} chars")


if __name__ == "__main__":
    main()
