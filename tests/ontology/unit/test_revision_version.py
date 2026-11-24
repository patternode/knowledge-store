"""A revision draft never proposes a version already published."""

from knowledge_store.ontology.slices.candidates import next_minor


def test_the_draft_follows_the_highest_published_version():
    assert next_minor("1.2.0", ["1.0.0", "1.2.0", "1.3.0"]) == "1.4.0"
    assert next_minor("1.2.0", ["1.0.0", "1.2.0"]) == "1.3.0"
