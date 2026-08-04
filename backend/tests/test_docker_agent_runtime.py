import asyncio
import importlib
import json
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


def test_exec_stream_supports_docker_socketio_read_and_raw_socket_write():
    class RawSocket:
        def __init__(self):
            self.writes = []

        def sendall(self, data: bytes):
            self.writes.append(data)

    class DockerSocketIO:
        def __init__(self):
            self._sock = RawSocket()

        def read(self, size: int):
            assert size == 4096
            return b"container prompt"

    stream = DockerSocketIO()

    docker_agent._validate_exec_stream(stream)

    assert docker_agent._sock_recv(stream, 4096) == b"container prompt"
    docker_agent._sock_write(stream, b"whoami\n")
    assert stream._sock.writes == [b"whoami\n"]


def test_exec_stream_retries_partial_socket_writes():
    class PartialSocket:
        def __init__(self):
            self.received = bytearray()

        def recv(self, size: int):
            return b""

        def send(self, data: bytes):
            chunk = data[:2]
            self.received.extend(chunk)
            return len(chunk)

    stream = PartialSocket()

    docker_agent._sock_write(stream, b"abcdef")

    assert bytes(stream.received) == b"abcdef"


def test_exec_stream_rejects_non_socket_objects():
    try:
        docker_agent._validate_exec_stream(object())
        raise AssertionError("expected unsupported stream to be rejected")
    except TypeError as exc:
        assert "unsupported Docker exec stream" in str(exc)


def test_exec_control_frame_preserves_chinese_error_message():
    frame = json.loads(docker_agent._exec_control_frame("error", "读取容器终端失败"))

    assert frame == {"type": "error", "message": "读取容器终端失败"}


def test_exec_bridge_cancels_the_other_direction_after_first_completion():
    state = {"cancelled": False}

    async def scenario():
        async def finishes():
            await asyncio.sleep(0)

        async def waits_forever():
            try:
                await asyncio.Future()
            except asyncio.CancelledError:
                state["cancelled"] = True
                raise

        await docker_agent._run_bridge_until_closed(finishes(), waits_forever())

    asyncio.run(scenario())

    assert state["cancelled"] is True
