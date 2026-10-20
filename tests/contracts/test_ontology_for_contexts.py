"""What Extraction and the Knowledge graph rely on from Ontology's contract: the model, the
extraction tool, mappings, renditions' naming rules and the versions."""

from __future__ import annotations

import pytest

from contract_support import published
from knowledge_store import ontology

USES = {
    "extraction": ["CORE_SHAPES", "CORE_TTL", "DATATYPES", "KL", "Mapping", "OntologySpec", "PROMPT_VERSION", "TOOL_NAME",
                   "Table", "model", "subject_template", "tool_spec", "versions"],
    "knowledge_graph": ["Column", "KL", "Mapping", "Table", "label_of", "model", "property_of", "rel_type", "renditions",
                        "versions"],
}


@pytest.mark.parametrize("consumer", sorted(USES))
def test_each_consumer_finds_what_it_uses(consumer):
    published("ontology", USES[consumer])


def test_the_core_files_exist():
    assert ontology.CORE_TTL.is_file() and ontology.CORE_SHAPES.is_file()


def test_the_vocabulary_is_a_namespace_and_datatypes_cover_numbers():
    assert str(ontology.KL).startswith("https://") and {"string", "decimal", "integer"} <= set(ontology.DATATYPES)


def test_graph_names_follow_the_renditions_rules():
    assert ontology.rel_type("launchedBy") == "LAUNCHED_BY"
    assert ontology.label_of("mission") == "Mission"
    assert ontology.property_of("name") == "a_name" and ontology.property_of("launchYear") == "launchYear"


def test_the_active_version_loads_as_a_spec(swept):
    v = ontology.versions.active_version(swept)
    spec, _ = ontology.versions.load_version(swept, v)
    assert v == "0.1.0" and isinstance(spec, ontology.OntologySpec)


def test_the_extraction_tool_is_named_and_built_from_a_spec(swept):
    spec, _ = ontology.versions.load_version(swept, ontology.versions.active_version(swept))
    tool = ontology.tool_spec(spec)
    assert tool["toolSpec"]["name"] == ontology.TOOL_NAME and tool["toolSpec"]["inputSchema"]["json"]["type"] == "object"
    assert isinstance(ontology.PROMPT_VERSION, str)
