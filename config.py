"""Carga de configuración desde .env y mapping.yaml."""

import os
from pathlib import Path

import yaml
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Rutas base
PROJECT_ROOT = Path(__file__).resolve().parent


def get_env(key: str, default: str = "") -> str:
    """Obtiene una variable de entorno."""
    return os.getenv(key, default).strip()


def load_mapping() -> dict[str, str]:
    """Carga el archivo mapping.yaml y retorna el diccionario de mapeo."""
    mapping_path = PROJECT_ROOT / "mapping.yaml"
    if not mapping_path.exists():
        return {}

    with open(mapping_path, encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if data is None:
        return {}
    return {str(k): str(v) for k, v in data.items()}


def _default_app_url() -> str:
    """En Railway, APP_URL puede inferirse del dominio público del servicio."""
    domain = get_env("RAILWAY_PUBLIC_DOMAIN")
    if domain:
        return f"https://{domain}" if not domain.startswith("http") else domain
    return "http://127.0.0.1:5001"


# Configuración principal
FORM_URL = get_env("FORM_URL", "https://ee-eu.kobotoolbox.org/x/5htUNnQd")
# URL de nuestra app (para que Playwright la abra y llene el iframe ahí)
APP_URL = get_env("APP_URL") or _default_app_url()
EXCEL_PATH = Path(get_env("EXCEL_PATH", "datos.xlsx"))
HEADLESS = get_env("HEADLESS", "true").lower() in ("true", "1", "yes")
RESUME_FROM_ROW_STR = get_env("RESUME_FROM_ROW", "")

# Resolver ruta del Excel relativa al proyecto
if not EXCEL_PATH.is_absolute():
    EXCEL_PATH = PROJECT_ROOT / EXCEL_PATH

# Fila desde la cual reanudar (None = desde el inicio)
RESUME_FROM_ROW: int | None = None
if RESUME_FROM_ROW_STR:
    try:
        RESUME_FROM_ROW = int(RESUME_FROM_ROW_STR)
    except ValueError:
        RESUME_FROM_ROW = None

# Directorio de logs
LOGS_DIR = PROJECT_ROOT / "logs"
STATS_FILE = LOGS_DIR / "estadisticas.json"
ERROR_LOG_FILE = LOGS_DIR / "errores.log"

# Navegar directo a FORM_URL (más fiable que cargar vía app con iframe)
USE_DIRECT_FORM_URL = get_env("USE_DIRECT_FORM_URL", "true").lower() in ("true", "1", "yes")

# === Envío por API KoboToolbox (más preciso que llenado en navegador) ===
KOBO_API_TOKEN = get_env("KOBO_API_TOKEN", "")
KOBO_ASSET_UID = get_env("KOBO_ASSET_UID", "")
# URL del servidor KoBoCat (kc); para EU puede ser https://kc-eu.kobotoolbox.org
KOBO_KC_URL = get_env("KOBO_KC_URL", "https://kc.kobotoolbox.org")
USE_KOBO_API = bool(KOBO_API_TOKEN and KOBO_ASSET_UID)
