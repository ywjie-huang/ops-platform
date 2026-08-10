"""
Alertmanager 查询服务
封装对 Alertmanager HTTP API v2 的调用。
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from datetime import datetime

from app.core.config import CHINA_TZ
from typing import Any

import httpx
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.config import ALERTMANAGER_URL, PROMETHEUS_URL
from app.core.settings import get_alertmanager_url, get_prometheus_url
from app.models.alert_event import AlertEvent

logger = logging.getLogger(__name__)

_TIMEOUT = httpx.Timeout(connect=5, read=10, write=5, pool=5)


async def check_alertmanager_health(db=None) -> bool:
    """检查 Alertmanager 是否可达。"""
    am_url = get_alertmanager_url(db) if db else ALERTMANAGER_URL
    if not am_url:
        return False
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
    if not am_url:
        return []
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
    if not prom_url:
        return []

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


# ─── 规则关联主机 ────────────────────────────────────────────

_rules_hosts_cache: dict[tuple[str, ...], tuple[float, dict[str, list[dict]]]] = {}
_rules_hosts_cache_ts: float = 0
_RULES_HOSTS_CACHE_TTL = 30  # 30 秒缓存


def _normalize_rule_names(rule_names: list[str] | None) -> list[str]:
    return list(dict.fromkeys(name for name in (rule_names or []) if name))


async def get_rules_hosts(db=None, rule_names: list[str] | None = None) -> dict[str, list[dict]]:
    """查询每条告警规则关联的主机列表。

    流程：获取规则 → 并发执行每条规则的 PromQL → 提取 instance 标签 → 匹配资产。
    返回 { rule_name: [{ id, name, ip }, ...] } 映射。
    """
    global _rules_hosts_cache, _rules_hosts_cache_ts
    requested_names = _normalize_rule_names(rule_names)
    cache_key = tuple(sorted(requested_names))
    now = time.time()
    cached = _rules_hosts_cache.get(cache_key)
    if cached and (now - cached[0]) < _RULES_HOSTS_CACHE_TTL:
        return cached[1]

    full_cached = _rules_hosts_cache.get(())
    if requested_names and full_cached and (now - full_cached[0]) < _RULES_HOSTS_CACHE_TTL:
        return {name: full_cached[1].get(name, []) for name in requested_names}

    rules = await get_rules(db)
    if requested_names:
        requested_set = set(requested_names)
        rules = [rule for rule in rules if rule.get("name") in requested_set]
    if not rules:
        result = {name: [] for name in requested_names}
        _rules_hosts_cache[cache_key] = (time.time(), result)
        _rules_hosts_cache_ts = time.time()
        return result

    prom_url = get_prometheus_url(db) if db else PROMETHEUS_URL

    # 发现 Prometheus 实例 → 资产匹配
    from app.services.prometheus import discover_instances
    instances = await discover_instances(prom_url)
    # 构建反向映射：prometheus_instance_label → clean_ip
    instance_to_ip: dict[str, str] = {}
    for clean_addr, info in instances.items():
        inst_label = info["instance"] if isinstance(info, dict) else str(info)
        instance_to_ip.setdefault(inst_label, clean_addr)

    # 查询所有资产，构建 ip → asset 映射
    from app.models.asset import Asset
    if db:
        assets = list(db.execute(select(Asset)).scalars().all())
    else:
        assets = []
    ip_to_asset: dict[str, Asset] = {}
    for asset in assets:
        ip_to_asset[asset.ip_address] = asset
        if asset.name:
            ip_to_asset[asset.name] = asset

    query_timeout = httpx.Timeout(connect=3, read=3, write=3, pool=3)
    query_semaphore = asyncio.Semaphore(10)

    async def _query_rule_hosts(client: httpx.AsyncClient, rule: dict) -> list[dict]:
        """执行单条规则的 PromQL，提取关联主机。"""
        query = rule.get("query", "")
        if not query:
            return []

        try:
            async with query_semaphore:
                resp = await client.get(
                    f"{prom_url}/api/v1/query",
                    params={"query": query},
                )
                resp.raise_for_status()
                data = resp.json()
                if data.get("status") != "success":
                    return []

                results = data.get("data", {}).get("result", [])
                # 提取所有不重复的 instance 标签
                seen_instances: set[str] = set()
                seen_asset_ids: set[int] = set()
                matched_hosts: list[dict] = []

                for item in results:
                    metric = item.get("metric", {})
                    inst = metric.get("instance", "")
                    if not inst or inst in seen_instances:
                        continue
                    seen_instances.add(inst)

                    # 尝试匹配资产
                    # 1. 直接用 instance 标签查
                    clean_ip = inst.split(":")[0] if ":" in inst else inst
                    asset = ip_to_asset.get(clean_ip) or ip_to_asset.get(inst)

                    # 2. 通过 instance_to_ip 反查
                    if not asset:
                        real_ip = instance_to_ip.get(inst, "")
                        if real_ip:
                            asset = ip_to_asset.get(real_ip)

                    if asset and asset.id not in seen_asset_ids:
                        seen_asset_ids.add(asset.id)
                        matched_hosts.append({
                            "id": asset.id,
                            "name": asset.name,
                            "ip": asset.ip_address,
                        })

                return matched_hosts
        except Exception as e:
            logger.warning("Failed to query rule '%s': %s", rule.get("name"), e)
            return []

    # 并发查询所有规则
    async with httpx.AsyncClient(timeout=query_timeout) as client:
        tasks = [_query_rule_hosts(client, rule) for rule in rules]
        host_lists = await asyncio.gather(*tasks)

    result: dict[str, list[dict]] = {name: [] for name in requested_names}
    for rule, hosts in zip(rules, host_lists):
        result[rule["name"]] = hosts

    _rules_hosts_cache[cache_key] = (time.time(), result)
    _rules_hosts_cache_ts = time.time()
    return result


# ─── Webhook 处理 ────────────────────────────────────────────

def _parse_iso(ts: str) -> datetime | None:
    """解析 ISO 8601 时间字符串。"""
    if not ts or ts in ("0001-01-01T00:00:00Z", "0001-01-01T00:00:00"):
        return None
    try:
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00")).astimezone(CHINA_TZ).replace(tzinfo=None)
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
