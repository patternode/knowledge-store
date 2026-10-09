"""Deployment configuration: the sources to ingest and the domain profile.

Both live in the lake (config/sources.json, config/profile.json), written by Terraform
from the deployer's variables, so a deployment is configured in one place (tfvars) and
every job and the portal read the same thing. Locally, pass files or let the defaults apply.

The profile is not the ontology. It tells the portal and the prompts what the collection
is about (a name, a paragraph, a handful of key terms and example questions) before any
ontology exists, and it never types a fact. The ontology is discovered or authored
separately and versioned (ontology/).
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

from . import layout
from .store import Store

LEVELS = ("low", "medium", "high")
_MARK = re.compile(r"^\[(low|medium|high)\]\s*", re.IGNORECASE)


@dataclass(frozen=True)
class SourceConfig:
    """One configured source: a name (the bronze partition), an adapter type and its options."""
    name: str
    type: str
    options: dict = field(default_factory=dict)
    scope: str = "public"   # public or private: private content is served only to private-scope users


@dataclass(frozen=True)
class Profile:
    name: str = "Knowledge Store"
    description: str = "A collection of documents, organised by an ontology discovered from them."
    key_terms: tuple[str, ...] = ()
    example_questions: tuple[str, ...] = ()
    # Parallel to example_questions. "" means the profile did not name a level; sample_questions()
    # then spreads the list across low, medium and high.
    question_levels: tuple[str, ...] = ()
    ontology_base: str = "https://example.org/ontology/lab#"
    language: str = "en"

    def prompt_context(self) -> str:
        """The profile as a short block for a model prompt."""
        parts = [f"Collection: {self.name}", self.description]
        if self.key_terms:
            parts.append("Key terms in this domain: " + ", ".join(self.key_terms))
        return "\n".join(parts)

    def to_dict(self) -> dict:
        return {"name": self.name, "description": self.description, "key_terms": list(self.key_terms),
                "example_questions": list(self.example_questions), "ontology_base": self.ontology_base,
                "language": self.language}

    def sample_questions(self) -> list[dict]:
        """[{text, level}] for the chat's sample rail. A level the profile names is kept. When none
        are named, the list is spread across low, medium and high in the order given."""
        levels = self.question_levels + ("",) * len(self.example_questions)
        return assign_levels(list(zip(self.example_questions, levels)))


DEFAULT_SOURCES = (SourceConfig(name="uploads", type="s3_landing", options={"prefix": layout.LANDING + "/"}),)


def parse_example_questions(raw) -> tuple[tuple[str, str], ...]:
    """(text, level) from a profile list. A string may start with [low], [medium] or [high], which
    sets the level and is not part of the question, so a deployer can label questions without
    changing the Terraform type (a list of strings). An object is {"text", "level"}."""
    out = []
    for item in raw or []:
        if isinstance(item, str):
            text = item.strip()
            mark = _MARK.match(text)
            level = mark.group(1).lower() if mark else ""
            if mark:
                text = text[mark.end():].strip()
        elif isinstance(item, dict):
            text = str(item.get("text") or item.get("question") or "").strip()
            level = str(item.get("level") or "").strip().lower()
            level = level if level in LEVELS else ""
        else:
            continue
        if text:
            out.append((text, level))
    return tuple(out)


def assign_levels(pairs) -> list[dict]:
    """[{text, level}]. Named levels stay. When none are named, the first third is low, the last
    third is high and the middle is medium, with at least one of each once there are three."""
    rows = [{"text": text, "level": level if level in LEVELS else ""} for text, level in pairs if text]
    if not rows or any(r["level"] for r in rows):
        for r in rows:
            if not r["level"]:
                r["level"] = "medium"
        return rows
    n = len(rows)
    if n == 1:
        rows[0]["level"] = "low"
        return rows
    if n == 2:
        rows[0]["level"] = "low"
        rows[1]["level"] = "high"
        return rows
    low_n = max(1, n // 3)
    high_n = max(1, n // 3)
    if low_n + high_n >= n:
        low_n, high_n = 1, 1
    for i, r in enumerate(rows):
        if i < low_n:
            r["level"] = "low"
        elif i >= n - high_n:
            r["level"] = "high"
        else:
            r["level"] = "medium"
    return rows


def profile_from_dict(d: dict) -> Profile:
    questions = parse_example_questions(d.get("example_questions"))
    return Profile(
        name=d.get("name") or Profile.name,
        description=d.get("description") or Profile.description,
        key_terms=tuple(d.get("key_terms") or ()),
        example_questions=tuple(text for text, _ in questions),
        question_levels=tuple(level for _, level in questions),
        ontology_base=d.get("ontology_base") or Profile.ontology_base,
        language=d.get("language") or "en",
    )


def sources_from_list(rows: list[dict]) -> tuple[SourceConfig, ...]:
    out = []
    names = set()
    for r in rows:
        name = r["name"]
        if not name.replace("-", "").replace("_", "").isalnum():
            raise ValueError(f"source name {name!r} must be letters, digits, - or _ (it is an S3 prefix)")
        if name in names:
            raise ValueError(f"source {name!r} is configured twice")
        names.add(name)
        scope = r.get("scope", "public")
        if scope not in ("public", "private"):
            raise ValueError(f"source {name!r}: scope must be public or private, not {scope!r}")
        out.append(SourceConfig(name=name, type=r["type"], options=dict(r.get("options") or {}), scope=scope))
    return tuple(out)


def load_profile(store: Store) -> Profile:
    if store.exists(layout.CONFIG_PROFILE):
        return profile_from_dict(json.loads(store.get(layout.CONFIG_PROFILE)))
    return Profile()


def load_sources(store: Store) -> tuple[SourceConfig, ...]:
    """A collection's sources. Without a config, a collection takes what is uploaded under
    landing/<collection id>/ (and a bare store everything under landing/)."""
    if store.exists(layout.CONFIG_SOURCES):
        return sources_from_list(json.loads(store.get(layout.CONFIG_SOURCES)))
    from .collections import collection_id
    cid = collection_id(store)
    if cid:
        return (SourceConfig(name="uploads", type="s3_landing", options={"prefix": f"{layout.LANDING}/{cid}/"}),)
    return DEFAULT_SOURCES
