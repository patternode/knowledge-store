"""The Azure Function App: the portal API, the knowledge tools over MCP, and the chat worker.

Thin on purpose: each function hands its request to knowledge_store.hosts.azure, which holds the
logic and its tests. infra/azure/package_function.py puts this file, host.json and the package
together with its dependencies into the zip Terraform deploys.

    GET|POST /api/{*path}   the portal API, called by the portal page with the person's token
    POST     /mcp           the tools, called through API Management by Copilot Studio and agents
    queue    chat           answers questions posted to /api/chat
"""

import logging

import azure.functions as func

from knowledge_store.hosts import azure as host

app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)  # every route verifies its bearer token


def _response(status: int, headers: dict, body: str) -> func.HttpResponse:
    return func.HttpResponse(body, status_code=status, headers=headers)


def _headers(req: func.HttpRequest) -> dict:
    return {k.lower(): v for k, v in req.headers.items()}


@app.route(route="api/{*path}", methods=["GET", "POST"])
def portal(req: func.HttpRequest) -> func.HttpResponse:
    path = "/api/" + (req.route_params.get("path") or "")
    body = req.get_body().decode() if req.method == "POST" else None
    return _response(*host.portal(req.method, path, dict(req.params), body, _headers(req)))


@app.route(route="mcp", methods=["GET", "POST", "DELETE"])
def mcp(req: func.HttpRequest) -> func.HttpResponse:
    return _response(*host.mcp(req.method, req.get_body().decode() or None, _headers(req)))


@app.queue_trigger(arg_name="msg", queue_name="%CHAT_QUEUE%", connection="LakeQueue")
def chat(msg: func.QueueMessage) -> None:
    logging.info("answering %s", msg.id)
    host.answer(msg.get_body().decode())
