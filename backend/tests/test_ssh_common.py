from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from app.api.ssh_common import _build_ssh_client


def test_build_ssh_client_falls_back_to_asset_password_when_auth_payload_has_empty_password():
    asset = SimpleNamespace(
        ip_address="172.16.100.21",
        ssh_port=2222,
        ssh_username="ops",
        ssh_password="saved-password",
        ssh_key_id=None,
    )

    with patch("app.api.ssh_common._get_default_ssh_key_sync", return_value=None), patch("app.api.ssh_common.paramiko.SSHClient") as ssh_client_cls:
        ssh_client = MagicMock()
        ssh_client_cls.return_value = ssh_client

        client, username, host = _build_ssh_client(asset, {
            "username": "ops",
            "port": 2222,
            "password": "",
        })

        assert client is ssh_client
        assert username == "ops"
        assert host == "172.16.100.21"
        ssh_client.connect.assert_called_once()
        kwargs = ssh_client.connect.call_args.kwargs
        assert kwargs["password"] == "saved-password"
        assert kwargs["port"] == 2222
        assert kwargs["username"] == "ops"
