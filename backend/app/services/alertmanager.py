"""
Alertmanager 查询服务
封装对 Alertmanager HTTP API v2 的调用。
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any

import httpx
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.config import ALERTMANAGER_URL
from app.core.settings import get_alertmanager_url, get_prometheus_url
from app.models.alert_event import AlertEvent

logger = logging.getLogger(__name__)

_TIMEOUT = httpx.Timeout(connect=5, read=10, write=5, pool=5)


async def check_alertmanager_health(db=None) -> bool:
    """检查 Alertmanager 是否可达。"""
    am_url = get_alertmanager_url(db) if db else ALERTMANAGER_URL
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.get(f"{am_url}/api/v2/status")
            return resp.status_code == 200
    except Exception as e:
        logger.warning('Alertmanager health check failed: %s', e)
        return False


async def get_alerts(db=None) -> list[dict[str, Any]]:
    """获取当前活跃告警列表。"""
    am_url = get_alertmanager_url(db) if db else ALERTMANAGER_URL
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.get(f"{am_url}/api/v2/alerts")
            resp.raise_for_status()
            raw = resp.json()
            return [
                {
                    "fingerprint": a.get("fingerprint", ""),
                    "labels": a.get("labels", {}),
                    "annotations": a.get("annotations", {}),
                    "status": a.get("status", {}),
                    "starts_at": a.get("startsAt", ""),
                    "ends_at": a.get("endsAt", ""),
                    "generator_url": a.get("generatorURL", ""),
                }
                for a in raw
            ]
    except Exception as e:
        logger.error("Failed to get alerts from Alertmanager: %s", e)
        return []


async def get_rules(db=None) -> list[dict[str, Any]]:
    """获取告警规则列表（来自 Prometheus /api/v1/rules，Alertmanager 本身不存规则）。"""
    prom_url = get_prometheus_url(db) if db else PROMETHEUS_URL

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.get(f"{prom_url}/api/v1/rules")
            resp.raise_for_status()
            data = resp.json()
            if data.get("status") != "success":
                return []

            results = []
            for group in data.get("data", {}).get("groups", []):
                for rule in group.get("rules", []):
                    if rule.get("type") != "alerting":
                        continue
                    results.append({
                        "name": rule.get("name", ""),
                        "query": rule.get("query", ""),
                        "duration": rule.get("duration", 0),
                        "state": rule.get("state", "inactive"),
                        "labels": rule.get("labels", {}),
                        "annotations": rule.get("annotations", {}),
                        "health": rule.get("health", ""),
                        "last_error": rule.get("lastError", ""),
                        "group_name": group.get("name", ""),
                        "file": group.get("file", ""),
                    })
            return results
    except Exception as e:
        logger.error("Failed to get rules: %s", e)
        return []


# ─── Webhook 处理 ────────────────────────────────────────────

def _parse_iso(ts: str) -> datetime | None:
    """解析 ISO 8601 时间字符串。"""
    if not ts or ts in ("0001-01-01T00:00:00Z", "0001-01-01T00:00:00"):
        return None
    try:
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00")).replace(tzinfo=None)
        if dt.year < 2000:
            return None
        return dt
    except Exception as e:
        logger.warning('Timestamp parse failed: %s', e)
        return None


def _extract_alert_value(annotations: dict, labels: dict) -> str:
    """从 annotations/labels 中提取告警值。"""
    # 1. 直接从 annotations 中找 value 相关字段
    for key in ("value", "val", "current_value", "threshold_value"):
        if annotations.get(key):
            return str(annotations[key])
    # 2. 从 description/summary 中提取百分比或数值
    import re
    for field in ("description", "summary"):
        text = annotations.get(field, "")
        # 匹配 "当前使用率16.35%" "16.35%" "值为 85" 等模式
        m = re.search(r'(?:当前[使用率值]*|当前|值为?|:)\s*(\d+\.?\d*\s*%?)', text)
        if m:
            return m.group(1).strip()
        # 匹配任意 百分比
        m = re.search(r'(\d+\.\d+\s*%)', text)
        if m:
            return m.group(1)
    return ""


def _calc_firing_count(db: Session, fingerprint: str) -> int:
    """根据 fingerprint 统计连续触发次数。"""
    if not fingerprint:
        return 1
    from sqlalchemy import func
    count = db.scalar(
        select(func.count(AlertEvent.id))
        .where(AlertEvent.fingerprint == fingerprint)
        .where(AlertEvent.status == "firing")
    ) or 0
    return count + 1  # +1 是当前这条


def process_webhook(db: Session, payload: list[dict]) -> int:
    """处理 Alertmanager webhook 推送，返回新增事件数。"""
    logger.info("Webhook received %d alerts", len(payload))
    count = 0
    for alert in payload:
        logger.info("Webhook raw alert: %s", json.dumps(alert, ensure_ascii=False, default=str))
        fingerprint = alert.get("fingerprint", "")
        status_info = alert.get("status", {})
        status = status_info.get("state", "firing") if isinstance(status_info, dict) else str(status_info)
        labels = alert.get("labels", {})
        annotations = alert.get("annotations", {})
        logger.info("Parsed labels: %s", json.dumps(labels, ensure_ascii=False))
        logger.info("Parsed annotations: %s", json.dumps(annotations, ensure_ascii=False))

        event = AlertEvent(
            fingerprint=fingerprint,
            alert_name=labels.get("alertname", ""),
            severity=labels.get("severity", "warning"),
            status=status,
            alert_value=_extract_alert_value(annotations, labels),
            summary=annotations.get("summary", ""),
            description=annotations.get("description", ""),
            instance=labels.get("instance", ""),
            job=labels.get("job", ""),
            firing_count=_calc_firing_count(db, fingerprint),
            generator_url=alert.get("generatorURL", ""),
            raw_labels=json.dumps(labels, ensure_ascii=False),
            raw_annotations=json.dumps(annotations, ensure_ascii=False),
            starts_at=_parse_iso(alert.get("startsAt", "")),
            ends_at=_parse_iso(alert.get("endsAt", "")),
        )
        db.add(event)
        count += 1

    db.commit()
    return count


def list_alert_events(
    db: Session,
    *,
    keyword: str = "",
    severity: str = "",
    status: str = "",
    limit: int = 100,
    offset: int = 0,
) -> tuple[list[AlertEvent], int]:
    """查询告警事件列表，返回 (items, total)。"""
    stmt = select(AlertEvent)
    count_stmt = select(AlertEvent)

    keyword = keyword.strip()
    severity = severity.strip()
    status = status.strip()

    if keyword:
        like_val = f"%{keyword}%"
        cond = or_(
            AlertEvent.alert_name.ilike(like_val),
            AlertEvent.summary.ilike(like_val),
            AlertEvent.instance.ilike(like_val),
        )
        stmt = stmt.where(cond)
        count_stmt = count_stmt.where(cond)
    if severity:
        stmt = stmt.where(AlertEvent.severity == severity)
        count_stmt = count_stmt.where(AlertEvent.severity == severity)
    if status:
        stmt = stmt.where(AlertEvent.status == status)
        count_stmt = count_stmt.where(AlertEvent.status == status)

    from sqlalchemy import func
    total = db.scalar(select(func.count()).select_from(count_stmt.subquery())) or 0

    stmt = stmt.order_by(AlertEvent.id.desc()).offset(offset).limit(limit)
    items = list(db.scalars(stmt).all())
    return items, total
