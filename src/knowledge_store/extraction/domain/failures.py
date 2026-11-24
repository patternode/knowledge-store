"""Whether an extraction failure is worth trying again.

A transient failure is one the same call could pass a little later: the model provider throttled
it, timed it out, was overloaded or briefly unreachable, or the credentials expired mid-run. A
document that failed that way is deferred and tried again by the next sweep, up to ATTEMPTS
times, and only then rejected. Anything else (a refused permission, an answer that does not parse,
a document the model cannot read) is permanent, and the document is rejected at once, as before.

Pure: it reads only the exception's class names and message, never an SDK.
"""

from __future__ import annotations

ATTEMPTS = 3

_TRANSIENT_NAMES = {
    "ThrottlingException", "TooManyRequestsException", "ServiceUnavailableException",
    "ModelTimeoutException", "ModelNotReadyException", "InternalServerException",
    "ExpiredTokenException", "RateLimitError", "APITimeoutError", "APIConnectionError",
    "InternalServerError", "OverloadedError", "TimeoutError", "ConnectionError",
    "ReadTimeoutError", "ConnectTimeoutError", "EndpointConnectionError",
}
_TRANSIENT_WORDS = ("throttl", "rate limit", "rate exceeded", "too many requests", "timed out", "timeout",
                    "overloaded", "service unavailable", "temporarily unavailable", "expired token",
                    "security token included in the request is expired", "connection reset")


def is_transient(error: BaseException) -> bool:
    names = {c.__name__ for c in type(error).__mro__}
    code = str(getattr(error, "response", {}) and (error.response or {}).get("Error", {}).get("Code", "") or "")
    if names & _TRANSIENT_NAMES or code in _TRANSIENT_NAMES:
        return True
    text = str(error).lower()
    return any(w in text for w in _TRANSIENT_WORDS)
