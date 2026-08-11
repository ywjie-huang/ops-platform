"""日志检索 API — Elasticsearch 数据源的统一日志查询入口。

所有 ES 查询在后端白名单构造，前端不接触原始 Query DSL。
错误以 code=1 + 中文 msg 返回（HTTP 200），与 test-connection 风格一致，
便于前端直接展示友好提示而不触发拦截器。
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import api_permission_required
from app.db.database import get_db
from app.models.user import User
from app.services.elasticsearch import (
    ElasticsearchError,
    log_filter_options,
    log_histogram,
    search_logs,
)

router = APIRouter(prefix="/logs", tags=["日志检索"])


@router.get("/search")
async def api_search_logs(
    keyword: str = Query("", description="日志内容关键字（短语匹配）"),
    namespace: str = Query("", description="K8s 命名空间"),
    pod: str = Query("", description="Pod 名称"),
    container: str = Query("", description="容器名称"),
    host: str = Query("", description="主机名"),
    level: str = Query("", description="日志级别（如 error / warn / info）"),
    start: str | None = Query(None, description="开始时间（ISO 8601）"),
    end: str | None = Query(None, description="结束时间（ISO 8601）"),
    size: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    _: User = Depends(api_permission_required("monitoring.view")),
):
    """日志检索：关键字 + 维度过滤 + 时间范围，按时间倒序。"""
    try:
        data = await search_logs(
            db, keyword=keyword, namespace=namespace, pod=pod, container=container,
            host=host, level=level, start=start, end=end, size=size, offset=offset,
        )
    except ElasticsearchError as e:
        return {"code": 1, "msg": e.detail, "data": None}
    return {"code": 0, "data": data}


@router.get("/histogram")
async def api_log_histogram(
    keyword: str = Query(""),
    namespace: str = Query(""),
    pod: str = Query(""),
    container: str = Query(""),
    host: str = Query(""),
    level: str = Query(""),
    start: str | None = Query(None),
    end: str | None = Query(None),
    db: Session = Depends(get_db),
    _: User = Depends(api_permission_required("monitoring.view")),
):
    """日志量时间直方图（与检索条件联动）。"""
    try:
        data = await log_histogram(
            db, keyword=keyword, namespace=namespace, pod=pod, container=container,
            host=host, level=level, start=start, end=end,
        )
    except ElasticsearchError as e:
        return {"code": 1, "msg": e.detail, "data": None}
    return {"code": 0, "data": data}


@router.get("/filter-options")
async def api_log_filter_options(
    start: str | None = Query(None),
    end: str | None = Query(None),
    db: Session = Depends(get_db),
    _: User = Depends(api_permission_required("monitoring.view")),
):
    """聚合可选过滤维度（namespace / host / level），供筛选下拉框。"""
    try:
        data = await log_filter_options(db, start=start, end=end)
    except ElasticsearchError as e:
        return {"code": 1, "msg": e.detail, "data": None}
    return {"code": 0, "data": data}
