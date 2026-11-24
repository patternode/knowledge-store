"""The no-context baseline and the trend page."""

from knowledge_store.evaluation import Question
from knowledge_store.evaluation.adapters.answerers import NoContextAnswerer
from knowledge_store.evaluation.adapters.trend import trend_html


class Model:
    def converse(self, **kw):
        assert "toolConfig" not in kw  # no tools: nothing to retrieve with
        return {"output": {"message": {"content": [{"text": "Probably a Delta II."}]}}, "usage": {"inputTokens": 5}}


def test_the_no_context_baseline_answers_without_tools_or_sources():
    out = NoContextAnswerer("m", client=Model())(Question(id="q", question="Which rocket?", must=[["Atlas V"]]))
    assert out["answer"] == "Probably a Delta II." and out["retrieved"] == [] and out["context"] == "none"


def test_the_trend_page_has_a_row_per_run_oldest_first():
    runs = [{"when": "2026-11-24T10:00", "set": "s", "summary": {"all": {"accuracy": 0.8, "recall_at_10": 0.9}}},
            {"when": "2026-11-20T10:00", "set": "s", "summary": {"all": {"accuracy": 0.7, "recall_at_10": 0.85}}}]
    page = trend_html(runs)
    assert page.index("2026-11-20") < page.index("2026-11-24") and "<polyline" in page
