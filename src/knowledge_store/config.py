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
from dataclasses import dataclass, field

from . import layout
from .store import Store


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


DEFAULT_SOURCES = (SourceConfig(name="uploads", type="s3_landing", options={"prefix": layout.LANDING + "/"}),)


def profile_from_dict(d: dict) -> Profile:
    return Profile(
        name=d.get("name") or Profile.name,
        description=d.get("description") or Profile.description,
        key_terms=tuple(d.get("key_terms") or ()),
        example_questions=tuple(d.get("example_questions") or ()),
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
