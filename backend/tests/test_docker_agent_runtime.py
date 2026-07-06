import importlib
import sys
from types import SimpleNamespace

sys.modules.setdefault("psutil", SimpleNamespace())

docker_agent = importlib.import_module("agent.docker_agent")


def test_read_container_logs_decodes_docker_sdk_bytes(monkeypatch):
    calls = []

    class FakeContainer:
        def logs(self, **kwargs):
            calls.append(kwargs)
            return "第一行\nsecond line".encode("utf-8")

    class FakeContainers:
        def get(self, container_id: str):
            assert container_id == "abc123def456"
            return FakeContainer()

    class FakeDockerClient:
        containers = FakeContainers()

    monkeypatch.setattr(docker_agent, "_docker_client", FakeDockerClient())

    logs = docker_agent.read_container_logs("abc123def456", 300)

    assert logs == "第一行\nsecond line"
    assert calls == [
        {"stdout": True, "stderr": True, "tail": 300, "timestamps": True}
    ]
