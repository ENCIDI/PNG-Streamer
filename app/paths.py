import os
import sys
from pathlib import Path


def is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def _app_root() -> Path:
    if is_frozen():
        # Inside an AppImage sys.executable points into the temporary mount,
        # the real location of the file is passed in $APPIMAGE.
        appimage = os.environ.get("APPIMAGE")
        if appimage:
            return Path(appimage).resolve().parent
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


# Writable location the program lives in (repo root when run from source).
APP_ROOT = _app_root()

# Read-only resources shipped with the program.
RESOURCES_DIR = Path(getattr(sys, "_MEIPASS", APP_ROOT)) / "app"
DEFAULTS_DIR = RESOURCES_DIR / "defaults"

# User data: never touched by updates.
DATA_DIR = APP_ROOT / "data"
IMAGES_DIR = DATA_DIR / "images"
LOGS_DIR = DATA_DIR / "logs"
BACKUPS_DIR = DATA_DIR / "backups"

# Locations used before v3, migrated into DATA_DIR on first start.
LEGACY_STORAGE_DIR = APP_ROOT / "app" / "storage"
LEGACY_IMAGES_DIR = APP_ROOT / "images"
