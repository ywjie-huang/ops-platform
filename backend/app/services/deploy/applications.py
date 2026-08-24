"""Application CRUD service — deploy module."""
from datetime import datetime

from sqlalchemy import or_, select
from sqlalchemy.orm import Session, selectinload

from app.core.config import CHINA_TZ
from app.models.deploy import DeployAppEnv, DeployApplication, DeployEnvironment


def list_applications(
    db: Session,
    *,
    keyword: str = "",
    app_type: str = "",
    deploy_strategy: str = "",
    status: str = "",
) -> list[DeployApplication]:
    """列出应用，支持关键词搜索和多维度筛选。"""
    stmt = select(DeployApplication).options(
        selectinload(DeployApplication.creator),
    )
    keyword = keyword.strip()
    app_type = app_type.strip()
    deploy_strategy = deploy_strategy.strip()
    status = status.strip()

    if keyword:
        like_val = f"%{keyword}%"
        stmt = stmt.where(
            or_(
                DeployApplication.name.ilike(like_val),
                DeployApplication.display_name.ilike(like_val),
                DeployApplication.description.ilike(like_val),
                DeployApplication.git_url.ilike(like_val),
                DeployApplication.jenkins_job_name.ilike(like_val),
            )
        )
    if app_type:
        stmt = stmt.where(DeployApplication.app_type == app_type)
    if deploy_strategy:
        stmt = stmt.where(DeployApplication.deploy_strategy == deploy_strategy)
    if status:
        stmt = stmt.where(DeployApplication.status == status)

    stmt = stmt.order_by(DeployApplication.id.desc())
    return list(db.scalars(stmt).unique().all())


def get_application(db: Session, app_id: int) -> DeployApplication | None:
    """获取单个应用详情。"""
    stmt = select(DeployApplication).options(
        selectinload(DeployApplication.creator),
    ).where(DeployApplication.id == app_id)
    return db.scalar(stmt)


def get_application_by_name(db: Session, name: str) -> DeployApplication | None:
    """按应用名称获取应用详情。"""
    stmt = select(DeployApplication).options(
        selectinload(DeployApplication.creator),
    ).where(DeployApplication.name == name)
    return db.scalar(stmt)


def create_application(
    db: Session,
    *,
    name: str,
    display_name: str = "",
    description: str = "",
    app_type: str = "web",
    git_url: str = "",
    git_branch: str = "main",
    jenkins_job_name: str = "",
    creator_id: int | None = None,
) -> DeployApplication:
    """创建新应用。"""
    app = DeployApplication(
        name=name,
        display_name=display_name,
        description=description,
        app_type=app_type,
        git_url=git_url,
        git_branch=git_branch,
        jenkins_job_name=jenkins_job_name,
        creator_id=creator_id,
    )
    db.add(app)
    db.commit()
    db.refresh(app)
    return get_application(db, app.id) or app


def update_application(
    db: Session,
    app: DeployApplication,
    *,
    name: str,
    display_name: str = "",
    description: str = "",
    app_type: str = "web",
    status: str = "active",
    git_url: str = "",
    git_branch: str = "main",
    jenkins_job_name: str = "",
) -> DeployApplication:
    """更新应用信息。"""
    app.name = name
    app.display_name = display_name
    app.description = description
    app.app_type = app_type
    app.status = status
    app.git_url = git_url
    app.git_branch = git_branch
    app.jenkins_job_name = jenkins_job_name
    app.updated_at = datetime.now(CHINA_TZ)
    db.commit()
    db.refresh(app)
    return get_application(db, app.id) or app


def delete_application(db: Session, app: DeployApplication) -> None:
    """删除应用（级联删除关联的环境配置、记录、配置项）。"""
    db.delete(app)
    db.commit()


def list_environments(db: Session) -> list[DeployEnvironment]:
    """列出所有环境（只读）。"""
    stmt = select(DeployEnvironment).order_by(DeployEnvironment.sort_order)
    return list(db.scalars(stmt).all())
