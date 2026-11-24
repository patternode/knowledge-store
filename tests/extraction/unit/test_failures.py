"""Which extraction failures are worth trying again."""

from __future__ import annotations

from knowledge_store.extraction.domain.failures import is_transient


class ClientError(Exception):
    def __init__(self, code):
        super().__init__(f"An error occurred ({code})")
        self.response = {"Error": {"Code": code}}


class RateLimitError(Exception):
    pass


def test_throttling_timeouts_and_expired_credentials_are_transient():
    assert is_transient(ClientError("ThrottlingException"))
    assert is_transient(ClientError("ExpiredTokenException"))
    assert is_transient(RateLimitError("slow down"))
    assert is_transient(TimeoutError("read timed out"))
    assert is_transient(RuntimeError("Model is overloaded, try again"))


def test_permissions_and_unparseable_answers_are_permanent():
    assert not is_transient(PermissionError("no model access"))
    assert not is_transient(ClientError("AccessDeniedException"))
    assert not is_transient(ValueError("the answer did not parse as JSON"))
