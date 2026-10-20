"""The ClaimVerifier port (Answering's, shared with Evaluation): grounded(question, claim, sources)
returns (supported, score). Run against the LexicalVerifier, and the HhemVerifier with a stand-in
model (the real one needs the `verify` extra and a download)."""

from __future__ import annotations

import pytest

from knowledge_store.evaluation import HhemVerifier, LexicalVerifier
from knowledge_store.evaluation.adapters.verifiers import HHEM_REVISION

SOURCE = ["Juno launched on an Atlas V 551 rocket from Cape Canaveral in August 2011."]


class StandIn:
    """Scores a pair by word overlap, as HHEM's predict would return a probability."""

    def __init__(self):
        self.pairs = []

    def predict(self, pairs):
        self.pairs.extend(pairs)
        premise, claim = pairs[0]
        words = [w for w in claim.lower().split() if len(w) > 3]
        return [sum(w.strip(".") in premise.lower() for w in words) / max(len(words), 1)]


@pytest.fixture(params=["lexical", "hhem"])
def verifier(request):
    if request.param == "lexical":
        return LexicalVerifier()
    return HhemVerifier(model=StandIn())


def test_a_claim_its_source_states_is_supported(verifier):
    ok, score = verifier.grounded("Which rocket?", "Juno launched on an Atlas V 551 rocket.", SOURCE)
    assert ok is True and score is not None and 0 <= score <= 1


def test_a_claim_its_source_does_not_state_is_unsupported(verifier):
    ok, _ = verifier.grounded("Who built it?", "Engineers assembled Juno inside Toulouse factories during winter.", SOURCE)
    assert ok is False


def test_the_result_is_a_pair_of_a_bool_and_a_score(verifier):
    out = verifier.grounded("?", "Juno launched in August 2011.", SOURCE)
    assert isinstance(out, tuple) and len(out) == 2 and isinstance(out[0], bool)


# --- the lexical verifier -------------------------------------------------------------------------

def test_a_number_the_source_does_not_state_fails_whatever_the_words():
    assert LexicalVerifier().grounded("?", "Revenue was $3.4 billion.", ["Revenue was $3.1 billion."]) == (False, 0.0)


def test_a_number_the_source_states_at_another_rounding_passes():
    ok, _ = LexicalVerifier().grounded("?", "Revenue was $3.10 billion.", ["Revenue was $3.1 billion."])
    assert ok


def test_a_claim_with_no_content_words_is_supported():
    assert LexicalVerifier().grounded("?", "It is.", SOURCE) == (True, 1.0)


def test_the_threshold_decides_the_verdict():
    claim = "Juno launched from Florida."
    assert not LexicalVerifier(threshold=0.9).grounded("?", claim, SOURCE)[0]
    assert LexicalVerifier(threshold=0.3).grounded("?", claim, SOURCE)[0]


def test_every_source_is_read():
    ok, _ = LexicalVerifier().grounded("?", "Juno reached Jupiter.", ["Juno launched.", "It reached Jupiter in 2016."])
    assert ok


# --- the HHEM verifier ----------------------------------------------------------------------------

def test_hhem_sends_the_sources_as_premise_and_the_claim_as_hypothesis():
    model = StandIn()
    HhemVerifier(model=model).grounded("?", "Juno launched.", ["one", "two"])
    assert model.pairs == [("one\ntwo", "Juno launched.")]


def test_hhem_cuts_a_long_premise():
    model = StandIn()
    HhemVerifier(model=model).grounded("?", "c", ["x" * 20_000])
    assert len(model.pairs[0][0]) == 8000


def test_hhem_compares_its_score_with_the_threshold():
    class Fixed:
        def predict(self, pairs):
            return [0.4]
    assert HhemVerifier(threshold=0.5, model=Fixed()).grounded("?", "c", ["s"]) == (False, 0.4)
    assert HhemVerifier(threshold=0.4, model=Fixed()).grounded("?", "c", ["s"]) == (True, 0.4)


def test_hhem_is_pinned_to_one_revision():
    assert len(HHEM_REVISION) == 40


def test_the_real_hhem_model_loads_at_its_pinned_revision():
    pytest.importorskip("transformers")
    pytest.skip("downloads the model: run by hand when calibrating (ADR-048)")
