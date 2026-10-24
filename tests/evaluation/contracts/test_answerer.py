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

        def answer_locally(root, collection, question, *, private, model_id, toolset="all"):
            seen.append((collection, question, private, model_id, toolset))
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
    assert seen == [("missions", "Which rocket launched Juno?", True, "fake-model", "all")]


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


# --- another system's answers, from a file ---------------------------------------------------------

from knowledge_store.evaluation import FileAnswerer, load_answer_index  # noqa: E402

ROWS = [
    {"question_id": "q1", "answer": "Juno launched on an Atlas V 551.", "document_ids": ["dsid_a", "dsid_b"]},
    {"question_id": "q2", "answer": "", "document_ids": []},
]


def _answers(tmp_path, rows=ROWS):
    p = tmp_path / "answers.jsonl"
    p.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
    return p


def test_a_file_answer_is_read_with_its_documents_as_sources(tmp_path):
    (tmp_path / "docs" / "missions").mkdir(parents=True)
    (tmp_path / "docs" / "missions" / "juno.json").write_text("The probe launched on an Atlas V 551.", encoding="utf-8")
    ask = FileAnswerer(_answers(tmp_path), index={"dsid_a": "missions/juno.json"}, documents=tmp_path / "docs")
    r = ask(Q)
    assert r["answer"] == "Juno launched on an Atlas V 551." and not r["abstained"] and r["claims"] == []
    assert r["sources"] == [
        {"n": 1, "name": "missions/juno.json", "doc": "dsid_a", "text": "The probe launched on an Atlas V 551."},
        {"n": 2, "name": "dsid_b", "doc": "dsid_b"},
    ]


def test_an_empty_file_answer_is_an_abstention_and_a_missing_one_an_error(tmp_path):
    ask = FileAnswerer(_answers(tmp_path))
    assert ask(Question(id="q2", question="?"))["abstained"] is True
    assert ask(Question(id="q9", question="?")) == {"error": "not in the answers file", "abstained": True}


def test_an_answer_index_is_a_json_object_or_lines(tmp_path):
    obj = tmp_path / "uuid_index.json"
    obj.write_text(json.dumps({"dsid_a": "missions/juno.json"}), encoding="utf-8")
    lines = tmp_path / "documents.jsonl"
    lines.write_text('{"doc_id": "dsid_a", "path": "missions/juno.json"}\n{"id": "dsid_b", "file": "b.txt"}\n',
                     encoding="utf-8")
    assert load_answer_index(obj) == {"dsid_a": "missions/juno.json"}
    assert load_answer_index(lines) == {"dsid_a": "missions/juno.json", "dsid_b": "b.txt"}
