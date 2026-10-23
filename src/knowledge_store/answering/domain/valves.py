"""Valves: the limits around every question, in one place.

The same limits cover a question answered from passages and a question answered from a mapped
table. TABLE_QUERIES are the catalog questions a mapped table is expected to answer. They are
added to the prompt when that collection's mapping has the attribute or the metric. They are
not an allowlist: the guardrail still screens the question, and the claim is still checked
against the cell or the figure.

    MAX_QUESTION_CHARS    2000  a longer question is refused before any model call
    MAX_HISTORY_TURNS     6     earlier turns of the conversation passed to the agent
    MAX_TOOL_CALLS        16    tool calls per question; past it a tool call is refused and the
                                agent is told to answer from the passages, cells and figures
                                it already has
    MAX_MODEL_CALLS       14    model calls per question, the hard stop
    MAX_OUTPUT_TOKENS     4000  per model call
    GROUNDING_REPAIRS     1     times the agent is shown its failed citations and asked again

and, with GUARDRAIL_ID set, a Bedrock Guardrail applied twice (ApplyGuardrail, outside the model
call so that passages and cells read by tools are never screened as if they were the person's input):

    the question          prompt attacks, denied topics and content filters, before the agent runs
    each claim            contextual grounding against the passage, cell or figure it cites,
                          after the quote or value check

The chat API adds its own: a daily question quota per person, and the Lambda's reserved
concurrency. Each number is an environment variable, set from Terraform.
"""

from __future__ import annotations

from typing import NamedTuple

from knowledge_store.kernel import settings


def limit(name: str, default: int) -> int:
    return settings.number(name, default)


MAX_QUESTION_CHARS = limit("MAX_QUESTION_CHARS", 2000)
MAX_HISTORY_TURNS = limit("MAX_HISTORY_TURNS", 6)
MAX_TOOL_CALLS = limit("MAX_TOOL_CALLS", 16)
MAX_MODEL_CALLS = limit("MAX_MODEL_CALLS", 14)
MAX_OUTPUT_TOKENS = limit("MAX_OUTPUT_TOKENS", 4000)
GROUNDING_REPAIRS = limit("GROUNDING_REPAIRS", 1)

TOOL_BUDGET_SPENT = (
    "Tool budget for this question is spent. Answer now from the passages you have read, "
    "or from the cells and figures the table tools already returned."
)


class TableQuery(NamedTuple):
    """One question a mapped table should answer, and what the mapping must have for it."""

    question: str
    type_name: str = ""
    attributes: tuple[str, ...] = ()
    metric: str = ""


# The space-missions catalog. A collection whose mapping has the named attribute or metric
# is told to answer that question from the table, citing the cell or the figure.
TABLE_QUERIES: tuple[TableQuery, ...] = (
    TableQuery("What sample cost does the catalog give Juno?",
               type_name="Mission", attributes=("sampleCost",)),
    TableQuery("Which missions launched on an Atlas V?",
               type_name="Mission", attributes=("vehicleFamily",)),
    TableQuery("How many catalogued missions launched on an Atlas V?",
               metric="atlas_v_launches"),
    TableQuery("What total sample cost does the catalog give the Atlas V missions?",
               type_name="Mission", attributes=("sampleCost", "vehicleFamily")),
    TableQuery("What name does the catalog give the launch vehicle atlas-v-551?",
               type_name="LaunchVehicle", attributes=("name",)),
)


def table_questions(described: dict | None) -> tuple[str, ...]:
    """The catalog questions this collection's mapped tables can answer.

    described is what describe_structured returns: types with columns, and named metrics.
    A question is included only when every attribute it needs is on that type, or its metric
    is published. A collection with no mapping gets none of them.
    """
    if not isinstance(described, dict):
        return ()
    have: set[tuple[str, str]] = set()
    for table in described.get("types") or []:
        type_name = table.get("type") or ""
        for col in table.get("columns") or []:
            attr = col.get("attribute") or ""
            if type_name and attr:
                have.add((type_name, attr))
    metrics = {m.get("name") for m in (described.get("metrics") or []) if isinstance(m, dict) and m.get("name")}
    out = []
    for query in TABLE_QUERIES:
        if query.metric:
            if query.metric in metrics:
                out.append(query.question)
            continue
        if query.attributes and all((query.type_name, attr) in have for attr in query.attributes):
            out.append(query.question)
    return tuple(out)


def table_query_note(questions: tuple[str, ...]) -> str:
    """Text appended to the system prompt when this collection can answer table questions."""
    if not questions:
        return ""
    lines = "\n".join(f"- {question}" for question in questions)
    return ("\n\nThese questions are answered from the mapped tables. "
            "Cite each value as its cell and each total as its figure:\n" + lines)
