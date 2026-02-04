import json
from pathlib import Path
from typing import Any, Dict, List, Optional


_SETTINGS_PATH = Path(__file__).resolve().parent.parent / "storage" / "settings.json"
_PROFILES_PATH = Path(__file__).resolve().parent.parent / "storage" / "profiles.json"


DEFAULT_SETTINGS: Dict[str, Any] = {
    "settings": {
        "microphone": "Default",
        "unnoised": False,
        "active-profile-id": 1,
        "server-port": 8642,
    }
}

DEFAULT_PROFILES: Dict[str, Any] = {
    "profiles": [
        {
            "id": 1,
            "name": "default",
            "images": [],
        }
    ]
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


def load_profiles() -> Dict[str, Any]:
    if not _PROFILES_PATH.exists():
        return DEFAULT_PROFILES.copy()
    with _PROFILES_PATH.open("r", encoding="utf-8") as profiles_file:
        return json.load(profiles_file)


def save_profiles(profiles: Dict[str, Any]) -> None:
    _PROFILES_PATH.parent.mkdir(parents=True, exist_ok=True)
    with _PROFILES_PATH.open("w", encoding="utf-8") as profiles_file:
        json.dump(profiles, profiles_file, ensure_ascii=False, indent=2)


def list_profiles() -> List[Dict[str, Any]]:
    return load_profiles().get("profiles", [])


def get_profile_by_id(profile_id: int) -> Optional[Dict[str, Any]]:
    for profile in list_profiles():
        if profile.get("id") == profile_id:
            return profile
    return None


def _next_profile_id(profiles: List[Dict[str, Any]]) -> int:
    max_id = 0
    for profile in profiles:
        try:
            max_id = max(max_id, int(profile.get("id", 0)))
        except (TypeError, ValueError):
            continue
    return max_id + 1


def create_profile(
    name: str,
    images: List[Dict[str, Any]],
    blink: Optional[Dict[str, Any]] = None,
    blink_images: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    profiles_data = load_profiles()
    profiles = profiles_data.setdefault("profiles", [])
    new_profile = {
        "id": _next_profile_id(profiles),
        "name": name,
        "images": images,
        "blink": blink or {},
        "blink-images": blink_images or [],
    }
    profiles.append(new_profile)
    save_profiles(profiles_data)
    return new_profile


def update_profile(updated_profile: Dict[str, Any]) -> None:
    profiles_data = load_profiles()
    profiles = profiles_data.setdefault("profiles", [])
    for idx, profile in enumerate(profiles):
        if profile.get("id") == updated_profile.get("id"):
            profiles[idx] = updated_profile
            save_profiles(profiles_data)
            return
    profiles.append(updated_profile)
    save_profiles(profiles_data)


def delete_profile(profile_id: int) -> None:
    profiles_data = load_profiles()
    profiles = profiles_data.setdefault("profiles", [])
    profiles_data["profiles"] = [p for p in profiles if p.get("id") != profile_id]
    save_profiles(profiles_data)
