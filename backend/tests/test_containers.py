from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi import HTTPException

from app.api import docker_mgmt
from app.api.docker_mgmt import _proxy_to_agent
from app.api.containers import ClusterCreate, api_create_cluster, api_get_cluster, api_list_clusters
from app.models.container import ContainerCluster, ContainerDeployment, ContainerPod
from app.services.containers import cluster_name_exists, refresh_cluster_connection_status
from app.services.docker_agent import docker_host_name_exists


def _create_container_tables(engine):
    ContainerCluster.__table__.create(engine)
    ContainerPod.__table__.create(engine)
    ContainerDeployment.__table__.create(engine)


def test_refresh_cluster_connection_status_marks_invalid_token_stopped(monkeypatch):
    engine = create_engine("sqlite:///:memory:")
    _create_container_tables(engine)
    SessionLocal = sessionmaker(bind=engine)

    def fake_test_connection(endpoint: str, token: str):
        assert endpoint == "https://k8s.example.com"
        assert token == "expired-token"
        return {"ok": False, "error": "authentication failed"}

    monkeypatch.setattr("app.services.containers.test_connection", fake_test_connection)

    db = SessionLocal()
    try:
        cluster = ContainerCluster(
            name="prod-k8s",
            provider="kubernetes",
            endpoint="https://k8s.example.com",
            token="expired-token",
            status="running",
            status_message="",
        )
        db.add(cluster)
        db.commit()

        refresh_cluster_connection_status(db, cluster)

        assert cluster.status == "stopped"
        assert cluster.status_message == "authentication failed"
    finally:
        db.close()


def test_create_cluster_without_token_saves_pending_configuration(monkeypatch):
    engine = create_engine("sqlite:///:memory:")
    _create_container_tables(engine)
    SessionLocal = sessionmaker(bind=engine)

    def fail_if_called(*args, **kwargs):
        raise AssertionError("K8s connection must not be tested without a token")

    monkeypatch.setattr("app.api.containers.test_connection", fail_if_called)
    monkeypatch.setattr("app.api.containers.get_cluster_info", fail_if_called)
    monkeypatch.setattr("app.api.containers.write_log", lambda *args, **kwargs: None)
    monkeypatch.setattr("app.api.containers.get_client_ip", lambda request: "127.0.0.1")

    db = SessionLocal()
    try:
        response = api_create_cluster(
            ClusterCreate(
                name="pending-k8s",
                endpoint="https://k8s.example.com",
                token="  ",
                description="pending credential",
            ),
            request=None,
            db=db,
            current_user=None,
        )

        assert response["data"]["status"] == "stopped"
        assert response["data"]["status_message"] == "Token is not configured"
        cluster = db.query(ContainerCluster).filter_by(name="pending-k8s").one()
        assert cluster.token == ""
    finally:
        db.close()


def test_refresh_cluster_connection_status_keeps_running_when_connection_ok(monkeypatch):
    engine = create_engine("sqlite:///:memory:")
    _create_container_tables(engine)
    SessionLocal = sessionmaker(bind=engine)

    monkeypatch.setattr(
        "app.services.containers.test_connection",
        lambda endpoint, token: {"ok": True, "version": "v1.29.0"},
    )

    db = SessionLocal()
    try:
        cluster = ContainerCluster(
            name="prod-k8s",
            provider="kubernetes",
            endpoint="https://k8s.example.com",
            token="valid-token",
            status="stopped",
            status_message="authentication failed",
        )
        db.add(cluster)
        db.commit()

        refresh_cluster_connection_status(db, cluster)

        assert cluster.status == "running"
        assert cluster.status_message == ""
        assert cluster.version == "v1.29.0"
    finally:
        db.close()


def test_list_clusters_refreshes_connection_status_before_returning_rows(monkeypatch):
    engine = create_engine("sqlite:///:memory:")
    _create_container_tables(engine)
    SessionLocal = sessionmaker(bind=engine)

    monkeypatch.setattr(
        "app.services.containers.test_connection",
        lambda endpoint, token: {"ok": False, "error": "authentication failed"},
    )

    db = SessionLocal()
    try:
        db.add(
            ContainerCluster(
                name="prod-k8s",
                provider="kubernetes",
                endpoint="https://k8s.example.com",
                token="expired-token",
                status="running",
                status_message="",
            )
        )
        db.commit()

        response = api_list_clusters(keyword="", db=db, _=None)

        assert response["data"][0]["status"] == "stopped"
        assert response["data"][0]["status_message"] == "authentication failed"
    finally:
        db.close()


def test_cluster_name_lookup_and_duplicate_detection_are_provider_scoped():
    engine = create_engine("sqlite:///:memory:")
    _create_container_tables(engine)
    SessionLocal = sessionmaker(bind=engine)

    db = SessionLocal()
    try:
        k8s = ContainerCluster(name="prod-main", provider="kubernetes")
        docker = ContainerCluster(name="prod-main", provider="docker")
        db.add_all([k8s, docker])
        db.commit()

        response = api_get_cluster("prod-main", db=db, _=None)

        assert response["data"]["id"] == k8s.id
        assert cluster_name_exists(db, "prod-main") is True
        assert cluster_name_exists(db, "prod-main", exclude_id=k8s.id) is False
        assert docker_host_name_exists(db, "prod-main") is True
        assert docker_host_name_exists(db, "prod-main", exclude_id=docker.id) is False
    finally:
        db.close()


def test_docker_host_can_be_resolved_by_readable_name():
    engine = create_engine("sqlite:///:memory:")
    _create_container_tables(engine)
    SessionLocal = sessionmaker(bind=engine)

    db = SessionLocal()
    try:
        host = ContainerCluster(name="docker-prod-01", provider="docker", endpoint="127.0.0.1:9001")
        db.add(host)
        db.commit()

        response = docker_mgmt.api_get_docker_host("docker-prod-01", db=db, _=None)

        assert response["data"]["id"] == host.id
        assert response["data"]["name"] == "docker-prod-01"
    finally:
        db.close()


def test_numeric_identifiers_are_not_accepted_as_resource_names():
    engine = create_engine("sqlite:///:memory:")
    _create_container_tables(engine)
    SessionLocal = sessionmaker(bind=engine)

    db = SessionLocal()
    try:
        for lookup, value in ((api_get_cluster, "4"), (docker_mgmt.api_get_docker_host, "8")):
            try:
                lookup(value, db=db, _=None)
                raise AssertionError("expected numeric identifiers to be rejected")
            except HTTPException as exc:
                assert exc.status_code == 404
    finally:
        db.close()


def test_name_lookup_rejects_ambiguous_existing_clusters():
    engine = create_engine("sqlite:///:memory:")
    _create_container_tables(engine)
    SessionLocal = sessionmaker(bind=engine)

    db = SessionLocal()
    try:
        db.add_all([
            ContainerCluster(name="duplicate", provider="kubernetes"),
            ContainerCluster(name="duplicate", provider="kubernetes"),
        ])
        db.commit()

        try:
            api_get_cluster("duplicate", db=db, _=None)
            raise AssertionError("expected ambiguous names to be rejected")
        except HTTPException as exc:
            assert exc.status_code == 409
            assert "同名集群" in exc.detail
    finally:
        db.close()


def test_proxy_to_agent_treats_empty_success_response_as_success(monkeypatch):
    calls = []

    class EmptySuccessResponse:
        status_code = 204
        text = ""

        def json(self):
            raise AssertionError("empty 2xx responses should not be parsed as JSON")

    def fake_request(method: str, url: str, timeout: int):
        calls.append((method, url, timeout))
        return EmptySuccessResponse()

    monkeypatch.setattr("app.api.docker_mgmt.http_requests.request", fake_request)

    host = ContainerCluster(name="docker-01", provider="docker", endpoint="127.0.0.1:9001")

    assert _proxy_to_agent(host, "POST", "/containers/abc123/restart") == {}
    assert calls == [("POST", "http://127.0.0.1:9001/containers/abc123/restart", 15)]


def test_proxy_to_agent_treats_plain_text_success_response_as_message(monkeypatch):
    class PlainTextSuccessResponse:
        status_code = 200
        text = "restarted"

        def json(self):
            raise ValueError("not json")

    monkeypatch.setattr(
        "app.api.docker_mgmt.http_requests.request",
        lambda method, url, timeout: PlainTextSuccessResponse(),
    )

    host = ContainerCluster(name="docker-01", provider="docker", endpoint="http://127.0.0.1:9001")

    assert _proxy_to_agent(host, "POST", "/containers/abc123/restart") == {"message": "restarted"}


def test_proxy_to_agent_explains_unsupported_post_from_old_agent(monkeypatch):
    class UnsupportedPostResponse:
        status_code = 501
        text = """<!DOCTYPE HTML>
<html lang="en">
  <body>
    <p>Error code: 501</p>
    <p>Message: Unsupported method ('POST').</p>
  </body>
</html>"""

        def json(self):
            raise ValueError("not json")

    monkeypatch.setattr(
        "app.api.docker_mgmt.http_requests.request",
        lambda method, url, timeout: UnsupportedPostResponse(),
    )

    host = ContainerCluster(name="docker-01", provider="docker", endpoint="http://127.0.0.1:9001")

    try:
        _proxy_to_agent(host, "POST", "/containers/abc123/restart")
        raise AssertionError("expected HTTPException")
    except HTTPException as exc:
        assert exc.status_code == 502
        assert "当前 Docker Agent 版本不支持容器操作" in exc.detail
        assert "<!DOCTYPE HTML>" not in exc.detail


def test_container_logs_proxy_clamps_tail_and_returns_logs(monkeypatch):
    engine = create_engine("sqlite:///:memory:")
    _create_container_tables(engine)
    SessionLocal = sessionmaker(bind=engine)
    calls = []

    def fake_proxy(host: ContainerCluster, method: str, path: str):
        calls.append((host.endpoint, method, path))
        return {"logs": "line-1\nline-2", "tail": 1000}

    monkeypatch.setattr("app.api.docker_mgmt._proxy_to_agent", fake_proxy)

    db = SessionLocal()
    try:
        host = ContainerCluster(name="docker-01", provider="docker", endpoint="127.0.0.1:9001")
        db.add(host)
        db.commit()

        response = docker_mgmt.api_container_logs(
            host.name,
            "abc123def456",
            tail_lines=5000,
            db=db,
            _=None,
        )

        assert response == {"code": 0, "data": {"logs": "line-1\nline-2", "tail": 1000}}
        assert calls == [("127.0.0.1:9001", "GET", "/containers/abc123def456/logs?tail=1000")]
    finally:
        db.close()
