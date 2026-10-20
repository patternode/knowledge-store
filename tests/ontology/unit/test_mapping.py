"""ontology.domain.mapping: the tables and metrics beside an ontology, checked against it."""

import pytest
import yaml
from rdflib import Graph

from knowledge_store.ontology.domain import mapping as m
from ks_ontology_sample import spec

S = spec()

TABLES = {
    "missions": {"location": "tables/missions.csv", "class": "Mission", "key": "id",
                 "columns": {"year": {"attribute": "launchYear", "datatype": "xsd:integer"},
                             "agency": {"relation": "launchedBy", "match": "code"}}},
    "orgs": {"location": "tables/orgs.csv", "class": "Organisation", "key": ["code"], "scope": "private",
             "columns": {"motto": {"attribute": "motto"}}},
}

METRICS = {"metrics": [{"name": "missions_per_year", "description": "Missions a year",
                        "expression": {"dialects": [{"dialect": "ansi_sql", "expression": "SELECT year, count(*) FROM missions GROUP BY year"}]},
                        "custom_extensions": [{"vendor_name": "COA", "data": {"source_table": "missions", "ontology_concepts": ["Mission"], "unit": "missions", "return_type": "integer"}}]}]}


def _write(tmp_path, tables=None, metrics=None):
    if tables is not None:
        (tmp_path / "mappings.yaml").write_text(yaml.safe_dump({"tables": tables}))
    if metrics is not None:
        (tmp_path / "metrics.osi.yaml").write_text(yaml.safe_dump(metrics))
    return tmp_path


def _load(tmp_path, tables=TABLES, metrics=None):
    return m.load(_write(tmp_path, tables, metrics), S)


def _variant(table, **changes):
    t = {k: (dict(v) if isinstance(v, dict) else v) for k, v in TABLES[table].items()}
    t.update(changes)
    return {**TABLES, table: t}


def test_a_directory_without_a_mapping_has_none(tmp_path):
    assert m.load(tmp_path, S) is None


def test_metrics_need_a_mapping_beside_them(tmp_path):
    with pytest.raises(ValueError, match="needs mappings.yaml"):
        m.load(_write(tmp_path, metrics=METRICS), S)


def test_a_mapping_is_read_with_columns_typed_by_the_ontology(tmp_path):
    mp = _load(tmp_path, metrics=METRICS)
    t = mp.table("missions")
    assert (t.class_name, t.key, t.scope) == ("Mission", ("id",), "public")
    assert t.column("year").datatype == "integer" and t.column("launchYear").name == "year"
    assert t.column("agency").range == "Organisation"
    assert mp.by_class("Organisation").scope == "private"
    assert mp.metrics[0].expression.startswith("SELECT year") and mp.metrics[0].unit == "missions"


def test_the_json_form_round_trips(tmp_path):
    mp = _load(tmp_path, metrics=METRICS)
    assert m.Mapping.from_json(mp.to_json()) == mp


def test_locations_leave_out_live_sources():
    t = m.Table("a", "coa:123", "a", "Mission", ("id",), ())
    u = m.Table("b", "tables/b.csv", "b", "Target", ("id",), ())
    assert m.Mapping((t, u)).locations() == {"tables/b.csv"}


def test_table_lookup_by_logical_name_class_or_name():
    t = m.Table("n", "l", "logical", "Mission", ("id",), ())
    mp = m.Mapping((t,))
    assert mp.table("n") is mp.table("logical") is mp.table("Mission") is t and mp.table("x") is None


@pytest.mark.parametrize("tables,message", [
    ({}, "needs a tables mapping"),
    ({"bad name": TABLES["missions"]}, "plain name"),
    ({**TABLES, "missions": {**TABLES["missions"], "logical_table": "a-b"}}, "logical_table"),
    ({**TABLES, "missions": {**TABLES["missions"], "location": "../x.csv"}}, "relative path"),
    ({**TABLES, "missions": {**TABLES["missions"], "location": "/abs.csv"}}, "relative path"),
    ({**TABLES, "missions": {**TABLES["missions"], "class": "Ghost"}}, "not in the ontology"),
    ({**TABLES, "missions": {**TABLES["missions"], "key": []}}, "needs a key"),
    ({**TABLES, "missions": {**TABLES["missions"], "columns": {}}}, "needs columns"),
    ({**TABLES, "missions": {**TABLES["missions"], "scope": "secret"}}, "public or private"),
    ({**TABLES, "copy": {**TABLES["missions"]}}, "share a logical_table|fill the same class"),
    ({**TABLES, "copy": {**TABLES["missions"], "logical_table": "copy"}}, "fill the same class"),
])
def test_a_table_that_does_not_fit_the_ontology_is_refused(tmp_path, tables, message):
    with pytest.raises(ValueError, match=message):
        _load(tmp_path, tables)


@pytest.mark.parametrize("column,message", [
    ("not a mapping", "must be a mapping"),
    ({}, "not both and not neither"),
    ({"attribute": "launchYear", "relation": "studies"}, "not both"),
    ({"attribute": "ghost"}, "not in the ontology"),
    ({"attribute": "launchYear", "datatype": "xsd:date"}, "disagrees"),
    ({"attribute": "launchYear", "datatype": "xsd:nonsense"}, "is not one of"),
    ({"relation": "ghost", "match": "x"}, "not in the ontology"),
    ({"relation": "launchedBy", "range": "Ghost", "match": "code"}, "range that is a class"),
    ({"relation": "launchedBy", "range": "Target", "match": "code"}, "not the range"),
    ({"relation": "launchedBy"}, "needs match"),
])
def test_a_column_that_does_not_fit_the_ontology_is_refused(tmp_path, column, message):
    t = _variant("missions", columns={"c": column})
    with pytest.raises(ValueError, match=message):
        _load(tmp_path, t)


def test_an_attribute_of_another_class_is_refused(tmp_path):
    t = _variant("orgs", columns={"y": {"attribute": "launchYear"}})
    with pytest.raises(ValueError, match="not of class"):
        _load(tmp_path, t)


def test_a_relation_from_another_class_is_refused(tmp_path):
    t = _variant("orgs", columns={"y": {"relation": "launchedBy", "match": "code"}})
    with pytest.raises(ValueError, match="does not start at"):
        _load(tmp_path, t)


def test_a_full_xsd_iri_is_a_datatype(tmp_path):
    t = _variant("missions", columns={"year": {"attribute": "launchYear", "datatype": "http://www.w3.org/2001/XMLSchema#int"}})
    assert _load(tmp_path, t).table("missions").column("year").datatype == "integer"


def test_a_join_to_a_class_without_a_table_is_refused(tmp_path):
    with pytest.raises(ValueError, match="has no table"):
        _load(tmp_path, {"missions": TABLES["missions"]})


def test_a_join_on_a_field_the_other_table_lacks_is_refused(tmp_path):
    t = _variant("missions", columns={"agency": {"relation": "launchedBy", "match": "nothing"}})
    with pytest.raises(ValueError, match="is not a column or key"):
        _load(tmp_path, t)


def _metric(**changes):
    base = METRICS["metrics"][0]
    return {"metrics": [{**base, **changes}]}


def _coa(**data):
    return [{"vendor_name": "COA", "data": {"source_table": "missions", **data}}]


@pytest.mark.parametrize("metric,message", [
    (_metric(name="bad name"), "plain name"),
    (_metric(expression={"dialects": [{"dialect": "ANSI_SQL", "expression": "DELETE FROM missions"}]}), "must be a SELECT"),
    (_metric(expression={"dialects": [{"dialect": "ANSI_SQL", "expression": "SELECT 1; DROP TABLE x"}]}), "read-only"),
    (_metric(expression={"dialects": [{"dialect": "ANSI_SQL", "expression": "SELECT 1 -- x"}]}), "read-only"),
    (_metric(expression={}), "must be a SELECT"),
    (_metric(custom_extensions=_coa(source_table="ghost")), "not a logical_table"),
    (_metric(custom_extensions=_coa(ontology_concepts=["Ghost"])), "not a class"),
    ({"metrics": METRICS["metrics"] * 2}, "used twice"),
])
def test_a_metric_that_is_not_a_safe_select_over_a_mapped_table_is_refused(tmp_path, metric, message):
    with pytest.raises(ValueError, match=message):
        _load(tmp_path, metrics=metric)


def _table(**changes):
    base = dict(name="t", location="tables/t.csv", logical_table="t", class_name="Mission", key=("id",),
                columns=(m.Column(name="y", attribute="launchYear", datatype="integer"),))
    base.update(changes)
    return m.Table(**base)


def _metric_obj(**changes):
    base = dict(name="n", description="d", expression="SELECT 1", source_table="t")
    base.update(changes)
    return m.Metric(**base)


@pytest.mark.parametrize("old,new,kind", [
    (None, None, "none"),
    (None, m.Mapping((_table(),)), "additive"),
    (m.Mapping((_table(),)), None, "removal"),
    (m.Mapping((_table(),)), m.Mapping((_table(),)), "none"),
    (m.Mapping((_table(),)), m.Mapping((_table(), _table(logical_table="u"))), "additive"),
    (m.Mapping((_table(),)), m.Mapping((_table(key=("other",)),)), "semantic"),
    (m.Mapping((_table(),)), m.Mapping((_table(columns=()),)), "removal"),
    (m.Mapping((_table(columns=()),)), m.Mapping((_table(),)), "additive"),
    (m.Mapping((_table(),)), m.Mapping((_table(columns=(m.Column(name="y", attribute="launchYear", datatype="decimal"),)),)), "semantic"),
    (m.Mapping((_table(),), (_metric_obj(),)), m.Mapping((_table(),), (_metric_obj(description="new words"),)), "descriptive"),
    (m.Mapping((_table(),), (_metric_obj(),)), m.Mapping((_table(),), (_metric_obj(expression="SELECT 2"),)), "semantic"),
    (m.Mapping((_table(),), (_metric_obj(),)), m.Mapping((_table(),)), "removal"),
    (m.Mapping((_table(),)), m.Mapping((_table(),), (_metric_obj(),)), "additive"),
])
def test_change_kind_names_the_strongest_change(old, new, kind):
    assert m.change_kind(old, new)[0] == kind


def test_change_kind_notes_each_change():
    _, notes = m.change_kind(m.Mapping((_table(),)), m.Mapping((_table(logical_table="u"),)))
    assert notes == ["table t removed", "table u"]


def test_the_subject_template_is_the_class_and_key_columns():
    assert m.subject_template(S, _table(key=("a", "b"))) == "https://example.org/space/Mission/{a}/{b}"


def test_r2rml_is_turtle_with_a_join_for_each_relation(tmp_path):
    mp = _load(tmp_path)
    ttl = m.r2rml(S, mp)
    Graph().parse(data=ttl, format="turtle")
    assert 'rr:joinCondition [ rr:child "agency" ; rr:parent "code" ]' in ttl
    assert "rr:datatype xsd:integer" in ttl


def test_r2rml_adds_a_hash_to_a_namespace_without_one(tmp_path):
    import dataclasses

    mp = _load(tmp_path)
    assert "@prefix o:   <https://x.org/o#> ." in m.r2rml(dataclasses.replace(S, namespace="https://x.org/o"), mp)


def test_agent_lines_are_empty_without_tables():
    assert m.agent_lines(None) == [] and m.agent_lines(m.Mapping()) == []


def test_column_json_names_only_what_it_maps():
    assert m.Column(name="a").to_json() == {"name": "a"}
    assert m.Column(name="a", attribute="x").to_json() == {"name": "a", "attribute": "x", "datatype": "string"}
