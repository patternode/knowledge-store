"""kernel.settings: the one place tunable settings are read from the environment."""

from knowledge_store.kernel import settings


def test_text_reads_the_variable(monkeypatch):
    monkeypatch.setenv("KS_T_TEXT", "hello")
    assert settings.text("KS_T_TEXT") == "hello"


def test_text_falls_back_to_its_default(monkeypatch):
    monkeypatch.delenv("KS_T_TEXT", raising=False)
    assert settings.text("KS_T_TEXT", "fallback") == "fallback"
    assert settings.text("KS_T_TEXT") == ""


def test_number_reads_an_integer(monkeypatch):
    monkeypatch.setenv("KS_T_NUM", "42")
    assert settings.number("KS_T_NUM", 7) == 42


def test_number_falls_back_when_unset(monkeypatch):
    monkeypatch.delenv("KS_T_NUM", raising=False)
    assert settings.number("KS_T_NUM", 7) == 7


def test_number_falls_back_when_not_a_number(monkeypatch):
    monkeypatch.setenv("KS_T_NUM", "lots")
    assert settings.number("KS_T_NUM", 7) == 7


def test_names_splits_on_commas_and_drops_blanks(monkeypatch):
    monkeypatch.setenv("KS_T_NAMES", " a, b ,,c ,")
    assert settings.names("KS_T_NAMES", "") == ["a", "b", "c"]


def test_names_uses_the_default_list_when_unset(monkeypatch):
    monkeypatch.delenv("KS_T_NAMES", raising=False)
    assert settings.names("KS_T_NAMES", "x,y") == ["x", "y"]
    assert settings.names("KS_T_NAMES", "") == []
