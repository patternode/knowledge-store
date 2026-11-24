"""The local store refuses a key that would leave its root."""

import pytest

from knowledge_store.platform_services.adapters.store import LocalStore


@pytest.mark.parametrize("key", ["../outside", "a/../../outside", "/etc/passwd", "a\\..\\..\\x"])
def test_a_key_outside_the_root_is_refused(tmp_path, key):
    store = LocalStore(tmp_path / "lake")
    with pytest.raises(ValueError):
        store.get(key)


def test_keys_inside_the_root_still_work(tmp_path):
    store = LocalStore(tmp_path / "lake")
    store.put("silver/doc-1.json", b"{}")
    assert store.get("silver/doc-1.json") == b"{}" and store.exists("silver/doc-1.json")
