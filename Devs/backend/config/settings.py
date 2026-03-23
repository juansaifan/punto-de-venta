"""Configuración central del POS."""
import os
import sys
from pathlib import Path


def _obtener_project_root() -> Path:
    """Raíz del proyecto (carpeta Devs o superior)."""
    if getattr(sys, "frozen", False) and hasattr(sys, "executable"):
        return Path(sys.executable).resolve().parent
    # Desarrollo: __file__ = .../Devs/backend/config/settings.py -> Devs
    return Path(__file__).resolve().parent.parent.parent


PROJECT_ROOT = _obtener_project_root()
DATA_DIR = PROJECT_ROOT / "data"
LOGS_DIR = PROJECT_ROOT / "logs"

DATABASE_URL = os.getenv(
    "POS_DATABASE_URL",
    f"sqlite:///{(DATA_DIR / 'pos.db').as_posix()}",
)

STORE_NAME = os.getenv("POS_STORE_NAME", "Punto de Venta")
CURRENCY = os.getenv("POS_CURRENCY", "PEN")
DEBUG = os.getenv("POS_DEBUG", "0").lower() in ("1", "true", "yes")


class Settings:
    project_root: Path = PROJECT_ROOT
    data_dir: Path = DATA_DIR
    logs_dir: Path = LOGS_DIR
    database_url: str = DATABASE_URL
    store_name: str = STORE_NAME
    currency: str = CURRENCY
    debug: bool = DEBUG


settings = Settings()
