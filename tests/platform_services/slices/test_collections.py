"""platform_services.slices.collections: several corpora in one lake."""

import json

import pytest

from knowledge_store.platform_services.adapters.store import LocalStore
from knowledge_store.platform_services.ports import PrefixStore
from knowledge_store.platform_services.slices import collections


@pytest.fixture
def lake(tmp_path):
    return LocalStore(tmp_path)


@pytest.mark.parametrize("cid", ["a", "holmes", "missions-2", "0" * 40])
def test_a_lower_case_id_of_up_to_forty_characters_is_valid(cid):
    assert collections.valid_id(cid) == cid


@pytest.mark.parametrize("cid", ["", None, "Holmes", "-lead", "a_b", "a/b", "0" * 41, "../x"])
def test_any_other_id_is_refused(cid):
    with pytest.raises(ValueError, match="collection id"):
        collections.valid_id(cid)


def test_a_lake_without_config_has_the_default_collection(lake):
    assert collections.ids(lake) == ["default"]


def test_ids_come_from_the_config_in_order(lake):
    lake.put(collections.CONFIG, json.dumps([{"id": "holmes"}, {"id": "missions"}]).encode())
    assert collections.ids(lake) == ["holmes", "missions"]


def test_a_bad_id_in_the_config_is_refused(lake):
    lake.put(collections.CONFIG, json.dumps([{"id": "Bad Id"}]).encode())
    with pytest.raises(ValueError):
        collections.ids(lake)


def test_scoped_writes_under_the_collections_prefix(lake):
    s = collections.scoped(lake, "holmes")
    s.put("silver/x.json", b"{}")
    assert lake.exists("collections/holmes/silver/x.json")


def test_scoped_refuses_a_bad_id(lake):
    with pytest.raises(ValueError):
        collections.scoped(lake, "../escape")


def test_collection_id_reads_a_scoped_store(lake):
    assert collections.collection_id(collections.scoped(lake, "holmes")) == "holmes"


def test_collection_id_is_none_for_a_bare_store_or_another_prefix(lake):
    assert collections.collection_id(lake) is None
    assert collections.collection_id(PrefixStore(lake, "other/x")) is None
