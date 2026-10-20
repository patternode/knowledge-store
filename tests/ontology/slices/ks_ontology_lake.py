"""Helpers the Ontology slice tests share: a local lake and a published version of the sample ontology."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "unit"))

from ks_ontology_sample import TTL  # noqa: E402

from knowledge_store.ontology.slices import versions  # noqa: E402


def master(tmp_path, ttl=TTL, name="master") -> Path:
    d = tmp_path / name
    d.mkdir(exist_ok=True)
    (d / "ontology.ttl").write_text(ttl)
    return d


def bump(ttl: str, version: str) -> str:
    return ttl.replace('owl:versionInfo "1.2.0"', f'owl:versionInfo "{version}"').replace("/1.2.0>", f"/{version}>")


def published(lake, tmp_path, ttl=TTL, activate=True, name="master"):
    return versions.publish(lake, master(tmp_path, ttl, name), by="test", activate=activate)


class ScriptedClient:
    """A ModelClient fake that answers each call with the next scripted tool input (or no tool call)."""

    def __init__(self, *answers):
        self.answers = list(answers)
        self.requests = []

    def converse(self, **request):
        self.requests.append(request)
        answer = self.answers.pop(0)
        name = request["toolConfig"]["tools"][0]["toolSpec"]["name"]
        if answer is None:
            return {"output": {"message": {"content": [{"text": "no"}]}}, "stopReason": "end_turn"}
        if isinstance(answer, Exception):
            raise answer
        return {"output": {"message": {"content": [{"toolUse": {"toolUseId": "t", "name": name, "input": answer}}]}},
                "stopReason": "tool_use", "usage": {"inputTokens": 3, "outputTokens": 2}}
