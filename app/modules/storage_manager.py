import json
from pathlib import Path
from typing import Any, Dict


_SETTINGS_PATH = Path(__file__).resolve().parent.parent / "storage" / "settings.json"


DEFAULT_SETTINGS: Dict[str, Any] = {
    "settings": {
        "microphone": "Default",
        "unnoised": False,
        "active-profile-id": 1,
        "server-port": 8642,
    }
}


def load_settings() -> Dict[str, Any]:
    if not _SETTINGS_PATH.exists():
        return DEFAULT_SETTINGS.copy()
    with _SETTINGS_PATH.open("r", encoding="utf-8") as settings_file:
        return json.load(settings_file)


def save_settings(settings: Dict[str, Any]) -> None:
    _SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with _SETTINGS_PATH.open("w", encoding="utf-8") as settings_file:
        json.dump(settings, settings_file, ensure_ascii=False, indent=2)


def update_settings(updates: Dict[str, Any]) -> Dict[str, Any]:
    settings = load_settings()
    settings_data = settings.setdefault("settings", {})
    settings_data.update(updates)
    save_settings(settings)
    return settings
