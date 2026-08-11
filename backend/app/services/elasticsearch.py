"""Elasticsearch 日志检索服务。

封装对 ES `_search` API 的调用。所有查询在后端构造：
前端只传白名单内的过滤参数，不接触原始 Query DSL，避免注入与越权。

字段约定基于 Filebeat 8.x ECS 映射（含 add_kubernetes_metadata 处理器），
对非 K8s 的 Docker/主机日志做候选字段兜底。
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

import httpx
from sqlalchemy.orm import Session

from app.core.settings import (
    get_elasticsearch_index,
    get_elasticsearch_password,
    get_elasticsearch_url,
    get_elasticsearch_username,
)

logger = logging.getLogger(__name__)

_TIMEOUT = httpx.Timeout(connect=5, read=15, write=5, pool=5)

# 单次查询上限保护
MAX_SIZE = 500
MAX_WINDOW = 10_000  # offset + size 上限（对应 ES max_result_window）

# 过滤维度 → ES 候选字段（任一命中即算匹配，兼容 K8s / 非 K8s 日志）
_FIELD_CANDIDATES: dict[str, list[str]] = {
    "namespace": ["kubernetes.namespace"],
    "pod": ["kubernetes.pod.name"],
    "container": ["kubernetes.container.name", "container.name"],
    "host": ["host.name"],
    "level": ["log.level", "level"],
}
_MESSAGE_FIELD = "message"


class ElasticsearchError(Exception):
    """ES 访问异常，detail 为面向用户的中文提示。"""

    def __init__(self, detail: str):
        super().__init__(detail)
        self.detail = detail


def _conn(db: Session) -> tuple[str, str, httpx.BasicAuth | None]:
    """读取 ES 连接配置；未配置时抛出友好错误。"""
    base_url = get_elasticsearch_url(db)
    if not base_url:
        raise ElasticsearchError("Elasticsearch 未配置，请先到「系统管理 → 集成中心」填写服务地址")
    index = get_elasticsearch_index(db)
    username = get_elasticsearch_username(db)
    password = get_elasticsearch_password(db)
    auth = httpx.BasicAuth(username, password) if username else None
    return base_url, index, auth


def _explain_http_error(exc: Exception) -> str:
    if isinstance(exc, httpx.TimeoutException):
        return "Elasticsearch 查询超时，请检查服务负载或缩小时间范围"
    if isinstance(exc, httpx.ConnectError):
        return "无法连接 Elasticsearch，请检查服务地址与网络"
    if isinstance(exc, httpx.HTTPStatusError):
        status = exc.response.status_code
        if status in (401, 403):
            return "Elasticsearch 认证失败，请检查用户名/密码"
        if status == 404:
            return "未找到匹配的日志索引，请检查索引模式配置"
        return f"Elasticsearch 返回错误（HTTP {status}）"
    return f"日志查询失败: {exc}"


def _term_any(fields: list[str], value: str) -> dict[str, Any]:
    """精确匹配任一候选字段（keyword 字段）。"""
    if len(fields) == 1:
        return {"term": {fields[0]: value}}
    return {
        "bool": {
            "should": [{"term": {f: value}} for f in fields],
            "minimum_should_match": 1,
        }
    }


def parse_time(value: str | None) -> str | None:
    """校验并规范化时间参数（ISO 8601），非法输入抛错而不是悄悄忽略。"""
    if not value:
        return None
    text = value.strip()
    if not text:
        return None
    try:
        dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        raise ElasticsearchError(f"时间格式无效: {value}（应为 ISO 8601）")
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat()


def build_query(
    *,
    keyword: str = "",
    namespace: str = "",
    pod: str = "",
    container: str = "",
    host: str = "",
    level: str = "",
    start: str | None = None,
    end: str | None = None,
) -> dict[str, Any]:
    """由白名单参数构造 bool 查询。keyword 走 match_phrase（整串短语匹配）。"""
    must: list[dict[str, Any]] = []
    filters: list[dict[str, Any]] = []

    keyword = (keyword or "").strip()
    if keyword:
        must.append({"match_phrase": {_MESSAGE_FIELD: keyword}})

    for param, fields in _FIELD_CANDIDATES.items():
        value = {"namespace": namespace, "pod": pod, "container": container,
                 "host": host, "level": level}[param]
        value = (value or "").strip()
        if value:
            filters.append(_term_any(fields, value))

    start = parse_time(start)
    end = parse_time(end)
    if start or end:
        rng: dict[str, Any] = {}
        if start:
            rng["gte"] = start
        if end:
            rng["lte"] = end
        filters.append({"range": {"@timestamp": rng}})

    return {"bool": {"must": must, "filter": filters}}


def _normalize_hit(hit: dict[str, Any]) -> dict[str, Any]:
    """把 ECS 结构的 _source 压平成前端直接可用的结构。"""
    src = hit.get("_source") or {}
    k8s = src.get("kubernetes") or {}
    return {
        "id": hit.get("_id"),
        "index": hit.get("_index"),
        "timestamp": src.get("@timestamp"),
        "message": src.get(_MESSAGE_FIELD) or "",
        "namespace": k8s.get("namespace"),
        "pod": (k8s.get("pod") or {}).get("name"),
        "container": (k8s.get("container") or {}).get("name")
        or (src.get("container") or {}).get("name"),
        "host": (src.get("host") or {}).get("name"),
        "level": (src.get("log") or {}).get("level") or src.get("level"),
    }


async def _search(db: Session, payload: dict[str, Any]) -> dict[str, Any]:
    base_url, index, auth = _conn(db)
    url = f"{base_url}/{index}/_search"
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT, auth=auth) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            return resp.json()
    except ElasticsearchError:
        raise
    except Exception as exc:
        logger.warning("Elasticsearch query failed: %s", exc)
        raise ElasticsearchError(_explain_http_error(exc)) from exc


async def search_logs(
    db: Session,
    *,
    keyword: str = "",
    namespace: str = "",
    pod: str = "",
    container: str = "",
    host: str = "",
    level: str = "",
    start: str | None = None,
    end: str | None = None,
    size: int = 100,
    offset: int = 0,
) -> dict[str, Any]:
    """日志检索：关键字 + 白名单维度过滤 + 时间范围，按时间倒序。"""
    size = max(1, min(size, MAX_SIZE))
    offset = max(0, offset)
    if offset + size > MAX_WINDOW:
        raise ElasticsearchError(f"翻页过深（offset+size 超过 {MAX_WINDOW}），请缩小时间范围或增加过滤条件")

    query = build_query(
        keyword=keyword, namespace=namespace, pod=pod, container=container,
        host=host, level=level, start=start, end=end,
    )
    payload = {
        "size": size,
        "from": offset,
        "query": query,
        "sort": [{"@timestamp": {"order": "desc"}}],
        "track_total_hits": True,
    }
    data = await _search(db, payload)
    hits = data.get("hits") or {}
    total = (hits.get("total") or {}).get("value", 0)
    return {
        "total": total,
        "items": [_normalize_hit(h) for h in hits.get("hits") or []],
    }


def _auto_interval(start: str | None, end: str | None, buckets: int = 40) -> str:
    """按时间范围自动选择直方图粒度。"""
    s = parse_time(start)
    e = parse_time(end)
    if s and e:
        try:
            span = (datetime.fromisoformat(e) - datetime.fromisoformat(s)).total_seconds()
        except ValueError:
            span = 0
    else:
        span = 0
    if span <= 0:
        return "1m"
    step = span / max(buckets, 1)
    for candidate, seconds in (
        ("10s", 10), ("30s", 30), ("1m", 60), ("5m", 300), ("10m", 600),
        ("30m", 1800), ("1h", 3600), ("3h", 10800), ("6h", 21600),
        ("12h", 43200), ("1d", 86400),
    ):
        if step <= seconds:
            return candidate
    return "7d"


async def log_histogram(
    db: Session,
    *,
    keyword: str = "",
    namespace: str = "",
    pod: str = "",
    container: str = "",
    host: str = "",
    level: str = "",
    start: str | None = None,
    end: str | None = None,
) -> dict[str, Any]:
    """日志量时间直方图（与检索条件联动）。"""
    query = build_query(
        keyword=keyword, namespace=namespace, pod=pod, container=container,
        host=host, level=level, start=start, end=end,
    )
    interval = _auto_interval(start, end)
    payload = {
        "size": 0,
        "query": query,
        "aggs": {
            "timeline": {
                "date_histogram": {
                    "field": "@timestamp",
                    "fixed_interval": interval,
                    "min_doc_count": 0,
                }
            }
        },
    }
    data = await _search(db, payload)
    buckets = ((data.get("aggregations") or {}).get("timeline") or {}).get("buckets") or []
    return {
        "interval": interval,
        "buckets": [
            {"key": b.get("key_as_string"), "count": b.get("doc_count", 0)}
            for b in buckets
        ],
    }


async def log_filter_options(
    db: Session,
    *,
    start: str | None = None,
    end: str | None = None,
) -> dict[str, Any]:
    """聚合可选过滤维度（namespace / host / level），供前端筛选下拉框。"""
    query = build_query(start=start, end=end)
    payload = {
        "size": 0,
        "query": query,
        "aggs": {
            "namespaces": {"terms": {"field": "kubernetes.namespace", "size": 100}},
            "hosts": {"terms": {"field": "host.name", "size": 100}},
            "levels": {"terms": {"field": "log.level", "size": 20}},
        },
    }
    data = await _search(db, payload)
    aggs = data.get("aggregations") or {}

    def _keys(name: str) -> list[str]:
        return [b.get("key") for b in (aggs.get(name) or {}).get("buckets") or [] if b.get("key")]

    return {
        "namespaces": _keys("namespaces"),
        "hosts": _keys("hosts"),
        "levels": _keys("levels"),
    }
