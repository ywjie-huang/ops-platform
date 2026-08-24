"""模式 B（Jenkins 治理触发）：参数契约与应用 release_mode 字段。"""
from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.deploy import DeployApplication, DeployEnvironment, DeployRecord
from app.models.system_config import SystemConfig
from app.models.user import User
from app.services.deploy.applications import create_application, update_application
from app.services.deploy.modeb import build_jenkins_params


def test_build_jenkins_params_contract():
    """模式 B 参数契约：8 个参数齐全，回调对账锚点与一次性凭据都在。"""
    params = build_jenkins_params(
        app_name="order-service",
        env_name="prod",
        version="v2.3.1",
        operator="zhangsan",
        record_id=456,
        release_mode="rollback",
        rollback_from=450,
        callback_token="tok-abc",
    )
    assert params == {
        "APP_NAME": "order-service",
        "ENV": "prod",
        "VERSION": "v2.3.1",
        "OPERATOR": "zhangsan",
        "RECORD_ID": "456",
        "RELEASE_MODE": "rollback",
        "ROLLBACK_FROM": "450",
        "CALLBACK_TOKEN": "tok-abc",
    }


def test_build_jenkins_params_defaults():
    """正常发布：rollback_from 为空串。"""
    params = build_jenkins_params(
        app_name="app", env_name="dev", version="v1",
        operator="op", record_id=1, callback_token="t",
    )
    assert params["RELEASE_MODE"] == "deploy"
    assert params["ROLLBACK_FROM"] == ""


def _make_db():
    engine = create_engine("sqlite:///:memory:")
    for table in (SystemConfig, User, DeployApplication, DeployEnvironment, DeployRecord):
        table.__table__.create(engine)
    return sessionmaker(bind=engine)()


def test_application_release_mode_crud_roundtrip():
    """应用 CRUD 透传 release_mode，默认 platform。"""
    db = _make_db()
    app = create_application(db, name="order-service", release_mode="jenkins", jenkins_job_name="order-deploy")
    assert app.release_mode == "jenkins"

    # 未传时默认 platform
    app2 = create_application(db, name="another")
    assert app2.release_mode == "platform"

    update_application(db, app2, name="another", release_mode="jenkins")
    db.refresh(app2)
    assert app2.release_mode == "jenkins"
