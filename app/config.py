from pathlib import Path
from typing import Final

APP_DIR: Final = Path(__file__).resolve().parent
PROJECT_DIR: Final = APP_DIR.parent
STATIC_DIR: Final = APP_DIR / "static"
TEMPLATES_DIR: Final = APP_DIR / "templates"
SECRET_KEY: Final = "dev-secret-key-change-me"
DEMO_USERNAME: Final = "admin"
DEMO_PASSWORD: Final = "admin123"
