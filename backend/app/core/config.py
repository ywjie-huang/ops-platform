import os
from pathlib import Path
from typing import Final

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
SECRET_KEY: Final = "dev-secret-key-change-me"
DEMO_USERNAME: Final = "admin"
DEMO_PASSWORD: Final = "admin123"

# Prometheus 配置
PROMETHEUS_URL: Final = "http://172.16.24.31:30001"

# Alertmanager 配置
ALERTMANAGER_URL: Final = "http://172.16.24.31:30093"
