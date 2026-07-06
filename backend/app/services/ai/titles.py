"""Conversation title generation for AI chats."""
from __future__ import annotations

import asyncio
import logging
import re
from collections.abc import Awaitable, Callable
from typing import Any

from sqlalchemy.orm import Session

from app.db.database import SessionLocal
from app.models.conversation import Conversation

logger = logging.getLogger(__name__)

DEFAULT_TITLE = "新对话"
MAX_TITLE_LENGTH = 20

LOW_INFO_MESSAGES = {
    "hi",
    "hello",
    "hey",
    "ok",
    "okay",
    "thanks",
    "你好",
    "您好",
    "在吗",
    "谢谢",
    "感谢",
    "好的",
    "好",
    "嗯",
    "嗯嗯",
    "可以",
    "你是谁",
    "你是什么",
    "你是什么模型",
}

OPS_KEYWORDS = (
    "服务器",
    "主机",
    "告警",
    "巡检",
    "cpu",
    "内存",
    "磁盘",
    "负载",
    "容器",
    "docker",
    "k8s",
    "kubernetes",
    "工单",
    "部署",
    "prometheus",
    "指标",
)

TROUBLESHOOTING_PHRASES = (
    "为什么",
    "怎么回事",
    "异常",
    "失败",
    "报错",
    "查一下",
    "看一下",
    "帮我看",
)

GENERIC_TITLES = {
    DEFAULT_TITLE,
    "新的对话",
    "问题咨询",
    "普通聊天",
    "聊天",
    "问候",
    "你好",
}


def _normalize_for_check(message: str) -> str:
    text = message.strip().lower()
    return re.sub(
        r"[\s,，.。!！?？:：;；'\"“”‘’《》【】\[\]()（）\-_/\\]+",
        "",
        text,
    )


def is_title_worthy(message: str) -> bool:
    """Return whether a user message carries enough intent to title a chat."""
    text = message.strip()
    if not text:
        return False

    normalized = _normalize_for_check(text)
    if normalized in LOW_INFO_MESSAGES:
        return False
    if normalized.startswith("你是") and len(normalized) <= 8:
        return False

    lower = text.lower()
    if any(keyword in lower for keyword in OPS_KEYWORDS):
        return True
    if any(phrase in lower for phrase in TROUBLESHOOTING_PHRASES):
        return True

    chinese_chars = len(re.findall(r"[\u4e00-\u9fff]", text))
    ascii_words = len(re.findall(r"[a-zA-Z0-9_./:-]+", text))
    return chinese_chars >= 8 or ascii_words >= 4


def _clean_message(message: str) -> str:
    text = message.strip()
    text = re.sub(
        r"^(麻烦|请|帮我|帮忙|能不能|可以|麻烦你)?\s*(查一下|看一下|看下|查查|看看)?",
        "",
        text,
    )
    text = re.sub(r"[?？!！。.\s]+$", "", text)
    return text.strip()


def _clamp_title(title: str) -> str:
    title = re.sub(r"\s+", " ", title).strip(" -_，,。.!！?？:：；;")
    if len(title) <= MAX_TITLE_LENGTH:
        return title
    return title[:MAX_TITLE_LENGTH].rstrip(" -_，,。.!！?？:：；;")


def _extract_subject(text: str) -> str | None:
    match = re.match(r"^([a-zA-Z0-9_.:-]{2,32})\s+", text)
    if match:
        return match.group(1)

    before_issue = re.split(r"为什么|怎么|指标|采集|抓取|异常|失败|报错", text, maxsplit=1)[0]
    before_issue = before_issue.strip(" ，,。.!！?？:：；;")
    if 2 <= len(before_issue) <= 12 and not re.search(
        r"帮我|请|查一下|看一下",
        before_issue,
    ):
        return before_issue
    return None


def generate_rule_title(message: str) -> str | None:
    """Generate a deterministic first title without calling the LLM."""
    if not is_title_worthy(message):
        return None

    text = _clean_message(message)
    lower = text.lower()

    if ("服务器" in text or "主机" in text) and (
        "资源" in text
        or "cpu" in lower
        or "内存" in text
        or "磁盘" in text
        or "负载" in text
    ):
        if "异常" in text or "哪台" in text or "高" in text:
            return "服务器资源异常"
        return "服务器资源查询"

    if "告警" in text:
        if "最近" in text or "今天" in text or "近期" in text:
            return "近期告警查询"
        return "告警查询"

    if "巡检" in text:
        return "系统巡检"

    if "指标" in text and ("采集" in text or "抓取" in text or "不到" in text):
        subject = _extract_subject(text)
        if subject:
            return _clamp_title(f"{subject} 指标采集排查")
        return "指标采集排查"

    if "prometheus" in lower:
        return "Prometheus 排查"

    if "容器" in text or "docker" in lower:
        if any(word in text for word in ("异常", "失败", "报错")):
            return "容器问题排查"
        return "容器查询"

    if "部署" in text:
        if any(word in text for word in ("失败", "报错", "异常")):
            return "应用部署排查"
        return "应用部署"

    return _clamp_title(text)


def maybe_set_rule_title(db: Session, conversation_id: int, user_message: str) -> str | None:
    conv = db.get(Conversation, conversation_id)
    if not conv or conv.title != DEFAULT_TITLE:
        return None

    rule_title = generate_rule_title(user_message)
    if not rule_title:
        return None

    conv.title = rule_title
    db.flush()
    return rule_title


def sanitize_llm_title(text: str) -> str | None:
    title = (text or "").strip().splitlines()[0].strip()
    should_rule_normalize = bool(
        re.match(r"^(标题|会话标题|主题)\s*[:：]\s*", title)
    ) or any(marker in title for marker in ("?", "？", "今天", "最近", "哪台"))
    title = re.sub(r"^(标题|会话标题|主题)\s*[:：]\s*", "", title)
    title = title.strip(" `*_#\"'“”‘’《》【】[]()（）")
    title = re.sub(r"[?？!！。.\s]+$", "", title)

    rule_title = generate_rule_title(title) if should_rule_normalize else None
    if rule_title:
        title = rule_title

    title = _clamp_title(title)
    if not title or title in GENERIC_TITLES:
        return None
    if _normalize_for_check(title) in LOW_INFO_MESSAGES:
        return None
    if len(title) < 3:
        return None
    return title


async def _generate_llm_title(
    db: Session,
    user_message: str,
    assistant_text: str | None = None,
) -> str | None:
    from app.core.settings import get_llm_config
    from app.services.ai.llm_client import LLMClient

    config = get_llm_config(db)
    if not config["base_url"] or not config["api_key"] or not config["model"]:
        return None

    client = LLMClient(
        config["base_url"],
        config["api_key"],
        config["model"],
        api_mode=config.get("api_mode") or "chat_completions",
        reasoning_effort=config.get("reasoning_effort") or "",
        temperature=0.2,
        max_tokens=64,
        top_p=0.8,
    )
    prompt = "请为这段运维平台对话生成一个 4 到 12 个字的中文短标题。只输出标题，不要解释。"
    content = f"用户问题：{user_message.strip()}"
    if assistant_text:
        content += f"\n助手回答摘要：{assistant_text.strip()[:300]}"

    chunks: list[str] = []
    async for event in client.chat_stream(
        [
            {"role": "system", "content": prompt},
            {"role": "user", "content": content},
        ],
        tools=None,
    ):
        if event["type"] == "text":
            chunks.append(event["content"])
        elif event["type"] == "done":
            break

    return sanitize_llm_title("".join(chunks))


TitleGenerator = Callable[[Session, str, str | None], Awaitable[str | None]]


async def refine_conversation_title_task(
    conversation_id: int,
    user_message: str,
    *,
    rule_title: str | None = None,
    assistant_text: str | None = None,
    session_factory: Callable[[], Session] = SessionLocal,
    title_generator: TitleGenerator | None = None,
) -> None:
    """Refine a title in a background task using an isolated DB session."""
    db = session_factory()
    try:
        conv = db.get(Conversation, conversation_id)
        if not conv or conv.title not in {DEFAULT_TITLE, rule_title}:
            return

        generator = title_generator or _generate_llm_title
        llm_title = await generator(db, user_message, assistant_text)
        if not llm_title:
            return

        conv = db.get(Conversation, conversation_id)
        if not conv or conv.title not in {DEFAULT_TITLE, rule_title}:
            return
        conv.title = llm_title
        db.commit()
    except Exception:
        db.rollback()
        logger.exception("Failed to refine AI conversation title")
    finally:
        db.close()


def schedule_title_refinement(
    conversation_id: int,
    user_message: str,
    *,
    rule_title: str | None = None,
    assistant_text: str | None = None,
) -> None:
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        logger.debug("No running event loop; skip AI title refinement scheduling")
        return

    loop.create_task(
        refine_conversation_title_task(
            conversation_id,
            user_message,
            rule_title=rule_title,
            assistant_text=assistant_text,
        )
    )
