from types import SimpleNamespace

from app.api import ai
from app.services.ai import conversations


class FakeDb:
    def __init__(self):
        self.committed = False

    def commit(self):
        self.committed = True


def _setup(monkeypatch, owner_id=7):
    db = FakeDb()
    conv = SimpleNamespace(id=12, user_id=owner_id, title="新对话")
    monkeypatch.setattr(conversations, "get_conversation", lambda _db, cid: conv)
    return db, conv


def test_rename_conversation_api_commits(monkeypatch):
    db, conv = _setup(monkeypatch)
    user = SimpleNamespace(id=7)

    response = ai.api_rename_conversation(
        12, ai.RenameConversationRequest(title="  磁盘排查记录  "), db=db, current_user=user,
    )

    assert response["code"] == 0
    assert response["data"]["title"] == "磁盘排查记录"
    assert conv.title == "磁盘排查记录"
    assert db.committed is True


def test_rename_conversation_api_rejects_non_owner(monkeypatch):
    """非对话所属用户不得重命名他人对话（IDOR 防护回归）。"""
    db, conv = _setup(monkeypatch, owner_id=99)
    user = SimpleNamespace(id=7)

    response = ai.api_rename_conversation(
        12, ai.RenameConversationRequest(title="hacked"), db=db, current_user=user,
    )

    assert response == {"code": 404, "msg": "对话不存在"}
    assert conv.title == "新对话"
    assert db.committed is False


def test_rename_conversation_api_rejects_blank_title(monkeypatch):
    db, conv = _setup(monkeypatch)
    user = SimpleNamespace(id=7)

    response = ai.api_rename_conversation(
        12, ai.RenameConversationRequest(title="   "), db=db, current_user=user,
    )

    assert response == {"code": 400, "msg": "标题不能为空"}
    assert conv.title == "新对话"
    assert db.committed is False
