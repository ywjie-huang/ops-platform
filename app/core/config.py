from pathlib import Path
from typing import Final

APP_DIR: Final = Path(__file__).resolve().parent
PROJECT_DIR: Final = APP_DIR.parent
STATIC_DIR: Final = APP_DIR / "static"
TEMPLATES_DIR: Final = APP_DIR / "templates"
DATA_DIR: Final = PROJECT_DIR / "data"

# MySQL 配置
MYSQL_HOST: Final = "localhost"
MYSQL_PORT: Final = 3306
MYSQL_USER: Final = "root"
MYSQL_PASSWORD: Final = "123456"
MYSQL_DATABASE: Final = "ops_platform"

DATABASE_URL: Final = (
    f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}"
    f"@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DATABASE}?charset=utf8mb4"
)
SECRET_KEY: Final = "dev-secret-key-change-me"
DEMO_USERNAME: Final = "admin"
DEMO_PASSWORD: Final = "admin123"
