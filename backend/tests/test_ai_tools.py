from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.container import ContainerCluster, DockerContainer
from app.services.ai.tools import handle_query_containers


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
