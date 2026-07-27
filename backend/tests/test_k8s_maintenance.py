from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from starlette.requests import Request

from app.api import containers as containers_api
from app.models.container import ContainerCluster
from app.services import k8s as k8s_service
from app.services.k8s import _classify_node_pods, build_kubeconfig


def _pod(
    name: str,
    *,
    phase: str = "Running",
    owner_kind: str | None = "Deployment",
    mirror: bool = False,
    empty_dir: bool = False,
) -> dict:
    metadata = {"name": name, "namespace": "default"}
    if owner_kind:
        metadata["ownerReferences"] = [{"kind": owner_kind, "controller": True}]
    if mirror:
        metadata["annotations"] = {"kubernetes.io/config.mirror": "mirror-id"}
    volumes = [{"name": "cache", "emptyDir": {}}] if empty_dir else []
    return {"metadata": metadata, "spec": {"volumes": volumes}, "status": {"phase": phase}}


def test_node_maintenance_preflight_only_evicts_safe_controller_managed_pods():
    classified = _classify_node_pods([
        _pod("web-1"),
        _pod("daemon", owner_kind="DaemonSet"),
        _pod("static", mirror=True),
        _pod("job-done", phase="Succeeded"),
        _pod("standalone", owner_kind=None),
        _pod("cache", empty_dir=True),
    ])

    assert [item["name"] for item in classified["evictable"]] == ["web-1"]
    assert {item["name"] for item in classified["skipped"]} == {"daemon", "static", "job-done"}
    assert {item["name"] for item in classified["blocked"]} == {"standalone", "cache"}


def test_drain_stops_before_cordon_when_server_preflight_finds_blocking_pods(monkeypatch):
    cordon_calls: list[tuple[tuple, dict]] = []
    monkeypatch.setattr(
        k8s_service,
        "get_node_maintenance_preview",
        lambda *args, **kwargs: {
            "ok": True,
            "blocked": [{"name": "standalone", "namespace": "default", "reason": "unmanaged"}],
            "evictable": [],
            "skipped": [],
        },
    )
    monkeypatch.setattr(
        k8s_service,
        "set_node_schedulable",
        lambda *args, **kwargs: cordon_calls.append((args, kwargs)) or {"ok": True},
    )

    result = k8s_service.drain_node("https://k8s.example.com", "token", "node-01")

    assert result["ok"] is False
    assert "preview" in result
    assert cordon_calls == []


def test_kubeconfig_quotes_untrusted_cluster_values():
    content = build_kubeconfig(
        'prod "edge"',
        "https://k8s.example.com:6443",
        'token\nwith "quotes"',
    )

    assert 'name: "prod \\"edge\\""' in content
    assert 'server: "https://k8s.example.com:6443"' in content
    assert 'token: "token\\nwith \\"quotes\\""' in content
    assert "insecure-skip-tls-verify: true" in content


def _request() -> Request:
    return Request({"type": "http", "method": "GET", "headers": [], "client": ("127.0.0.1", 0)})


def _cluster_session():
    engine = create_engine("sqlite:///:memory:")
    ContainerCluster.__table__.create(engine)
    return sessionmaker(bind=engine)()


def test_kubeconfig_download_returns_attachment_without_json_token(monkeypatch):
    monkeypatch.setattr(containers_api, "write_log", lambda *args, **kwargs: None)
    db = _cluster_session()
    try:
        cluster = ContainerCluster(
            name="prod-k8s",
            provider="kubernetes",
            endpoint="https://k8s.example.com:6443",
            token="secret-token",
        )
        db.add(cluster)
        db.commit()

        response = containers_api.api_download_cluster_kubeconfig(
            cluster.name,
            request=_request(),
            db=db,
            current_user=None,
        )

        assert response.media_type.startswith("application/x-yaml")
        assert "attachment" in response.headers["content-disposition"]
        assert b"secret-token" in response.body
    finally:
        db.close()


def test_saved_connection_test_updates_cluster_status(monkeypatch):
    monkeypatch.setattr(containers_api, "write_log", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        containers_api,
        "test_connection",
        lambda endpoint, token: {"ok": True, "version": "v1.30.1"},
    )
    db = _cluster_session()
    try:
        cluster = ContainerCluster(
            name="prod-k8s",
            provider="kubernetes",
            endpoint="https://k8s.example.com:6443",
            token="secret-token",
            status="stopped",
        )
        db.add(cluster)
        db.commit()

        response = containers_api.api_test_saved_cluster_connection(
            cluster.name,
            request=_request(),
            db=db,
            current_user=None,
        )

        assert response["data"]["ok"] is True
        assert cluster.status == "running"
        assert cluster.version == "v1.30.1"
    finally:
        db.close()


def test_cordon_requires_exact_node_name_confirmation():
    try:
        containers_api.api_cordon_cluster_node(
            "prod-k8s",
            "node-01",
            containers_api.NodeCordonRequest(confirm_node="node-02"),
            request=_request(),
            db=None,
            current_user=None,
        )
        raise AssertionError("expected explicit node confirmation to be required")
    except HTTPException as exc:
        assert exc.status_code == 400
        assert "确认节点名称" in exc.detail
