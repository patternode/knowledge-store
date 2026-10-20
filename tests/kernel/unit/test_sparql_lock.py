"""kernel.sparql_lock: one re-entrant lock for rdflib's parser."""

import threading

from knowledge_store.kernel.sparql_lock import PARSE_LOCK


def test_the_lock_is_reentrant_so_nested_parses_do_not_deadlock():
    with PARSE_LOCK:
        assert PARSE_LOCK.acquire(timeout=1)
        PARSE_LOCK.release()


def test_another_thread_waits_while_the_lock_is_held():
    got = []
    with PARSE_LOCK:
        t = threading.Thread(target=lambda: got.append(PARSE_LOCK.acquire(timeout=0.05)))
        t.start()
        t.join()
    assert got == [False]
