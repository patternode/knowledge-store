"""kernel.contract: a contract package's names load on first use."""

import types

import pytest

from knowledge_store.kernel.contract import lazy


def test_a_published_name_resolves_to_the_object_in_its_module():
    getattr_, _ = lazy("knowledge_store.kernel", {"safe_name": "identifiers"})
    from knowledge_store.kernel.identifiers import safe_name

    assert getattr_("safe_name") is safe_name


def test_a_name_marked_with_at_resolves_to_the_module_itself():
    getattr_, _ = lazy("knowledge_store.kernel", {"values": "@values"})
    mod = getattr_("values")
    assert isinstance(mod, types.ModuleType)
    assert mod.__name__ == "knowledge_store.kernel.values"


def test_an_unpublished_name_raises_attribute_error_naming_the_package():
    getattr_, _ = lazy("knowledge_store.kernel", {})
    with pytest.raises(AttributeError, match="knowledge_store.kernel"):
        getattr_("anything")


def test_dir_lists_the_published_names_sorted():
    _, dir_ = lazy("pkg", {"b": "m", "a": "m"})
    assert dir_() == ["a", "b"]


def test_a_real_contract_publishes_what_its_dir_lists():
    import knowledge_store.platform_services as ps

    for name in dir(ps):
        assert getattr(ps, name) is not None
