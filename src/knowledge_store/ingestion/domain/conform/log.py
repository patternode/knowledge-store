"""Rule log and span claims shared by the literal modules."""

from __future__ import annotations

from collections import Counter

_EXAMPLES = 3

def _record(found, counts: Counter, examples: dict[str, list]) -> None:
    for _, _, old, new, rule in found:
        shown = f"{old} -> {new}"
        _note(counts, examples, rule, shown)

def _note(counts: Counter, examples: dict[str, list], rule: str, example: str) -> None:
    counts[rule] += 1
    examples.setdefault(rule, [])
    if len(examples[rule]) < _EXAMPLES and example not in examples[rule]:
        examples[rule].append(example)

def _overlaps(start: int, end: int, found: list[tuple[int, int, str, str, str]]) -> bool:
    return any(start < have_end and end > have_start for have_start, have_end, *_ in found)

def _keep(found: list, start: int, end: int, old: str, new: str, rule: str = "date") -> None:
    if new and new != old and not _overlaps(start, end, found):
        if "/" in new:
            rule = "period"
        found.append((start, end, old, new, rule))


def _assemble(text: str, found: list) -> tuple[str, list]:
    """Apply non-overlapping claims. A hold, where the text is unchanged, is not logged."""
    found.sort(key=lambda item: (item[0], -(item[1] - item[0])))
    parts: list[str] = []
    kept = []
    at = 0
    for start, end, old, new, rule in found:
        if start < at:
            continue
        parts.append(text[at:start])
        parts.append(new)
        at = end
        if new != old:
            kept.append((start, end, old, new, rule))
    parts.append(text[at:])
    return "".join(parts), kept
