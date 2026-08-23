"""模式 B demo：Jenkins 回调端点测试（一次性 token 认证 / 幂等 / 状态流转）。"""
from __future__ import annotations

import json
from datetime import datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api.deploy_jenkins import jenkins_callback
from app.models.deploy import DeployApplication, DeployEnvironment, DeployRecord
from app.models.system_config import SystemConfig
from app.models.user import User

RECORD_TOKEN = "one-time-token-abc"


def _make_db():
    engine = create_engine("sqlite:///:memory:")
    SystemConfig.__table__.create(engine)
    User.__table__.create(engine)
    DeployApplication.__table__.create(engine)
    DeployEnvironment.__table__.create(engine)
    DeployRecord.__table__.create(engine)
    # DeployRecord 的 relationship 为 lazy='joined'，查询时 JOIN users 表
    return sessionmaker(bind=engine)()


def _seed_record(db, status="triggering", with_token=True):
    app = DeployApplication(name="jenkins-modeb-demo", status="archived")
    db.add(app)
    db.flush()
    snapshot = {
        "mode": "jenkins-modeb-demo",
        "jenkins_build_number": 5,
    }
    if with_token:
        snapshot["callback_token"] = RECORD_TOKEN
    record = DeployRecord(
        app_id=app.id,
        version="demo-1",
        status=status,
        deploy_config=json.dumps(snapshot),
        log="",
    )
    # started_at 不带时区（naive）——模拟 MySQL 剥掉 tzinfo 后读回的真实形态
    record.started_at = datetime.now()
    db.add(record)
    db.commit()
    return record


def test_callback_rejects_wrong_token():
    db = _make_db()
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


def test_callback_rejects_record_without_token():
    """快照里没有 token 的记录（异常数据）拒绝回调。"""
    db = _make_db()
    record = _seed_record(db, with_token=False)

    result = jenkins_callback(
        body={"record_id": record.id, "status": "success"},
        x_deploy_token="whatever",
        db=db,
    )
    assert result["code"] == 1


def test_callback_updates_triggering_record_to_success():
    db = _make_db()
    record = _seed_record(db, status="triggering")

    result = jenkins_callback(
        body={"record_id": record.id, "status": "success",
              "build_url": "http://jenkins/job/demo/7/"},
        x_deploy_token=RECORD_TOKEN,
        db=db,
    )
    assert result["code"] == 0
    db.refresh(record)
    assert record.status == "success"
    assert record.finished_at is not None
    # duration 正常计算（回归：naive started_at 不再抛 TypeError → 500）
    assert isinstance(record.duration, float)
    assert record.duration >= 0
    # build_url 合并进快照，一次性 token 已焚毁
    snapshot = json.loads(record.deploy_config)
    assert snapshot["jenkins_build_url"] == "http://jenkins/job/demo/7/"
    assert "callback_token" not in snapshot
    assert "[Jenkins 回调] status=success" in record.log


def test_callback_failed_records_error_message():
    db = _make_db()
    record = _seed_record(db, status="triggering")

    jenkins_callback(
        body={"record_id": record.id, "status": "failed", "message": "构建挂了"},
        x_deploy_token=RECORD_TOKEN,
        db=db,
    )
    db.refresh(record)
    assert record.status == "failed"
    assert "构建挂了" in record.error_message


def test_callback_burns_token_after_use():
    """一次性 token 用后即焚：同 token 二次回调被拒（token 已从快照清除）。"""
    db = _make_db()
    record = _seed_record(db, status="triggering")

    first = jenkins_callback(
        body={"record_id": record.id, "status": "success"},
        x_deploy_token=RECORD_TOKEN,
        db=db,
    )
    assert first["code"] == 0

    # 二次回调：token 已焚毁 + 状态已终态，双重拒绝
    second = jenkins_callback(
        body={"record_id": record.id, "status": "failed"},
        x_deploy_token=RECORD_TOKEN,
        db=db,
    )
    assert second["code"] == 1
    assert "token" in second["msg"]
    db.refresh(record)
    assert record.status == "success"  # 不被改写


def test_callback_rejects_unknown_record_and_bad_body():
    db = _make_db()

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
