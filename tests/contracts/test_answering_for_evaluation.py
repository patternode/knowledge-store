"""What Evaluation relies on from Answering's contract: the ClaimVerifier port it shares, and the
in-process agent loop its InProcessAnswerer runs."""

from __future__ import annotations

import inspect

from contract_support import published
from knowledge_store import answering
from knowledge_store.evaluation import LexicalVerifier


def test_evaluation_finds_what_it_uses():
    published("answering", ["ClaimVerifier", "answer_locally"])


def test_the_lexical_verifier_satisfies_the_shared_port():
    assert hasattr(LexicalVerifier(), "grounded") and "grounded" in answering.ClaimVerifier.__dict__


def test_the_local_loop_takes_what_the_answerer_passes():
    params = inspect.signature(answering.answer_locally).parameters
    assert {"private", "model_id"} <= set(params) and len([p for p in params.values() if p.default is p.empty]) <= 3
