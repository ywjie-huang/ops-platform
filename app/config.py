from pathlib import Path
from typing import Final

BASE_DIR: Final = Path(__file__).resolve().parent.parent
STATIC_DIR: Final = BASE_DIR / "static"
TEMPLATES_DIR: Final = BASE_DIR / "templates"
SECRET_KEY: Final = "dev-secret-key-change-me"
DEMO_USERNAME: Final = "admin"
DEMO_PASSWORD: Final = "admin123"
