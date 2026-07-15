import os
import secrets

# Project root directory (parent of app/)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
DB_PATH = os.path.join(DATA_DIR, "vulhub_web.db")

DEFAULT_SERVER_PORT = 8088
DEFAULT_IDLE_TIMEOUT_HOURS = 0
DEFAULT_REMOVE_IMAGE = True
DEFAULT_SCAN_CRON = "0 */6 * * *"
DEFAULT_CLEANUP_CRON = "0 2 * * *"

JWT_ALGORITHM = "HS256"
JWT_EXPIRE_HOURS = 72

SECRET_KEY = ""


def get_secret_key() -> str:
    global SECRET_KEY
    if not SECRET_KEY:
        SECRET_KEY = secrets.token_hex(32)
    return SECRET_KEY
