"""模式 B demo：Jenkins 回调端点测试（token 认证 / 幂等 / 状态流转）。"""
from __future__ import annotations

import json

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api.deploy_jenkins import CALLBACK_TOKEN_KEY, jenkins_callback
from app.core.settings import set_config
from app.models.deploy import DeployApplication, DeployEnvironment, DeployRecord
from app.models.system_config import SystemConfig
from app.models.user import User


def _make_db():
    engine = create_engine("sqlite:///:memory:")
    SystemConfig.__table__.create(engine)
    User.__table__.create(engine)
    DeployApplication.__table__.create(engine)
    DeployEnvironment.__table__.create(engine)
    DeployRecord.__table__.create(engine)
    # DeployRecord 的 relationship 为 lazy='joined'，查询时 JOIN users 表
    return sessionmaker(bind=engine)()


def _seed_record(db, status="triggering"):
    from datetime import datetime
    app = DeployApplication(name="jenkins-modeb-demo", status="archived")
    db.add(app)
    db.flush()
    record = DeployRecord(
        app_id=app.id,
        version="demo-1",
        status=status,
        deploy_config=json.dumps({"mode": "jenkins-modeb-demo", "jenkins_build_number": 5}),
        log="",
    )
    # started_at 不带时区（naive）——模拟 MySQL 剥掉 tzinfo 后读回的真实形态
    record.started_at = datetime.now()
    db.add(record)
    db.commit()
    return record


def test_callback_rejects_wrong_token():
    db = _make_db()
    set_config(db, CALLBACK_TOKEN_KEY, "right-token", "")
    db.commit()
    record = _seed_record(db)

    result = jenkins_callback(
        body={"record_id": record.id, "status": "success"},
        x_deploy_token="wrong-token",
        db=db,
    )
    assert result["code"] == 1
    assert "token" in result["msg"]
    db.refresh(record)
    assert record.status == "triggering"  # 未被改动


def test_callback_updates_triggering_record_to_success():
    db = _make_db()
    set_config(db, CALLBACK_TOKEN_KEY, "tok", "")
    db.commit()
    record = _seed_record(db, status="triggering")

    result = jenkins_callback(
        body={"record_id": record.id, "status": "success",
              "build_url": "http://jenkins/job/demo/7/"},
        x_deploy_token="tok",
        db=db,
    )
    assert result["code"] == 0
    db.refresh(record)
    assert record.status == "success"
    assert record.finished_at is not None
    # duration 正常计算（回归：naive started_at 不再抛 TypeError → 500）
    assert isinstance(record.duration, float)
    assert record.duration >= 0
    # build_url 合并进快照
    snapshot = json.loads(record.deploy_config)
    assert snapshot["jenkins_build_url"] == "http://jenkins/job/demo/7/"
    assert "[Jenkins 回调] status=success" in record.log


def test_callback_failed_records_error_message():
    db = _make_db()
    set_config(db, CALLBACK_TOKEN_KEY, "tok", "")
    db.commit()
    record = _seed_record(db, status="triggering")

    jenkins_callback(
        body={"record_id": record.id, "status": "failed", "message": "构建挂了"},
        x_deploy_token="tok",
        db=db,
    )
    db.refresh(record)
    assert record.status == "failed"
    assert "构建挂了" in record.error_message


def test_callback_is_idempotent_for_finished_records():
    """重复/迟到回调 no-op：已终态的记录不被二次改写。"""
    db = _make_db()
    set_config(db, CALLBACK_TOKEN_KEY, "tok", "")
    db.commit()
    record = _seed_record(db, status="success")  # 已完成

    result = jenkins_callback(
        body={"record_id": record.id, "status": "failed"},  # 迟到的失败回调
        x_deploy_token="tok",
        db=db,
    )
    assert result["code"] == 0
    assert "no-op" in result["msg"]
    db.refresh(record)
    assert record.status == "success"  # 不被改写


def test_callback_rejects_unknown_record_and_bad_body():
    db = _make_db()
    set_config(db, CALLBACK_TOKEN_KEY, "tok", "")
    db.commit()

    r1 = jenkins_callback(
        body={"record_id": 99999, "status": "success"},
        x_deploy_token="tok", db=db,
    )
    assert r1["code"] == 1

    r2 = jenkins_callback(
        body={"record_id": "abc", "status": "weird"},
        x_deploy_token="tok", db=db,
    )
    assert r2["code"] == 1
