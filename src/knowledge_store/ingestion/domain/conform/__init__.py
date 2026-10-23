"""Canonical text, before any ontology is involved.

Refine runs this on the parsed text. The bronze bytes stay as they were. The silver
document and its passages are this form, so a date, a time, a time period and a number
are written one way whatever the file called them. The reading of a number and of a
written date is kernel.values, the same reading a table cell uses.

A time period is an ISO 8601 interval (2023-07-14/2023-07-20, 09:00/17:00) or a
duration (PT2H, P3D, P14D/P30D). A month written with its year is that month (2023-07).
Milliseconds are decimal seconds, which is the ISO duration form.

Only forms that are unambiguous are rewritten. A numeric date that could be day-first or
month-first is left as written. A clock without am/pm, a zone, or an hour of 13 or more
(or 00) is left as written, unless it sits against a date or in a range where the other
end fixes the reading. A bare year is not a date. A quarter, a fiscal year and a half
stay as written, because the calendar they use is not fixed. A business day is not a
fixed length. Words such as yes and no are not booleans. A hyphenated range of numbers
is rewritten on each side. Thousands separators are commas and the dedicated group
spaces. Parentheses mark a loss only when the amount has a currency sign or a grouping
separator. Quotes, dashes, ellipsis and ligatures fold to ASCII. A link's scheme
and host, an email's domain and a UUID are written in one case. An exact fraction
and a scientific number use the same decimal form as any other number. An
information size is a number and a symbol (8 MB, 10 MiB, 256 B). The B is
uppercase, or the word is byte. A lowercase b stays, so a bit form stays. A bare
B on its own stays, because it also means a billion. A hyphenated tag stays.
Decimal and binary prefixes are not converted into each other. Fenced code
is left as written. Nothing here is a class, a synonym or a unit from a domain.

Each literal family is its own module. This module only runs them, in one order,
and keeps fenced code out of every one of them.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from knowledge_store.ingestion.domain.conform.clocks import _claim_clocks
from knowledge_store.ingestion.domain.conform.dates import _claim_dates
from knowledge_store.ingestion.domain.conform.fold import _fold, _group_spaces
from knowledge_store.ingestion.domain.conform.identifiers import _identifiers
from knowledge_store.ingestion.domain.conform.log import _assemble, _record
from knowledge_store.ingestion.domain.conform.numbers import _claim_numbers, _scientific
from knowledge_store.ingestion.domain.conform.periods import _durations
from knowledge_store.ingestion.domain.conform.punctuation import _punctuation
from knowledge_store.ingestion.domain.conform.sizes import _sizes

CONFORMER_VERSION = "conform@1"

# The order is the behaviour. A later rule sees the spans an earlier rule has claimed.
RULES = (
    "punctuation",
    "identifiers",
    "scientific",
    "periods",
    "dates",
    "clocks",
    "sizes",
    "numbers",
)

_FENCE = re.compile(r"```.*?```", re.DOTALL)


@dataclass(frozen=True)
class ConformResult:
    text: str
    rules: tuple[dict, ...]


def conform(text: str) -> ConformResult:
    """The canonical text, and one row per rule that changed something."""
    folded, counts, examples = _fold(text)
    pieces: list[str] = []
    pos = 0
    for fence in _FENCE.finditer(folded):
        if fence.start() > pos:
            piece, found = _literals(folded[pos:fence.start()])
            pieces.append(piece)
            _record(found, counts, examples)
        pieces.append(fence.group())
        pos = fence.end()
    if pos < len(folded):
        piece, found = _literals(folded[pos:])
        pieces.append(piece)
        _record(found, counts, examples)
    joined = _group_spaces("".join(pieces), counts, examples)
    rules = tuple({"rule": name, "applied": counts[name], "examples": examples[name]}
                  for name in sorted(counts) if counts[name])
    return ConformResult(joined, rules)


def _literals(text: str) -> tuple[str, list]:
    text, notes = _punctuation(text)
    found: list = []
    _identifiers(text, found)
    _scientific(text, found)
    _durations(text, found)
    _claim_dates(text, found)
    _claim_clocks(text, found)
    _sizes(text, found)
    _claim_numbers(text, found)
    body, kept = _assemble(text, found)
    return body, notes + kept
