"""The chat agent's deployable: AgentCore Runtime's entry point (Dockerfile.agent runs this module).

It composes Answering's agent loop with Access's per-person quota, the Bedrock Guardrail and the
Gateway's MCP tools, all as the caller. Configuration is read here.
"""

from __future__ import annotations

import logging
import os

from knowledge_store.access import agent_quota as quotas
from knowledge_store.answering import FAILED, Guardrail, GatewayTools, run, streamed

log = logging.getLogger("agent")


def _bearer(context) -> str | None:
    for k, v in ((getattr(context, "request_headers", None) or {}).items()):
        if k.lower() == "authorization":
            return v.split(" ", 1)[1] if v.lower().startswith("bearer ") else v
    return os.environ.get("DEV_BEARER_TOKEN")


def admit(token: str | None, quota: "quotas.AgentQuota | None") -> str | None:
    """None if the caller may ask now, else why not. Counts the invocation against the caller's
    daily limit (access/adapters/agent_quota.py), which holds even when the Runtime is called without the portal.
    A limit that cannot be checked refuses: the limit is the only bound on a direct caller's spend."""
    if quota is None:
        return None
    try:
        return quota.check(token)
    except Exception:
        log.exception("quota check failed")
        return "the daily limit could not be checked; try again shortly"


def make_app(quota: "quotas.AgentQuota | None" = None):
    from bedrock_agentcore.runtime import BedrockAgentCoreApp
    app = BedrockAgentCoreApp()
    quota = quota if quota is not None else quotas.AgentQuota.from_env()

    @app.entrypoint
    def invoke(payload: dict, context=None):
        payload = payload or {}
        token = _bearer(context)
        if not token:
            return {"error": "no caller token: the agent acts only as its caller"}
        refused = admit(token, quota)
        if refused:
            return {"error": refused, "quota": True}

        def work(on_step=None):
            with GatewayTools(os.environ["GATEWAY_MCP_URL"], token) as tools:
                return run(payload, tools, guardrail=Guardrail.from_env(), on_step=on_step)

        if payload.get("stream"):
            return streamed(work)  # a generator: the runtime sends it as server-sent events
        try:
            return work()
        except Exception:  # report to the caller rather than a bare 500; the detail is logged
            log.exception("question failed")
            return {"error": FAILED}

    return app


if __name__ == "__main__":
    make_app().run()
