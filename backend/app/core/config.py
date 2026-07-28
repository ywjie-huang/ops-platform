import os
from datetime import timezone, timedelta
from pathlib import Path
from typing import Final

# 中国时区 (UTC+8)
CHINA_TZ: Final = timezone(timedelta(hours=8))

# core/config.py 在 app/core/ 下，APP_DIR 需要上溯两级到 app/
APP_DIR: Final = Path(__file__).resolve().parent.parent
PROJECT_DIR: Final = APP_DIR.parent
DATA_DIR: Final = PROJECT_DIR / "data"

# MySQL 配置（支持环境变量覆盖，兼容 Docker 部署）
MYSQL_HOST: Final = os.environ.get("MYSQL_HOST", "localhost")
MYSQL_PORT: Final = int(os.environ.get("MYSQL_PORT", "3306"))
MYSQL_USER: Final = os.environ.get("MYSQL_USER", "root")
MYSQL_PASSWORD: Final = os.environ.get("MYSQL_PASSWORD", "123456")
MYSQL_DATABASE: Final = os.environ.get("MYSQL_DATABASE", "ops_platform")

DATABASE_URL: Final = (
    f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}"
    f"@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DATABASE}?charset=utf8mb4"
)
SECRET_KEY: Final = os.environ.get("SECRET_KEY", "dev-secret-key-change-me")
CORS_ORIGINS: Final = tuple(
    origin.strip()
    for origin in os.environ.get("CORS_ORIGINS", "*").split(",")
    if origin.strip()
) or ("*",)
DEMO_USERNAME: Final = "admin"
DEMO_PASSWORD: Final = "admin123"

# 构建产物存储目录
DEPLOY_ARTIFACT_DIR: Final = DATA_DIR / "deploy_artifacts"

# Redis 配置（支持环境变量覆盖，兼容 Docker 部署）
REDIS_HOST: Final = os.environ.get("REDIS_HOST", "localhost")
REDIS_PORT: Final = int(os.environ.get("REDIS_PORT", "6379"))
REDIS_PASSWORD: Final = os.environ.get("REDIS_PASSWORD", "123456")
REDIS_DB: Final = int(os.environ.get("REDIS_DB", "0"))

# Prometheus 配置
PROMETHEUS_URL: Final = os.environ.get("PROMETHEUS_URL", "").strip().rstrip("/")

# Alertmanager 配置
ALERTMANAGER_URL: Final = os.environ.get("ALERTMANAGER_URL", "").strip().rstrip("/")
