import asyncio

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.container import ContainerCluster, DockerContainer
from app.services.ai.tools import handle_query_containers, handle_query_logs


def test_query_containers_matches_docker_host_by_endpoint_ip():
    engine = create_engine("sqlite:///:memory:")
    ContainerCluster.__table__.create(engine)
    DockerContainer.__table__.create(engine)
    SessionLocal = sessionmaker(bind=engine)

    db = SessionLocal()
    try:
        host = ContainerCluster(
            name="docker-prod-01",
            provider="docker",
            endpoint="172.16.100.1:9001",
            host_ip="",
        )
        db.add(host)
        db.flush()
        db.add(
            DockerContainer(
                host_id=host.id,
                container_id="abc123def456",
                name="web",
                image="nginx:latest",
                status="running",
            )
        )
        db.commit()

        result = handle_query_containers(db, {"host_ip": "172.16.100.1"})

        assert "web" in result
        assert "nginx:latest" in result
    finally:
        db.close()


def test_query_containers_matches_docker_host_by_http_endpoint_ip():
    engine = create_engine("sqlite:///:memory:")
    ContainerCluster.__table__.create(engine)
    DockerContainer.__table__.create(engine)
    SessionLocal = sessionmaker(bind=engine)

    db = SessionLocal()
    try:
        host = ContainerCluster(
            name="docker-prod-01",
            provider="docker",
            endpoint="http://172.16.100.1:9001",
            host_ip="",
        )
        db.add(host)
        db.flush()
        db.add(
            DockerContainer(
                host_id=host.id,
                container_id="abc123def456",
                name="api",
                image="app:latest",
                status="running",
            )
        )
        db.commit()

        result = handle_query_containers(db, {"host_ip": "172.16.100.1"})

        assert "api" in result
        assert "app:latest" in result
    finally:
        db.close()


# ─── query_logs 测试 ───────────────────────────────────────
# handler 内部 `from app.services.elasticsearch import search_logs` 延迟导入，
# 因此 mock 目标是 `app.services.elasticsearch.search_logs`（源头模块）。


def _run_query_logs(monkeypatch, args, captured=None):
    """调用 handle_query_logs 并捕获传给底层 search_logs 的参数。"""
    async def fake_search_logs(db, **kwargs):
        if captured is not None:
            captured.update(kwargs)
            captured["db"] = db
        return _fake_es_response()

    monkeypatch.setattr(
        "app.services.elasticsearch.search_logs", fake_search_logs
    )
    return asyncio.run(handle_query_logs(db=None, args=args))


def _fake_es_response():
    """模拟 search_logs 的返回结构。"""
    return {
        "total": 1,
        "items": [
            {
                "id": "abc",
                "index": "filebeat-7d",
                "timestamp": "2026-08-11T14:23:01+08:00",
                "message": "java.lang.OutOfMemoryError: Java heap space",
                "namespace": "prod",
                "pod": "api-7d9f",
                "container": "server",
                "host": "node-1",
                "level": "error",
            }
        ],
    }


def test_query_logs_normal_case_includes_fields_and_url(monkeypatch):
    captured = {}
    result = _run_query_logs(monkeypatch, {
        "pod": "api-7d9f", "level": "error", "minutes": 60, "limit": 10,
    }, captured)

    # 过滤参数正确传到底层
    assert captured["pod"] == "api-7d9f"
    assert captured["level"] == "error"
    assert captured["container"] == ""
    assert captured["size"] == 10
    # 时间换算为 ISO（start/end，非 minutes）
    assert captured["start"] != captured["end"]
    assert "T" in captured["start"] and "T" in captured["end"]
    # 输出含关键字段
    assert "1" in result  # total
    assert "OutOfMemoryError" in result
    assert "prod/api-7d9f/server" in result  # namespace/pod/container 拼接
    # 末尾带日志检索页 URL（页面认的 key，无 minutes）
    assert "/monitoring/logs?" in result
    assert "pod=api-7d9f" in result
    assert "level=error" in result
    assert "start=" in result and "end=" in result
    assert "minutes=" not in result


def test_query_logs_empty_results_gives_hint(monkeypatch):
    async def fake_search_logs(db, **kwargs):
        return {"total": 0, "items": []}

    monkeypatch.setattr(
        "app.services.elasticsearch.search_logs", fake_search_logs
    )
    result = asyncio.run(
        handle_query_logs(db=None, args={"minutes": 30})
    )
    assert "无匹配日志" in result
    assert "扩大 minutes" in result


def test_query_logs_es_not_configured_returns_detail(monkeypatch):
    """ES 未配置（或任何 ES 异常）：handler 转述 e.detail，不抛异常。"""
    from app.services.elasticsearch import ElasticsearchError

    async def fake_search_logs(db, **kwargs):
        raise ElasticsearchError(
            "Elasticsearch 未配置，请先到「系统管理 → 集成中心」填写服务地址"
        )

    monkeypatch.setattr(
        "app.services.elasticsearch.search_logs", fake_search_logs
    )
    result = asyncio.run(handle_query_logs(db=None, args={}))
    assert "未配置" in result
    assert "集成中心" in result


def test_query_logs_limit_clamped_to_max(monkeypatch):
    """limit 超过 20 被钳制；底层收到的 size 不超过 20。"""
    captured = {}
    _run_query_logs(monkeypatch, {"limit": 50}, captured)
    assert captured["size"] == 20


def test_query_logs_minutes_clamped_to_max(monkeypatch):
    """minutes 超过 1440 被钳制到 1440。"""
    from datetime import timedelta

    captured = {}
    _run_query_logs(monkeypatch, {"minutes": 99999}, captured)
    # start 与 end 间隔应为 1440 分钟（24 小时）
    from datetime import datetime
    start = datetime.fromisoformat(captured["start"])
    end = datetime.fromisoformat(captured["end"])
    assert abs((end - start).total_seconds() - 1440 * 60) < 5


def test_query_logs_message_truncated(monkeypatch):
    """超过 300 字符的 message 被截断。"""
    long_msg = "X" * 500

    async def fake_search_logs(db, **kwargs):
        return {
            "total": 1,
            "items": [
                {
                    "timestamp": "2026-08-11T14:23:01+08:00",
                    "message": long_msg,
                    "namespace": "prod",
                    "pod": "api",
                    "container": None,
                    "host": None,
                    "level": "error",
                }
            ],
        }

    monkeypatch.setattr(
        "app.services.elasticsearch.search_logs", fake_search_logs
    )
    result = asyncio.run(handle_query_logs(db=None, args={}))
    # 原文 500 字符不应完整出现，但前 300 + 省略号应出现
    assert "X" * 500 not in result
    assert "X" * 300 in result
    assert "..." in result
