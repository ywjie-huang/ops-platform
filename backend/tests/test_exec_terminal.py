import asyncio
import json

from app.api import exec_terminal


class FakeAgentWebSocket:
    def __init__(self, message=None, error: Exception | None = None):
        self.message = message
        self.error = error
        self.close_reason = ""

    async def recv(self):
        if self.error is not None:
            raise self.error
        return self.message


def test_agent_ready_control_frame_completes_handshake():
    socket = FakeAgentWebSocket(json.dumps({"type": "ready"}))

    buffered = asyncio.run(exec_terminal._wait_for_agent_ready(socket))

    assert buffered is None


def test_agent_error_control_frame_rejects_handshake():
    socket = FakeAgentWebSocket(
        json.dumps({"type": "error", "message": "unsupported Docker exec stream"})
    )

    try:
        asyncio.run(exec_terminal._wait_for_agent_ready(socket))
        raise AssertionError("expected Agent handshake failure")
    except exec_terminal.AgentExecHandshakeError as exc:
        assert str(exc) == "unsupported Docker exec stream"


def test_legacy_agent_first_output_is_buffered():
    socket = FakeAgentWebSocket(b"/ # ")

    buffered = asyncio.run(exec_terminal._wait_for_agent_ready(socket))

    assert buffered == b"/ # "


def test_agent_disconnect_before_ready_reports_reason():
    socket = FakeAgentWebSocket(error=RuntimeError("connection closed"))

    try:
        asyncio.run(exec_terminal._wait_for_agent_ready(socket))
        raise AssertionError("expected Agent handshake failure")
    except exec_terminal.AgentExecHandshakeError as exc:
        assert "connection closed" in str(exc)


def test_backend_bridge_cancels_the_other_direction_after_first_completion():
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

        await exec_terminal._run_bridge_until_closed(finishes(), waits_forever())

    asyncio.run(scenario())

    assert state["cancelled"] is True
