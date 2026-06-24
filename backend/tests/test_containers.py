from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api.containers import api_list_clusters
from app.models.container import ContainerCluster, ContainerDeployment, ContainerPod
from app.services.containers import refresh_cluster_connection_status


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
