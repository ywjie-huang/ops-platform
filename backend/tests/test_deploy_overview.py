"""发布总览聚合（overview 服务）：KPI / 状态矩阵 / 版本对比 / 记录摘要。"""
from __future__ import annotations

import json
from datetime import datetime, timedelta

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.models  # noqa: F401  注册全部关联模型（DeployAppEnv 的 Asset/Cluster 外键关系）
from app.core.config import CHINA_TZ
from app.models.deploy import (
    DeployAppEnv,
    DeployApproval,
    DeployApplication,
    DeployEnvironment,
    DeployRecord,
)
from app.models.user import User
from app.services.deploy.overview import (
    current_version_for,
    get_kpi,
    get_matrix,
    record_brief,
)


def _make_db():
    engine = create_engine("sqlite:///:memory:")
    for table in (User, DeployApplication, DeployEnvironment, DeployAppEnv, DeployRecord, DeployApproval):
        table.__table__.create(engine)
    return sessionmaker(bind=engine)()


def _seed(db):
    dev = DeployEnvironment(name="dev", approval_required=False, sort_order=1)
    prod = DeployEnvironment(name="prod", approval_required=True, sort_order=2)
    db.add_all([dev, prod])
    db.flush()
    app1 = DeployApplication(name="order-api", app_type="api", jenkins_job_name="order-pipe")
    app2 = DeployApplication(name="web", app_type="web", jenkins_job_name="web-pipe")
    db.add_all([app1, app2])
    db.flush()
    db.add_all([
        DeployAppEnv(app_id=app1.id, env_id=dev.id, enabled=True),
        DeployAppEnv(app_id=app1.id, env_id=prod.id, enabled=True),
        DeployAppEnv(app_id=app2.id, env_id=dev.id, enabled=False),
    ])
    db.flush()
    return dev, prod, app1, app2


def _rec(db, app_id, env_id, status, version="v1", created_at=None):
    r = DeployRecord(app_id=app_id, env_id=env_id, status=status, version=version, deploy_config="")
    db.add(r)
    db.flush()
    if created_at is not None:
        r.created_at = created_at
        db.flush()
    return r


def test_matrix_cells_pick_latest_record():
    """矩阵单元格 = 该 (应用, 环境) 的最新一条记录；未配置的环境不出现在 envs 键中。"""
    db = _make_db()
    dev, prod, app1, app2 = _seed(db)
    _rec(db, app1.id, dev.id, "success", "v1.0")
    latest = _rec(db, app1.id, dev.id, "failed", "v1.1")
    _rec(db, app1.id, prod.id, "triggering", "v1.1")

    m = get_matrix(db)
    assert [e["name"] for e in m["envs"]] == ["dev", "prod"]
    assert m["envs"][1]["approval_required"] is True

    apps = {a["name"]: a for a in m["apps"]}
    cell = apps["order-api"]["envs"][str(dev.id)]
    assert cell["enabled"] is True
    assert cell["record"]["id"] == latest.id
    assert cell["record"]["status"] == "failed"

    # web 只配置了 dev（且 disabled）：prod 键不存在；dev 有配置但无记录 → record=None
    assert str(prod.id) not in apps["web"]["envs"]
    assert apps["web"]["envs"][str(dev.id)]["enabled"] is False
    assert apps["web"]["envs"][str(dev.id)]["record"] is None


def test_kpi_counts():
    """KPI：进行中含 triggering、待审批计数、今日/本周口径正确。"""
    db = _make_db()
    dev, prod, app1, app2 = _seed(db)
    now = datetime.now(CHINA_TZ).replace(tzinfo=None)
    running_rec = _rec(db, app1.id, prod.id, "triggering")
    _rec(db, app1.id, dev.id, "success")
    _rec(db, app2.id, dev.id, "failed", created_at=now - timedelta(days=3))
    db.add(DeployApproval(record_id=running_rec.id, status="pending"))
    db.commit()

    kpi = get_kpi(db)
    assert kpi["running"] == 1
    assert kpi["pending_approvals"] == 1
    assert kpi["today_total"] == 2          # 3 天前的失败不计入今日
    assert kpi["today_success"] == 1
    assert kpi["today_failed"] == 0
    assert kpi["week_failed"] == 1


def test_current_version_skips_failed_and_self():
    """版本对比：取此记录之前最近一次成功版本，跳过失败与自身。"""
    db = _make_db()
    _, prod, app1, _ = _seed(db)
    _rec(db, app1.id, prod.id, "success", "v1.0")
    _rec(db, app1.id, prod.id, "failed", "v1.1")
    cur = _rec(db, app1.id, prod.id, "pending", "v1.2")
    assert current_version_for(db, app1.id, prod.id, cur.id) == "v1.0"
    assert current_version_for(db, app1.id, prod.id, 999) == "v1.0"


def test_record_brief_reads_jenkins_snapshot():
    """record_brief 从 deploy_config 快照解析 Jenkins 构建信息。"""
    db = _make_db()
    dev, _, app1, _ = _seed(db)
    r = _rec(db, app1.id, dev.id, "triggering", "v1")
    r.deploy_config = json.dumps({"jenkins_build_url": "http://j/job/x/47", "jenkins_build_number": 47})
    db.commit()

    brief = record_brief(r)
    assert brief["jenkins_build_url"] == "http://j/job/x/47"
    assert brief["jenkins_build_number"] == 47
    assert record_brief(None) is None
