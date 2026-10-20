"""platform_services.slices.config: the sources and the domain profile a deployment sets."""

import json

import pytest

from knowledge_store.platform_services.adapters.store import LocalStore
from knowledge_store.platform_services.domain import layout
from knowledge_store.platform_services.slices import collections, config
from knowledge_store.platform_services.slices.config import Profile, SourceConfig


@pytest.fixture
def lake(tmp_path):
    return LocalStore(tmp_path)


# --- the profile -------------------------------------------------------------------------


def test_a_lake_without_a_profile_has_the_default(lake):
    assert config.load_profile(lake) == Profile()


def test_the_profile_is_read_from_the_lake(lake):
    lake.put(layout.CONFIG_PROFILE, json.dumps({"name": "Holmes", "key_terms": ["case"], "language": "fr"}).encode())
    p = config.load_profile(lake)
    assert (p.name, p.key_terms, p.language) == ("Holmes", ("case",), "fr")
    assert p.description == Profile.description


def test_prompt_context_names_the_collection_and_its_key_terms():
    p = Profile(name="Holmes", description="Stories.", key_terms=("case", "client"))
    assert p.prompt_context() == "Collection: Holmes\nStories.\nKey terms in this domain: case, client"


def test_prompt_context_leaves_out_key_terms_when_there_are_none():
    assert "Key terms" not in Profile().prompt_context()


def test_to_dict_round_trips_through_profile_from_dict():
    p = config.profile_from_dict({"name": "N", "description": "D", "key_terms": ["k"], "example_questions": ["q?"], "ontology_base": "https://x/#", "language": "de"})
    assert config.profile_from_dict(p.to_dict()) == config.profile_from_dict({**p.to_dict()})
    assert p.to_dict()["example_questions"] == ["q?"]


def test_an_empty_dict_gives_the_default_profile():
    assert config.profile_from_dict({}) == Profile()


# --- example questions ---------------------------------------------------------------------


def test_a_level_mark_sets_the_level_and_is_not_part_of_the_question():
    assert config.parse_example_questions(["[HIGH] Who did it?"]) == (("Who did it?", "high", "", ""),)


def test_a_trailing_https_link_is_taken_off_the_question():
    q = config.parse_example_questions(["What sold? [Sales](https://example.org/s)"])
    assert q == (("What sold?", "", "https://example.org/s", "Sales"),)


def test_a_trailing_table_link_is_taken_off_the_question():
    q = config.parse_example_questions(["Totals? [t](tables/sales-2024.csv)"])
    assert q == (("Totals?", "", "tables/sales-2024.csv", "t"),)


def test_a_link_with_another_scheme_stays_in_the_question():
    q = config.parse_example_questions(["Bad [x](javascript:alert(1))"])
    assert q[0][2] == "" and "javascript" in q[0][0]


def test_an_object_question_takes_its_text_level_and_link():
    q = config.parse_example_questions([{"text": "Q?", "level": "Low", "link": "tables/a.csv"}])
    assert q == (("Q?", "low", "tables/a.csv", "a.csv"),)


def test_an_object_question_may_say_question_instead_of_text():
    assert config.parse_example_questions([{"question": "Q?"}])[0][0] == "Q?"


def test_an_object_with_an_unknown_level_has_none():
    assert config.parse_example_questions([{"text": "Q?", "level": "extreme"}])[0][1] == ""


def test_an_object_link_that_is_not_allowed_is_dropped_with_its_label():
    q = config.parse_example_questions([{"text": "Q?", "link": "http://insecure.example", "link_label": "x"}])
    assert q[0][2:] == ("", "")


def test_an_object_takes_a_link_written_in_its_text():
    q = config.parse_example_questions([{"text": "Q? [L](https://e.org/x)"}])
    assert q == (("Q?", "", "https://e.org/x", "L"),)


def test_items_that_are_neither_text_nor_objects_or_are_empty_are_skipped():
    assert config.parse_example_questions([3, None, "  ", {"text": ""}, "ok"]) == (("ok", "", "", ""),)


def test_no_questions_is_an_empty_tuple():
    assert config.parse_example_questions(None) == ()


# --- levels ----------------------------------------------------------------------------------


def _levels(n):
    return [r["level"] for r in config.assign_levels([(f"q{i}", "") for i in range(n)])]


def test_one_unlabelled_question_is_low():
    assert _levels(1) == ["low"]


def test_two_unlabelled_questions_are_low_then_high():
    assert _levels(2) == ["low", "high"]


def test_three_unlabelled_questions_get_one_of_each():
    assert _levels(3) == ["low", "medium", "high"]


def test_six_unlabelled_questions_are_spread_in_thirds():
    assert _levels(6) == ["low", "low", "medium", "medium", "high", "high"]


def test_when_any_level_is_named_the_unnamed_are_medium():
    rows = config.assign_levels([("a", "high"), ("b", ""), ("c", "bogus")])
    assert [r["level"] for r in rows] == ["high", "medium", "medium"]


def test_empty_texts_are_dropped():
    assert config.assign_levels([("", "low")]) == []


def test_a_link_gets_a_label_from_its_file_name_when_none_is_given():
    rows = config.assign_levels([("q", "low", "tables/a.csv", "")])
    assert rows[0]["link"] == "tables/a.csv" and rows[0]["link_label"] == "a.csv"


def test_sample_questions_carry_levels_and_links_from_the_profile():
    p = config.profile_from_dict({"example_questions": ["[low] A?", "B? [t](tables/b.csv)"]})
    assert p.sample_questions() == [{"text": "A?", "level": "low"}, {"text": "B?", "level": "medium", "link": "tables/b.csv", "link_label": "t"}]


# --- sources ---------------------------------------------------------------------------------


def test_a_bare_lake_without_config_takes_everything_uploaded_under_landing(lake):
    assert config.load_sources(lake) == config.DEFAULT_SOURCES
    assert config.DEFAULT_SOURCES[0].options == {"prefix": "landing/"}


def test_a_collection_without_config_takes_its_own_landing_folder(lake):
    (src,) = config.load_sources(collections.scoped(lake, "holmes"))
    assert src == SourceConfig(name="uploads", type="s3_landing", options={"prefix": "landing/holmes/"})


def test_sources_are_read_from_the_lake(lake):
    lake.put(layout.CONFIG_SOURCES, json.dumps([{"name": "web", "type": "http_urls", "options": {"urls": ["https://e.org"]}, "scope": "private"}]).encode())
    (src,) = config.load_sources(lake)
    assert (src.name, src.type, src.scope, src.options["urls"]) == ("web", "http_urls", "private", ["https://e.org"])


def test_a_source_is_public_unless_it_says_otherwise():
    assert config.sources_from_list([{"name": "a", "type": "t"}])[0].scope == "public"


@pytest.mark.parametrize("name", ["a/b", "a b", "a.b", ""])
def test_a_source_name_that_cannot_be_a_prefix_is_refused(name):
    with pytest.raises(ValueError, match="letters, digits"):
        config.sources_from_list([{"name": name, "type": "t"}])


def test_a_source_configured_twice_is_refused():
    with pytest.raises(ValueError, match="twice"):
        config.sources_from_list([{"name": "a", "type": "t"}, {"name": "a", "type": "u"}])


def test_a_scope_other_than_public_or_private_is_refused():
    with pytest.raises(ValueError, match="scope"):
        config.sources_from_list([{"name": "a", "type": "t", "scope": "secret"}])
