import os
import secrets
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
# JWT 签名密钥：绝不使用源码中公开的默认值（否则攻击者可伪造任意用户 token）。
# 未显式配置或使用了已知不安全值时，退化为随机生成的临时密钥（仅供开发）。
# 注意：随机密钥每次进程启动都会变化且多 worker 之间不共享，生产环境必须通过
# SECRET_KEY 环境变量显式指定一个稳定的高熵密钥（见启动期告警）。
_INSECURE_SECRET_VALUES: Final = frozenset({
    "",
    "dev-secret-key-change-me",
    "change-me-in-production",
})
_raw_secret_key: Final = os.environ.get("SECRET_KEY", "").strip()
SECRET_KEY: Final = (
    _raw_secret_key
    if (_raw_secret_key and _raw_secret_key not in _INSECURE_SECRET_VALUES)
    else secrets.token_urlsafe(48)
)
SECRET_KEY_IS_DEFAULT: Final = bool(
    (not _raw_secret_key) or (_raw_secret_key in _INSECURE_SECRET_VALUES)
)
CORS_ORIGINS: Final = tuple(
    origin.strip()
    for origin in os.environ.get("CORS_ORIGINS", "*").split(",")
    if origin.strip()
) or ("*",)
DEFAULT_ADMIN_USERNAME: Final = "admin"
DEFAULT_ADMIN_PASSWORD: Final = "admin123"
INITIAL_ADMIN_USERNAME: Final = os.environ.get(
    "INITIAL_ADMIN_USERNAME", DEFAULT_ADMIN_USERNAME
).strip()
INITIAL_ADMIN_PASSWORD: Final = os.environ.get(
    "INITIAL_ADMIN_PASSWORD", DEFAULT_ADMIN_PASSWORD
)

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
