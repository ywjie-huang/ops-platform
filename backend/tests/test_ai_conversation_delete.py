from types import SimpleNamespace

from app.api import ai
from app.services.ai import conversations


class FakeDb:
    def __init__(self):
        self.committed = False

    def commit(self):
        self.committed = True


def test_delete_conversation_api_commits_transaction(monkeypatch):
    db = FakeDb()
    user = SimpleNamespace(id=7)
    conv = SimpleNamespace(id=12, user_id=7)

    monkeypatch.setattr(conversations, "get_conversation", lambda _db, cid: conv)
    monkeypatch.setattr(
        conversations,
        "delete_conversation",
        lambda _db, conversation_id: conversation_id == 12,
    )

    response = ai.api_delete_conversation(12, db=db, current_user=user)

    assert response == {"code": 0, "msg": "已删除"}
    assert db.committed is True


def test_delete_conversation_api_rejects_non_owner(monkeypatch):
    """非对话所属用户不得删除他人对话（IDOR 防护回归）。"""
    db = FakeDb()
    user = SimpleNamespace(id=7)
    conv = SimpleNamespace(id=12, user_id=99)  # 属于其他用户

    monkeypatch.setattr(conversations, "get_conversation", lambda _db, cid: conv)

    def delete_should_not_run(_db, _cid):
        raise AssertionError("不得删除非本人对话")

    monkeypatch.setattr(conversations, "delete_conversation", delete_should_not_run)

    response = ai.api_delete_conversation(12, db=db, current_user=user)

    assert response == {"code": 404, "msg": "对话不存在"}
    assert db.committed is False
