from pathlib import Path
from typing import Final

APP_DIR: Final = Path(__file__).resolve().parent
PROJECT_DIR: Final = APP_DIR.parent
STATIC_DIR: Final = APP_DIR / "static"
TEMPLATES_DIR: Final = APP_DIR / "templates"
DATA_DIR: Final = PROJECT_DIR / "data"
DATABASE_FILE: Final = DATA_DIR / "ops.db"
DATABASE_URL: Final = f"sqlite:///{DATABASE_FILE.as_posix()}"
SECRET_KEY: Final = "dev-secret-key-change-me"
DEMO_USERNAME: Final = "admin"
DEMO_PASSWORD: Final = "admin123"
