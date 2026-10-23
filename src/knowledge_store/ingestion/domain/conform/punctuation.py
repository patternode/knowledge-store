"""ASCII punctuation, ligatures and exact fractions. Fenced code never reaches here."""

from __future__ import annotations

from decimal import Decimal

from knowledge_store.kernel.values import canonical

_QUOTES = {
    "\u2018": "'", "\u2019": "'", "\u201a": "'", "\u201b": "'",
    "\u201c": '"', "\u201d": '"', "\u201e": '"', "\u201f": '"',
}

_DASHES = {
    "\u2010": "-", "\u2011": "-", "\u2012": "-", "\u2013": "-", "\u2014": "-",
    "\u2015": "-", "\u2212": "-",
}

_LIGATURES = {"\ufb00": "ff", "\ufb01": "fi", "\ufb02": "fl", "\ufb03": "ffi", "\ufb04": "ffl"}

# Terminating decimals only. A third and a sixth do not have one exact decimal.
_FRAC = {
    "½": "0.5", "¼": "0.25", "¾": "0.75",
    "⅕": "0.2", "⅖": "0.4", "⅗": "0.6", "⅘": "0.8",
    "⅛": "0.125", "⅜": "0.375", "⅝": "0.625", "⅞": "0.875",
}

def _punctuation(text: str) -> tuple[str, list]:
    """ASCII quotes, dashes, ellipsis and ligatures, and an exact fraction."""
    notes = []
    out: list[str] = []
    i, n = 0, len(text)
    while i < n:
        ch = text[i]
        if ch in _QUOTES or ch in _DASHES:
            repl = _QUOTES[ch] if ch in _QUOTES else _DASHES[ch]
            notes.append((0, 0, ch, repl, "punctuation"))
            out.append(repl)
            i += 1
            continue
        if ch == "\u2026":
            notes.append((0, 0, ch, "...", "punctuation"))
            out.append("...")
            i += 1
            continue
        if ch in _LIGATURES:
            repl = _LIGATURES[ch]
            notes.append((0, 0, ch, repl, "punctuation"))
            out.append(repl)
            i += 1
            continue
        if ch in _FRAC:
            j = i
            while j > 0 and text[j - 1].isdigit():
                j -= 1
            if j < i:
                del out[-(i - j):]
            whole = text[j:i] or "0"
            new = canonical(Decimal(whole) + Decimal(_FRAC[ch]), "decimal")
            old = text[j:i + 1]
            if new and new != old:
                notes.append((0, 0, old, new, "number"))
                out.append(new)
            else:
                out.append(old)
            i += 1
            continue
        out.append(ch)
        i += 1
    return "".join(out), notes
