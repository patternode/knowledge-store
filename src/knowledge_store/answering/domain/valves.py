"""Valves: the limits around every question, in one place.

The same limits cover a question answered from passages and a question answered from a mapped
table. TABLE_QUERIES are the catalog questions a mapped table is expected to answer. They are
added to the prompt when that collection's mapping has the attribute or the metric. They are
not an allowlist: the guardrail still screens the question, and the claim is still checked
against the cell or the figure.

    MAX_QUESTION_CHARS    2000  a longer question is refused before any model call
    MAX_HISTORY_TURNS     6     earlier turns of the conversation passed to the agent
    MAX_TOOL_CALLS        12    tool calls per question; past it a tool call is refused and the
                                agent is told to answer from the passages, cells and figures
                                it already has
    MAX_SEARCHES          8     searches (search_passages, search_entities) per question; past it
                                a search is refused with the same instruction, while reads still run
    MAX_MODEL_CALLS       14    model calls per question, the hard stop
    RESERVED_MODEL_CALLS  4     of those, kept for the answer: once this many are left every tool
                                call is refused, so the agent answers in text, the harness asks
                                for the structured answer, and one repair still fits
    MAX_OUTPUT_TOKENS     8000  per model call
    GROUNDING_REPAIRS     1     times the agent is shown its failed citations and asked again

The order matters: the searches run out first, then the tools, and the model calls last, so that a
question that keeps searching still ends in an answer or a plain "not in the sources" rather than in
a spent budget. The first EnterpriseRAG run had the hard stop first, and 11 of 120 questions ended
in no answer after 12 to 18 searches each (docs/_handover-2026-10-25-baselines.md).

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
MAX_TOOL_CALLS = limit("MAX_TOOL_CALLS", 12)
MAX_SEARCHES = limit("MAX_SEARCHES", 8)
MAX_MODEL_CALLS = limit("MAX_MODEL_CALLS", 14)
RESERVED_MODEL_CALLS = limit("RESERVED_MODEL_CALLS", 4)
MAX_OUTPUT_TOKENS = limit("MAX_OUTPUT_TOKENS", 8000)
GROUNDING_REPAIRS = limit("GROUNDING_REPAIRS", 1)

TOOL_BUDGET_SPENT = (
    "Tool budget for this question is spent. Answer now from the passages you have read, "
    "or from the cells and figures the table tools already returned. If they do not answer the "
    "question, set answerable to false and say in gaps what is missing."
)
SEARCH_BUDGET_SPENT = (
    "You have made the most searches one question allows. Do not search again. Answer now from the "
    "passages you have read, or set answerable to false and say in gaps what is missing. You may "
    "still read passages you have found."
)
SEARCH_TOOLS = ("search_passages", "search_entities")


def tools_allowed(counts: dict, tool: str = "") -> str:
    """The refusal a call of tool gets now, or "" when it may run. counts holds tool_calls, searches
    and model_calls as they stand with this call included. The reserve keeps the last model calls
    for the answer, so a tool call made once only that many remain is refused like a spent budget.
    The search cap refuses searches only: a read of what was found still runs."""
    if counts.get("tool_calls", 0) > MAX_TOOL_CALLS:
        return TOOL_BUDGET_SPENT
    if counts.get("model_calls", 0) > MAX_MODEL_CALLS - RESERVED_MODEL_CALLS:
        return TOOL_BUDGET_SPENT
    if tool in SEARCH_TOOLS and counts.get("searches", 0) > MAX_SEARCHES:
        return SEARCH_BUDGET_SPENT
    return ""


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
               type_name="Mission", attributes=("sampleCostMillionUsd",)),
    TableQuery("Which missions launched on an Atlas V?",
               type_name="Mission", attributes=("vehicleFamily",)),
    TableQuery("How many catalogued missions launched on an Atlas V?",
               metric="atlas_v_launches"),
    TableQuery("What total sample cost does the catalog give the Atlas V missions?",
               type_name="Mission", attributes=("sampleCostMillionUsd", "vehicleFamily")),
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
