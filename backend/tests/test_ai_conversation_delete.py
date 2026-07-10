from app.api import ai
from app.services.ai import conversations


class FakeDb:
    def __init__(self):
        self.committed = False

    def commit(self):
        self.committed = True


def test_delete_conversation_api_commits_transaction(monkeypatch):
    db = FakeDb()

    monkeypatch.setattr(
        conversations,
        "delete_conversation",
        lambda _db, conversation_id: conversation_id == 12,
    )

    response = ai.api_delete_conversation(12, db=db, _=object())

    assert response == {"code": 0, "msg": "已删除"}
    assert db.committed is True
