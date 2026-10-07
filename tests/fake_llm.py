"""A deterministic stand-in for the model, answering each tool the lab uses from the passages
it is sent. Enough to drive the whole lifecycle offline; it knows nothing about any domain
beyond the tiny vocabulary the tests plant in their documents."""

from __future__ import annotations

import json
import re

PASSAGE = re.compile(r'<passage id="([^"]+)">\n(.*?)\n</passage>', re.S)


def _resp(name: str, payload: dict) -> dict:
    return {"output": {"message": {"role": "assistant", "content": [
        {"toolUse": {"toolUseId": "t1", "name": name, "input": payload}}]}},
        "stopReason": "tool_use", "usage": {"inputTokens": 100, "outputTokens": 50}}


class FakeClient:
    """Documents in the tests name missions ("Mission Alpha"), agencies ("Agency Nova") and
    targets ("Planet Kiro"); "launched by" links a mission to an agency, "studies" a mission
    to a target, and "Instrument X" is a thing the first ontology has no term for."""

    def __init__(self):
        self.calls: list[str] = []

    def converse(self, **kw):
        tool = kw["toolConfig"]["tools"][0]["toolSpec"]
        name = tool["name"]
        self.calls.append(name)
        text = kw["messages"][0]["content"][0]["text"]
        passages = PASSAGE.findall(text)
        if name == "propose_types":
            return _resp(name, self._propose(passages))
        if name == "define_ontology":
            return _resp(name, self._define(json.loads(text), kw["system"][0]["text"]))
        if name == "review_ontology":
            # One edit that changes nothing and one that cannot apply: the path runs, the draft stays.
            return _resp(name, {"edits": [
                {"op": "set_datatype", "kind": "attributes", "term": "launchYear", "value": "integer",
                 "reason": "years are whole numbers"},
                {"op": "set_parent", "kind": "classes", "term": "Comet", "value": "TargetBody",
                 "reason": "a comet is a target body"}]})
        if name == "record_knowledge":
            return _resp(name, self._record(passages, tool, text))
        raise AssertionError(name)

    @staticmethod
    def _find(pattern: str, passages):
        for pid, body in passages:
            for m in re.finditer(pattern, body):
                yield pid, m.group(0)

    def _propose(self, passages):
        out = {"classes": [], "relations": [], "attributes": []}
        for label, pat in (("Mission", r"Mission \w+"), ("Space agency", r"Agency \w+"), ("Target body", r"Planet \w+")):
            ex = [{"text": t, "passage_id": p} for p, t in self._find(pat, passages)][:2]
            if ex:
                out["classes"].append({"name": label, "definition": f"A {label.lower()}.", "examples": ex})
        ex = [{"text": t, "passage_id": p} for p, t in self._find(r"launched by", passages)][:1]
        if ex:
            out["relations"].append({"name": "launched by", "definition": "Who launched it.", "subject_type": "Mission",
                                     "object_type": "Space agency", "examples": ex})
        ex = [{"text": t, "passage_id": p} for p, t in self._find(r"in \d{4}", passages)][:1]
        if ex:
            out["attributes"].append({"name": "launch year", "definition": "Year of launch.", "entity_type": "Mission",
                                      "datatype": "integer", "examples": ex})
        return out

    @staticmethod
    def _define(agg, system):
        if "An ontology already exists" in system:
            return {"classes": [{"name": "Instrument", "definition": "A scientific instrument carried by a mission.",
                                 "synonyms": ["payload"]}],
                    "relations": [{"name": "carries", "definition": "A mission carries an instrument.",
                                   "domain": "Mission", "range": "Instrument"}],
                    "attributes": [], "rejected": []}
        return {"classes": [{"name": "Mission", "definition": "A space mission.", "synonyms": ["probe"]},
                            {"name": "SpaceAgency", "label": "Space agency", "definition": "An organisation that flies missions."},
                            {"name": "TargetBody", "label": "Target body", "definition": "What a mission studies."}],
                "relations": [{"name": "launchedBy", "definition": "The agency that launched a mission.",
                               "domain": "Mission", "range": "SpaceAgency"},
                              {"name": "studies", "definition": "The body a mission studies.",
                               "domain": "Mission", "range": "TargetBody"}],
                "attributes": [{"name": "launchYear", "definition": "Year of launch.", "domain": "Mission", "datatype": "integer"}],
                "rejected": [{"name": "noise", "reason": "seen once"}]}

    def _record(self, passages, tool, text):
        schema = tool["inputSchema"]["json"]["properties"]
        types = set(schema["entities"]["items"]["properties"]["type"]["enum"])
        rels = set(schema.get("relations", {}).get("items", {}).get("properties", {}).get("predicate", {}).get("enum", []))
        attrs = set(schema.get("attributes", {}).get("items", {}).get("properties", {}).get("property", {}).get("enum", []))
        known = dict(re.findall(r"- (k\d+): \w+ \"([^\"]+)\"", text))
        known_by_name = {v: k for k, v in known.items()}
        ents, refs = [], {}

        def ent(kind, name, pid):
            if name in known_by_name:
                return known_by_name[name]
            if name not in refs:
                refs[name] = f"e{len(refs) + 1}"
                ents.append({"ref": refs[name], "type": kind, "name": name, "passage_ids": [pid]})
            return refs[name]

        out = {"entities": ents, "attributes": [], "relations": [], "candidates": []}
        for pid, body in passages:
            m = re.search(r"(Mission \w+)", body)
            if not m:
                continue
            mission = ent("Mission", m.group(1), pid) if "Mission" in types or m.group(1) in known_by_name else None
            ag = re.search(r"launched by (Agency \w+)", body)
            if ag and mission and "launchedBy" in rels:
                out["relations"].append({"subject": mission, "predicate": "launchedBy",
                                         "object": ent("SpaceAgency", ag.group(1), pid), "passage_ids": [pid]})
            yr = re.search(r"in (\d{4})", body)
            if yr and mission and "launchYear" in attrs:
                out["attributes"].append({"entity": mission, "property": "launchYear", "value": yr.group(1),
                                          "passage_ids": [pid]})
            st = re.search(r"studies (Planet \w+)", body)
            if st and mission and "studies" in rels:
                out["relations"].append({"subject": mission, "predicate": "studies",
                                         "object": ent("TargetBody", st.group(1), pid), "passage_ids": [pid]})
            ins = re.search(r"carries (Instrument \w+)", body)
            if ins:
                if "carries" in rels and mission:
                    out["relations"].append({"subject": mission, "predicate": "carries",
                                             "object": ent("Instrument", ins.group(1), pid), "passage_ids": [pid]})
                elif "Instrument" not in types:
                    out["candidates"].append({"kind": "class", "term": "Instrument",
                                              "definition": "A scientific instrument on a mission.",
                                              "evidence": ins.group(0), "nearest": None, "passage_ids": [pid]})
        return out
