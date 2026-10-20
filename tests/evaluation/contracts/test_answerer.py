"""The Answerer port: given a question, a reply dict with an answer, or an error with abstained set.
Run against both offline adapters: InProcessAnswerer (Answering's local loop, replaced at its
boundary) and HttpAnswerer (against a local chat API)."""

from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from knowledge_store.evaluation import HttpAnswerer, InProcessAnswerer, Question
from knowledge_store.evaluation.adapters import answerers

Q = Question(id="q1", question="Which rocket launched Juno?", private=True)


class ChatApi:
    """A local chat API: POST starts a job, GET reports it, after `polls` pending polls."""

    def __init__(self, final: dict, polls: int = 1):
        self.final, self.polls, self.seen = final, polls, []
        api = self

        class H(BaseHTTPRequestHandler):
            def _send(self, body):
                data = json.dumps(body).encode()
                self.send_response(200)
                self.send_header("content-type", "application/json")
                self.end_headers()
                self.wfile.write(data)

            def do_POST(self):
                n = int(self.headers.get("content-length") or 0)
                api.seen.append(("POST", self.path, self.headers.get("authorization"), json.loads(self.rfile.read(n))))
                self._send({"id": "job-1", "status": "pending"})

            def do_GET(self):
                api.seen.append(("GET", self.path, self.headers.get("authorization"), None))
                if api.polls > 0:
                    api.polls -= 1
                    return self._send({"id": "job-1", "status": "pending"})
                self._send(api.final)

            def log_message(self, *a):
                pass

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), H)
        self.url = f"http://127.0.0.1:{self.server.server_address[1]}"
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def close(self):
        self.server.shutdown()


@pytest.fixture
def api():
    servers = []

    def make(final, polls=1):
        s = ChatApi(final, polls)
        servers.append(s)
        return s
    yield make
    for s in servers:
        s.close()


@pytest.fixture
def in_process(monkeypatch, tmp_path):
    def make(final):
        import knowledge_store.answering as answering
        seen = []

        def answer_locally(root, collection, question, *, private, model_id):
            seen.append((collection, question, private, model_id))
            if isinstance(final, Exception):
                raise final
            return final
        monkeypatch.setattr(answering, "answer_locally", answer_locally, raising=False)
        return InProcessAnswerer(str(tmp_path / "lake"), "missions", "fake-model"), seen
    return make


@pytest.fixture
def http(api):
    def make(final):
        s = api(final)
        return HttpAnswerer(s.url, "tok", "missions", timeout_s=10, poll_s=0.01), s.seen
    return make


@pytest.fixture(params=["in_process", "http"])
def answerer(request):
    return request.getfixturevalue(request.param)


def test_a_reply_carries_the_answer(answerer):
    ask, _ = answerer({"status": "done", "answer": "Atlas V 551", "abstained": False})
    r = ask(Q)
    assert r["answer"] == "Atlas V 551" and not r.get("error")


def test_the_reply_is_a_dict(answerer):
    ask, _ = answerer({"status": "done", "answer": "", "abstained": True})
    assert isinstance(ask(Q), dict)


# --- what each adapter adds -----------------------------------------------------------------------

def test_in_process_asks_the_collection_as_the_question_says(in_process):
    ask, seen = in_process({"answer": "x"})
    ask(Q)
    assert seen == [("missions", "Which rocket launched Juno?", True, "fake-model")]


def test_in_process_opens_the_lake_from_its_uri(tmp_path):
    a = InProcessAnswerer(str(tmp_path), "c", None)
    assert a.collection == "c" and a.model_id is None and hasattr(a.root, "get")


def test_http_sends_the_question_with_the_token_and_polls_the_job(http):
    ask, seen = http({"status": "done", "answer": "x"})
    ask(Q)
    post, *gets = seen
    assert post == ("POST", "/api/chat?c=missions", "Bearer tok", {"question": "Which rocket launched Juno?"})
    assert gets[-1][1] == "/api/chat?c=missions&id=job-1" and all(g[2] == "Bearer tok" for g in gets)


def test_http_turns_a_failed_job_into_an_error(api):
    s = api({"status": "failed", "error": "quota"}, polls=0)
    r = HttpAnswerer(s.url, "t", "c", poll_s=0.01)(Q)
    assert r == {"error": "quota", "abstained": True}


def test_http_a_failed_job_without_a_reason_still_fails(api):
    s = api({"status": "failed"}, polls=0)
    assert HttpAnswerer(s.url, "t", "c", poll_s=0.01)(Q)["error"] == "failed"


def test_http_gives_up_after_its_timeout(api):
    s = api({"status": "done"}, polls=10_000)
    r = HttpAnswerer(s.url, "t", "c", timeout_s=0.05, poll_s=0.01)(Q)
    assert r == {"error": "timed out", "abstained": True}


@pytest.mark.parametrize("url", ["http://example.com", "ftp://localhost", "localhost:8765", "http://10.0.0.1"])
def test_http_refuses_to_send_a_token_in_the_clear(url):
    with pytest.raises(ValueError, match="https"):
        HttpAnswerer(url, "t", "c")


@pytest.mark.parametrize("url", ["https://ks.example.com/", "http://localhost:8765", "http://127.0.0.1:1", "http://[::1]:2"])
def test_http_accepts_https_and_this_machine(url):
    assert not HttpAnswerer(url, "t", "c").base.endswith("/")


def test_the_adapters_module_needs_no_sdk():
    assert "boto3" not in answerers.__dict__
