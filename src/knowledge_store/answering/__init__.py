"""BC-005 Answering: a person's question to an answer made only of claims that passed their checks, within limits, with the steps visible.

This module is the context's contract: other contexts import only the names below.
"""

from knowledge_store.kernel.contract import lazy

_EXPORTS: dict[str, str] = {
    "ClaimVerifier": "ports",
    "FAILED": "adapters.agent_app",
    "GatewayTools": "adapters.agent_app",
    "Guardrail": "adapters.bedrock_guardrail",
    "QuestionScreen": "ports",
    "agent_client": "@adapters.agent_client",
    "answer_locally": "adapters.agent_app",
    "fallback_chat": "@adapters.fallback_chat",
    "run": "adapters.agent_app",
    "streamed": "adapters.agent_app",
    "valves": "@domain.valves",
    "workbench": "@slices.workbench",
}

__getattr__, __dir__ = lazy(__name__, _EXPORTS)
