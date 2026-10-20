"""A labelled corpus of replies that an evaluation can get wrong in either direction.

Each case says whether the reply is right. The scorer must agree on every case: the wrong
replies are the false positives an evaluation must not pass, and the right replies and right
declines are there so that stopping false positives does not fail true positives or true
negatives. docs/design/evaluation-false-positives.md compares this scorer with the one before
ADR-048 on the same corpus.
"""

import pytest

from knowledge_store.evaluation import LexicalVerifier, Question, score

JUNO = dict(id="q", question="Which rocket launched Juno?", must=[["Atlas V"]], must_not=["Delta II"])
REVENUE = dict(id="q", question="What was revenue?", figures=[{"value": 2_400_000_000}])
ROUND = dict(id="q", question="What was revenue?", figures=[{"value": 2_000_000_000}])
PRECISE = dict(id="q", question="What was revenue?", figures=[{"value": 94_930_000_000}])
FUNDING = dict(id="q", question="Who funded the probe?", kind="unanswerable", answerable=False)
ORDER = dict(id="q", question="Which launched first?", kind="comparison", must=[["Voyager 2"]],
             first=["Voyager 2", "Voyager 1"])


def reply(answer, **kw):
    return {"answer": answer, **kw}


# (name, question, reply, verdicts, right): verdicts are a claim verifier's, or None.
CASES = [
    # wrong replies: each was, or could have been, passed as right
    ("negated fact", JUNO, reply("It was not an Atlas V."), None, False),
    ("negated fact, contraction", JUNO, reply("Juno didn't fly on an Atlas V."), None, False),
    ("coarse figure a sixth away", REVENUE, reply("Revenue was about $2 billion."), None, False),
    ("wrong figure", REVENUE, reply("Revenue was $2.9 billion."), None, False),
    ("year taken for a figure", dict(ROUND, figures=[{"value": 2025}]), reply("In 2025 revenue rose."), None, False),
    ("decline, then a guess the verifier rejects", FUNDING,
     reply("The sources do not say. It was probably NASA.", claims=[{"text": "NASA funded it"}]),
     [{"supported": False}], False),
    ("near miss asserted", JUNO, reply("An Atlas V and a Delta II."), None, False),
    ("comparison reversed", ORDER, reply("Voyager 1 launched before Voyager 2."), None, False),
    ("answered an unanswerable question", FUNDING, reply("NASA funded it."), None, False),
    # right replies and right declines: each must stay right
    ("plain answer", JUNO, reply("An Atlas V 551."), None, True),
    ("near miss ruled out", JUNO, reply("An Atlas V, not a Delta II."), None, True),
    ("near miss ruled out first", JUNO, reply("Not a Delta II but an Atlas V."), None, True),
    ("no doubt is not a negation", JUNO, reply("There is no doubt it was an Atlas V."), None, True),
    ("not only is not a negation", JUNO, reply("Not only an Atlas V carried it; it was the 551."), None, True),
    ("figure at its own rounding", PRECISE, reply("Revenue was $94.9 billion."), None, True),
    ("figure rounded to whole billions", PRECISE, reply("Revenue was $95 billion."), None, True),
    ("round figure stated round", ROUND, reply("Revenue was $2 billion."), None, True),
    ("round figure stated precisely", ROUND, reply("Revenue was $2.00 billion."), None, True),
    ("cited hedge is a decline", FUNDING, reply("The sources do not say who funded the probe."), None, True),
    ("abstained", FUNDING, reply("", abstained=True), None, True),
    ("decline showing context it found", FUNDING,
     reply("The sources do not say who funded it. They do say it launched in 2011.",
           claims=[{"text": "it launched in 2011"}]), [{"supported": True}], True),
    ("comparison in order", ORDER, reply("Voyager 2 launched before Voyager 1."), None, True),
]


@pytest.mark.parametrize("name,question,result,verdicts,right", CASES, ids=[c[0] for c in CASES])
def test_the_scorer_agrees_with_the_label(name, question, result, verdicts, right):
    assert score(Question(**question), result, verdicts)["correct"] is right


def test_a_decline_with_claims_and_no_verifier_is_flagged_not_failed():
    row = score(Question(**FUNDING), reply("The sources do not say. NASA, perhaps.", claims=[{"text": "NASA"}]))
    assert row["correct"] and row["hedged"]


SOURCE = "Juno was launched on an Atlas V 551 in 2011. Its budget was $1.1 billion."

# (name, claim, supported)
CLAIMS = [
    ("supported claim", "Juno launched on an Atlas V 551", True),
    ("supported figure", "Juno's budget was $1.1 billion", True),
    ("supported year", "Juno launched in 2011", True),
    ("negation the source lacks", "Juno was not launched on an Atlas V 551", False),
    ("wrong year", "Juno was launched on an Atlas V 551 in 2016", False),
    ("wrong figure", "Juno's budget was $1.9 billion", False),
    ("unrelated claim", "Cassini carried the Huygens probe to Titan", False),
]


@pytest.mark.parametrize("name,claim,supported", CLAIMS, ids=[c[0] for c in CLAIMS])
def test_the_lexical_verifier_agrees_with_the_label(name, claim, supported):
    assert LexicalVerifier().grounded("", claim, [SOURCE])[0] is supported
