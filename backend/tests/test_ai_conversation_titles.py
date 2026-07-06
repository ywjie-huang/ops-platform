import asyncio
from pathlib import Path
from types import SimpleNamespace

from app.services.ai.titles import (
    DEFAULT_TITLE,
    generate_rule_title,
    is_title_worthy,
    maybe_set_rule_title,
    refine_conversation_title_task,
    sanitize_llm_title,
)


class FakeDb:
    def __init__(self, conv):
        self.conv = conv
        self.flushed = False

    def get(self, model, conversation_id):
        return self.conv

    def flush(self):
        self.flushed = True


def test_short_greetings_are_not_title_worthy():
    for text in [
        "你好",
        "hi",
        "hello",
        "在吗",
        "谢谢",
        "好的",
        "嗯",
        "ok",
        "可以",
        "你是谁",
    ]:
        assert is_title_worthy(text) is False


def test_ops_questions_are_title_worthy():
    assert is_title_worthy("今天哪台服务器资源异常？") is True
    assert is_title_worthy("harbor 为什么指标采集不到") is True


def test_rule_title_for_server_resource_question():
    title = generate_rule_title("今天哪台服务器资源异常？")

    assert title == "服务器资源异常"
    assert title != DEFAULT_TITLE
    assert len(title) <= 20


def test_rule_title_preserves_subject_for_metric_collection_issue():
    title = generate_rule_title("harbor 为什么指标采集不到")

    assert title == "harbor 指标采集排查"


def test_maybe_set_rule_title_updates_default_title_only():
    conv = SimpleNamespace(id=1, title=DEFAULT_TITLE)
    db = FakeDb(conv)

    rule_title = maybe_set_rule_title(db, conv.id, "今天哪台服务器资源异常？")

    assert rule_title == "服务器资源异常"
    assert conv.title == "服务器资源异常"
    assert db.flushed is True


def test_maybe_set_rule_title_does_not_overwrite_existing_title():
    conv = SimpleNamespace(id=1, title="人工命名")
    db = FakeDb(conv)

    rule_title = maybe_set_rule_title(db, conv.id, "今天哪台服务器资源异常？")

    assert rule_title is None
    assert conv.title == "人工命名"
    assert db.flushed is False


def test_sanitize_llm_title_rejects_generic_or_noisy_output():
    assert sanitize_llm_title("《服务器资源异常排查》") == "服务器资源异常排查"
    assert sanitize_llm_title("标题：今天哪台服务器资源异常？") == "服务器资源异常"
    assert sanitize_llm_title("新对话") is None
    assert sanitize_llm_title("你好") is None


def test_async_refinement_uses_fresh_session_and_keeps_manual_title():
    sessions = []

    class FakeConversation:
        def __init__(self):
            self.title = "人工命名"

    class FakeSession:
        def __init__(self):
            self.conv = FakeConversation()
            self.committed = False
            self.closed = False

        def get(self, model, conversation_id):
            return self.conv

        def commit(self):
            self.committed = True

        def rollback(self):
            pass

        def close(self):
            self.closed = True

    def session_factory():
        session = FakeSession()
        sessions.append(session)
        return session

    async def title_generator(*args, **kwargs):
        return "服务器资源异常排查"

    asyncio.run(
        refine_conversation_title_task(
            1,
            "今天哪台服务器资源异常？",
            rule_title="服务器资源异常",
            session_factory=session_factory,
            title_generator=title_generator,
        )
    )

    assert len(sessions) == 1
    assert sessions[0].conv.title == "人工命名"
    assert sessions[0].committed is False
    assert sessions[0].closed is True


def test_chat_api_schedules_title_refinement_once_after_final_answer():
    source = Path("backend/app/api/ai.py").read_text(encoding="utf-8")

    assert source.count("schedule_title_refinement(") == 1
    assert "assistant_text=full_text" in source
