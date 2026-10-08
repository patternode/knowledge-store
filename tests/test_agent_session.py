from knowledge_store.portal_api.agent_client import session_for


def test_one_warm_session_per_person_and_scope():
    a = session_for("site-abc", False)
    assert a == session_for("site-abc", False)          # the same person keeps their session
    assert a != session_for("site-xyz", False)          # people never share one
    assert a != session_for("site-abc", True)           # nor does private reading share with public
    assert len(a) >= 33 and "abc" not in a              # AgentCore's minimum length; the id hides the sub
