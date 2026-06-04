"""
发布记录管理、执行调度、回滚。
"""

from __future__ import annotations

import json
import logging
from datetime import datetime

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.config import CHINA_TZ
from app.models.deploy import DeployAppEnv, DeployRecord

logger = logging.getLogger(__name__)


# ─── 记录 CRUD ───────────────────────────────────────────────


def list_records(
    db: Session,
    *,
    application_id: int | None = None,
    environment_id: int | None = None,
    status: str = "",
    keyword: str = "",
) -> list[DeployRecord]:
    stmt = select(DeployRecord)
    if application_id:
        stmt = stmt.where(DeployRecord.application_id == application_id)
    if environment_id:
        stmt = stmt.where(DeployRecord.environment_id == environment_id)
    status = status.strip()
    if status:
        stmt = stmt.where(DeployRecord.status == status)
    keyword = keyword.strip()
    if keyword:
        like_val = f"%{keyword}%"
        stmt = stmt.where(
            or_(
                DeployRecord.version.ilike(like_val),
                DeployRecord.image.ilike(like_val),
            )
        )
    stmt = stmt.order_by(DeployRecord.id.desc())
    return list(db.scalars(stmt).all())


def get_record(db: Session, record_id: int) -> DeployRecord | None:
    return db.get(DeployRecord, record_id)


# ─── 发布执行 ────────────────────────────────────────────────


def execute_deployment(db: Session, record: DeployRecord) -> dict:
    """
    执行发布。根据 deploy_method 分发到不同的执行器。
    返回 {"ok": True/False, "error": "..."}
    """
    # 查找应用-环境配置
    app_env = db.scalar(
        select(DeployAppEnv).where(
            DeployAppEnv.application_id == record.application_id,
            DeployAppEnv.environment_id == record.environment_id,
        )
    )
    if not app_env:
        return {"ok": False, "error": "未找到该应用在此环境的配置，请先配置部署信息"}

    method = record.deploy_method

    if method == "jenkins":
        return _execute_jenkins(db, record, app_env)
    elif method == "ssh":
        return {"ok": False, "error": "SSH 部署请使用文件上传接口"}
    elif method == "docker":
        return _execute_docker(db, record, app_env)
    elif method == "kubernetes":
        return _execute_k8s(db, record, app_env)
    else:
        return {"ok": False, "error": f"不支持的部署方式: {method}"}


def _execute_jenkins(db: Session, record: DeployRecord, app_env: DeployAppEnv) -> dict:
    """Jenkins 构建触发。"""
    if not app_env.jenkins_job_name:
        return {"ok": False, "error": "未配置 Jenkins Job 名称"}

    # 从系统配置获取 Jenkins 连接信息
    jenkins_config = _get_jenkins_config(db)
    if not jenkins_config:
        return {"ok": False, "error": "未配置 Jenkins 连接信息，请在系统配置中设置"}

    from app.services.deploy.jenkins import trigger_build

    # 解析构建参数
    params = {}
    if record.version:
        params["VERSION"] = record.version
    if record.image:
        params["IMAGE"] = record.image
    # 合并默认参数
    try:
        default_params = json.loads(app_env.jenkins_params_json or "{}")
        default_params.update(params)
        params = default_params
    except json.JSONDecodeError:
        pass

    result = trigger_build(
        base_url=jenkins_config["base_url"],
        job_name=app_env.jenkins_job_name,
        username=jenkins_config["username"],
        api_token=jenkins_config["api_token"],
        params=params if params else None,
    )

    if not result["ok"]:
        return result

    # 更新记录状态
    record.status = "building"
    record.started_at = datetime.now(CHINA_TZ)
    # 暂存 queue_id 到 logs 字段（后续轮询时使用）
    record.logs = json.dumps({"queue_id": result.get("queue_id")})
    db.flush()

    return {"ok": True, "msg": "Jenkins 构建已触发"}


def _execute_docker(db: Session, record: DeployRecord, app_env: DeployAppEnv) -> dict:
    """Docker 部署（P1 实现）。"""
    return {"ok": False, "error": "Docker 部署功能即将上线"}


def _execute_k8s(db: Session, record: DeployRecord, app_env: DeployAppEnv) -> dict:
    """K8s 部署（P2 实现）。"""
    return {"ok": False, "error": "Kubernetes 部署功能即将上线"}


def execute_ssh_deployment(
    db: Session,
    record: DeployRecord,
    file_content: bytes,
    file_name: str,
) -> dict:
    """
    SSH 部署：上传文件到目标服务器并执行部署脚本。
    由 API 文件上传端点调用。
    """
    app_env = db.scalar(
        select(DeployAppEnv).where(
            DeployAppEnv.application_id == record.application_id,
            DeployAppEnv.environment_id == record.environment_id,
        )
    )
    if not app_env:
        return {"ok": False, "error": "未找到该应用在此环境的配置，请先配置部署信息"}
    if not app_env.ssh_asset_id:
        return {"ok": False, "error": "未配置目标主机，请先在环境配置中设置 SSH 部署信息"}
    if not app_env.ssh_deploy_path:
        return {"ok": False, "error": "未配置部署路径，请先在环境配置中设置部署目录"}

    from app.services.deploy.ssh_deployer import deploy_via_ssh

    record.status = "deploying"
    record.started_at = datetime.now(CHINA_TZ)
    db.flush()

    result = deploy_via_ssh(
        db,
        asset_id=app_env.ssh_asset_id,
        deploy_path=app_env.ssh_deploy_path,
        deploy_script=app_env.ssh_deploy_script or "",
        file_content=file_content,
        file_name=file_name,
    )

    record.finished_at = datetime.now(CHINA_TZ)
    if record.started_at:
        record.duration_seconds = int((record.finished_at - record.started_at).total_seconds())
    record.logs = result.get("logs", "")

    if result["ok"]:
        record.status = "success"
    else:
        record.status = "failed"
        record.logs += f"\n[错误] {result.get('error', '')}"

    db.flush()
    return result


def execute_ssh_deployment_background(
    record_id: int,
    file_content: bytes,
    file_name: str,
) -> None:
    """后台执行 SSH 部署，独立 DB session。"""
    from app.db.database import SessionLocal

    db = SessionLocal()
    try:
        record = db.get(DeployRecord, record_id)
        if not record:
            logger.error("SSH 部署后台任务：记录 %s 不存在", record_id)
            return
        try:
            result = execute_ssh_deployment(db, record, file_content, file_name)
            # execute_ssh_deployment 返回错误时，确保记录状态被更新
            if not result.get("ok"):
                record.status = "failed"
                record.finished_at = datetime.now(CHINA_TZ)
                record.logs = (record.logs or "") + f"\n[错误] {result.get('error', '未知错误')}"
            db.commit()
        except Exception as e:
            logger.exception("SSH 部署后台任务异常: record_id=%s", record_id)
            record.status = "failed"
            record.finished_at = datetime.now(CHINA_TZ)
            record.logs = (record.logs or "") + f"\n[系统错误] {e}"
            db.commit()
    finally:
        db.close()


# ─── Jenkins 状态轮询 ───────────────────────────────────────


def poll_running_deployments(db: Session) -> None:
    """
    轮询所有 building 状态的 Jenkins 发布记录，更新状态。
    由 scheduler 或后台线程调用。
    """
    stmt = select(DeployRecord).where(DeployRecord.status == "building")
    records = list(db.scalars(stmt).all())
    if not records:
        return

    jenkins_config = _get_jenkins_config(db)
    if not jenkins_config:
        logger.warning("Jenkins 配置缺失，跳过轮询")
        return

    from app.services.deploy.jenkins import get_build_info, get_build_log, get_queue_item

    for record in records:
        try:
            app_env = db.scalar(
                select(DeployAppEnv).where(
                    DeployAppEnv.application_id == record.application_id,
                    DeployAppEnv.environment_id == record.environment_id,
                )
            )
            if not app_env or not app_env.jenkins_job_name:
                continue

            # 如果还没有 build_number，尝试从 queue 获取
            if not record.jenkins_build_number:
                queue_info = {}
                try:
                    queue_info = json.loads(record.logs or "{}")
                except json.JSONDecodeError:
                    pass
                queue_id = queue_info.get("queue_id")
                if queue_id:
                    qr = get_queue_item(
                        jenkins_config["base_url"], queue_id,
                        jenkins_config["username"], jenkins_config["api_token"],
                    )
                    if qr["ok"] and qr.get("build_number"):
                        record.jenkins_build_number = qr["build_number"]
                        db.flush()
                    elif qr["ok"] and qr.get("cancelled"):
                        record.status = "failed"
                        record.finished_at = datetime.now(CHINA_TZ)
                        record.logs = "构建被取消"
                        db.flush()
                        continue
                    else:
                        continue  # 还在队列中，下次再查
                else:
                    continue

            # 查询构建状态
            info = get_build_info(
                jenkins_config["base_url"], app_env.jenkins_job_name,
                record.jenkins_build_number,
                jenkins_config["username"], jenkins_config["api_token"],
            )
            if not info["ok"]:
                continue

            if info["building"]:
                # 还在构建中，拉取最新日志
                log_result = get_build_log(
                    jenkins_config["base_url"], app_env.jenkins_job_name,
                    record.jenkins_build_number,
                    jenkins_config["username"], jenkins_config["api_token"],
                )
                if log_result["ok"]:
                    record.logs = log_result.get("text", "")
                continue

            # 构建完成
            build_result = info.get("result", "")
            record.finished_at = datetime.now(CHINA_TZ)
            record.duration_seconds = int(info.get("duration", 0) / 1000)
            record.jenkins_build_url = info.get("url", "")

            # 拉取完整日志
            log_result = get_build_log(
                jenkins_config["base_url"], app_env.jenkins_job_name,
                record.jenkins_build_number,
                jenkins_config["username"], jenkins_config["api_token"],
            )
            if log_result["ok"]:
                record.logs = log_result.get("text", "")

            if build_result == "SUCCESS":
                record.status = "success"
            else:
                record.status = "failed"

            db.flush()
            logger.info("Jenkins 构建 #%s 完成，结果: %s", record.jenkins_build_number, build_result)

        except Exception as e:
            logger.error("轮询发布记录 #%s 失败: %s", record.id, e)


# ─── 回滚 ────────────────────────────────────────────────────


def rollback_deployment(db: Session, record_id: int, user_id: int) -> dict:
    """
    回滚到指定发布记录的版本。创建一条新的发布记录。
    """
    original = get_record(db, record_id)
    if not original:
        return {"ok": False, "error": "原发布记录不存在"}

    if original.status not in ("success", "failed", "rolled_back"):
        return {"ok": False, "error": "只能回滚已完成的发布"}

    # 找到该应用在该环境的上一个成功版本（排除当前记录）
    prev = db.scalar(
        select(DeployRecord)
        .where(
            DeployRecord.application_id == original.application_id,
            DeployRecord.environment_id == original.environment_id,
            DeployRecord.status == "success",
            DeployRecord.id != record_id,
        )
        .order_by(DeployRecord.id.desc())
    )
    if not prev:
        return {"ok": False, "error": "没有找到可回滚的历史版本"}

    # 创建新的发布记录
    new_record = DeployRecord(
        application_id=original.application_id,
        environment_id=original.environment_id,
        deploy_method=original.deploy_method,
        version=prev.version,
        image=prev.image,
        status="pending",
        trigger_type="manual",
        rollback_from=record_id,
        creator_id=user_id,
    )
    db.add(new_record)
    db.flush()

    return {"ok": True, "record_id": new_record.id}


# ─── 发布状态矩阵 ────────────────────────────────────────────


def get_status_matrix(db: Session) -> list[dict]:
    """
    获取发布状态矩阵：每个应用在每个环境的当前版本和状态。
    返回 [{app_id, app_name, display_name, app_type, deploy_method, envs: {env_name: {version, status, record_id, finished_at}}}]
    """
    from app.models.deploy import DeployApplication, DeployEnvironment

    apps = list(db.scalars(select(DeployApplication).where(DeployApplication.status == "active").order_by(DeployApplication.id)).all())
    envs = list(db.scalars(select(DeployEnvironment).order_by(DeployEnvironment.sort_order)).all())

    # 预取每个应用在每个环境的最新成功/失败记录
    all_records = list(
        db.scalars(
            select(DeployRecord)
            .where(DeployRecord.status.in_(["success", "failed", "building", "deploying", "pending"]))
            .order_by(DeployRecord.id.desc())
        ).all()
    )

    # 构建索引: (app_id, env_id) -> 最新记录
    latest_map: dict[tuple[int, int], DeployRecord] = {}
    for r in all_records:
        key = (r.application_id, r.environment_id)
        if key not in latest_map:
            latest_map[key] = r

    result = []
    for app in apps:
        env_data = {}
        for env in envs:
            record = latest_map.get((app.id, env.id))
            if record:
                env_data[env.name] = {
                    "version": record.version or record.image or "-",
                    "status": record.status,
                    "record_id": record.id,
                    "finished_at": record.finished_at.isoformat() if record.finished_at else None,
                }
            else:
                env_data[env.name] = {"version": "-", "status": "none", "record_id": None, "finished_at": None}
        result.append({
            "app_id": app.id,
            "app_name": app.name,
            "display_name": app.display_name,
            "app_type": app.app_type,
            "deploy_method": app.deploy_method,
            "envs": env_data,
        })

    return result


# ─── 概览统计 ────────────────────────────────────────────────


def get_overview(db: Session) -> dict:
    """发布概览统计。"""
    from app.models.deploy import DeployApplication

    total_apps = db.scalar(select(DeployApplication).where(DeployApplication.status == "active")) or 0
    total_apps = len(list(db.scalars(select(DeployApplication).where(DeployApplication.status == "active")).all()))

    total_records = len(list(db.scalars(select(DeployRecord)).all()))
    success_count = len(list(db.scalars(select(DeployRecord).where(DeployRecord.status == "success")).all()))
    failed_count = len(list(db.scalars(select(DeployRecord).where(DeployRecord.status == "failed")).all()))
    building_count = len(list(db.scalars(select(DeployRecord).where(DeployRecord.status == "building")).all()))
    pending_count = len(list(db.scalars(select(DeployRecord).where(DeployRecord.status == "pending")).all()))

    success_rate = round(success_count / total_records * 100, 1) if total_records > 0 else 0

    return {
        "total_apps": total_apps,
        "total_records": total_records,
        "success_count": success_count,
        "failed_count": failed_count,
        "building_count": building_count,
        "pending_count": pending_count,
        "success_rate": success_rate,
    }


# ─── 工具函数 ────────────────────────────────────────────────


def _get_jenkins_config(db: Session) -> dict | None:
    """从系统配置获取 Jenkins 连接信息。"""
    from app.models.system_config import SystemConfig

    config = db.scalar(select(SystemConfig).where(SystemConfig.key == "jenkins_config"))
    if not config:
        return None
    try:
        data = json.loads(config.value)
        if data.get("base_url") and data.get("username") and data.get("api_token"):
            return data
    except (json.JSONDecodeError, AttributeError):
        pass
    return None
