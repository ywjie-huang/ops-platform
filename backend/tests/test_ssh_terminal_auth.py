import asyncio
import json
from types import SimpleNamespace

from app.api import ssh_terminal


class DummySession:
    def __init__(self):
        self.closed = False

    def close(self):
        self.closed = True


class FakeWebSocket:
    def __init__(self, first_message: str):
        self.first_message = first_message
        self.accepted = False
        self.closed_with: tuple[int, str] | None = None

    async def accept(self):
        self.accepted = True

    async def receive_text(self):
        return self.first_message

    async def close(self, code: int, reason: str):
        self.closed_with = (code, reason)


def test_ssh_websocket_requires_a_login_token():
    user, error = ssh_terminal._authenticate_websocket_user(None)

    assert user is None
    assert error == "Authentication required"


def test_ssh_websocket_closes_before_asset_lookup_without_token(monkeypatch):
    websocket = FakeWebSocket(json.dumps({"username": "root", "port": 22}))

    def unexpected_asset_lookup(_asset_id):
        raise AssertionError("asset lookup must follow WebSocket authentication")

    monkeypatch.setattr(ssh_terminal, "_get_asset_sync", unexpected_asset_lookup)

    asyncio.run(ssh_terminal.ws_ssh(websocket, 11))

    assert websocket.accepted is True
    assert websocket.closed_with == (1008, "Authentication required")


def test_ssh_websocket_rejects_revoked_token(monkeypatch):
    monkeypatch.setattr(
        ssh_terminal,
        "decode_access_token",
        lambda _token: {"sub": "7", "jti": "revoked-token"},
    )
    monkeypatch.setattr(ssh_terminal, "is_revoked", lambda _jti: True)

    user, error = ssh_terminal._authenticate_websocket_user("access-token")

    assert user is None
    assert error == "Session expired"


def test_ssh_websocket_rejects_user_without_terminal_permission(monkeypatch):
    session = DummySession()
    user = SimpleNamespace(id=7, username="operator")
    monkeypatch.setattr(
        ssh_terminal,
        "decode_access_token",
        lambda _token: {"sub": "7", "jti": "active-token"},
    )
    monkeypatch.setattr(ssh_terminal, "is_revoked", lambda _jti: False)
    monkeypatch.setattr(ssh_terminal, "SessionLocal", lambda: session)
    monkeypatch.setattr(ssh_terminal, "get_user", lambda _db, _user_id: user)
    monkeypatch.setattr(ssh_terminal, "has_permission", lambda _user, _code: False)

    authenticated_user, error = ssh_terminal._authenticate_websocket_user("access-token")

    assert authenticated_user is None
    assert error == "SSH terminal permission required"
    assert session.closed is True


def test_ssh_websocket_accepts_authorized_user(monkeypatch):
    session = DummySession()
    user = SimpleNamespace(id=7, username="operator")
    seen = {}

    def get_user(_db, user_id):
        seen["user_id"] = user_id
        return user

    def has_permission(candidate, code):
        seen["permission_user"] = candidate
        seen["permission_code"] = code
        return True

    monkeypatch.setattr(
        ssh_terminal,
        "decode_access_token",
        lambda _token: {"sub": "7", "jti": "active-token"},
    )
    monkeypatch.setattr(ssh_terminal, "is_revoked", lambda _jti: False)
    monkeypatch.setattr(ssh_terminal, "SessionLocal", lambda: session)
    monkeypatch.setattr(ssh_terminal, "get_user", get_user)
    monkeypatch.setattr(ssh_terminal, "has_permission", has_permission)

    authenticated_user, error = ssh_terminal._authenticate_websocket_user("access-token")

    assert authenticated_user is user
    assert error is None
    assert seen == {
        "user_id": 7,
        "permission_user": user,
        "permission_code": ssh_terminal.SSH_TERMINAL_PERMISSION,
    }
    assert session.closed is True
