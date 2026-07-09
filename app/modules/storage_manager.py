import json
from pathlib import Path
from app.modules import logging_manager as logm
from typing import Any, Dict, List, Optional


_SETTINGS_PATH = Path(__file__).resolve().parent.parent / "storage" / "settings.json"
_PROFILES_PATH = Path(__file__).resolve().parent.parent / "storage" / "profiles.json"
_SOUND_PROFILES_PATH = Path(__file__).resolve().parent.parent / "storage" / "sound_profiles.json"
_LOGGER = logm.get_logger(__name__)


DEFAULT_SETTINGS: Dict[str, Any] = {
    "settings": {
        "active-image-profile-id": 1,
        "active-sound-profile-id": 1,
        "server-port": 8642,
        "show-console": False,
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

DEFAULT_SOUND_PROFILES: Dict[str, Any] = {
    "sound-profiles": [
        {
            "id": 1,
            "name": "default",
            "host-api": None,
            "microphone": None,
            "microphone-name": "Default",
            "unnoised": False,
            "noise-algorithm": "adaptive",
            "noise-threshold": 15.0,
            "compressor-enabled": False,
            "compressor-threshold": 60.0,
            "compressor-ratio": 4.0,
            "effects": [],
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
    _LOGGER.info("Settings saved")


def update_settings(updates: Dict[str, Any]) -> Dict[str, Any]:
    settings = load_settings()
    settings_data = settings.setdefault("settings", {})
    settings_data.update(updates)
    save_settings(settings)
    return settings


def _next_id(items: List[Dict[str, Any]]) -> int:
    max_id = 0
    for item in items:
        try:
            max_id = max(max_id, int(item.get("id", 0)))
        except (TypeError, ValueError):
            continue
    return max_id + 1


def load_profiles() -> Dict[str, Any]:
    if not _PROFILES_PATH.exists():
        return DEFAULT_PROFILES.copy()
    with _PROFILES_PATH.open("r", encoding="utf-8") as profiles_file:
        return json.load(profiles_file)


def save_profiles(profiles: Dict[str, Any]) -> None:
    _PROFILES_PATH.parent.mkdir(parents=True, exist_ok=True)
    with _PROFILES_PATH.open("w", encoding="utf-8") as profiles_file:
        json.dump(profiles, profiles_file, ensure_ascii=False, indent=2)
    _LOGGER.info("Profiles saved")


def list_profiles() -> List[Dict[str, Any]]:
    return load_profiles().get("profiles", [])


def get_profile_by_id(profile_id: int) -> Optional[Dict[str, Any]]:
    for profile in list_profiles():
        if profile.get("id") == profile_id:
            return profile
    return None


def create_profile(
    name: str,
    images: List[Dict[str, Any]],
    blink: Optional[Dict[str, Any]] = None,
    blink_images: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    profiles_data = load_profiles()
    profiles = profiles_data.setdefault("profiles", [])
    new_profile = {
        "id": _next_id(profiles),
        "name": name,
        "images": images,
        "blink": blink or {},
        "blink-images": blink_images or [],
    }
    profiles.append(new_profile)
    save_profiles(profiles_data)
    _LOGGER.info("Profile created: id=%s name=%s", new_profile.get("id"), new_profile.get("name"))
    return new_profile


def update_profile(updated_profile: Dict[str, Any]) -> None:
    profiles_data = load_profiles()
    profiles = profiles_data.setdefault("profiles", [])
    for idx, profile in enumerate(profiles):
        if profile.get("id") == updated_profile.get("id"):
            profiles[idx] = updated_profile
            save_profiles(profiles_data)
            _LOGGER.info(
                "Profile updated: id=%s name=%s",
                updated_profile.get("id"),
                updated_profile.get("name"),
            )
            return
    profiles.append(updated_profile)
    save_profiles(profiles_data)
    _LOGGER.info(
        "Profile inserted: id=%s name=%s",
        updated_profile.get("id"),
        updated_profile.get("name"),
    )


def delete_profile(profile_id: int) -> None:
    profiles_data = load_profiles()
    profiles = profiles_data.setdefault("profiles", [])
    profiles_data["profiles"] = [p for p in profiles if p.get("id") != profile_id]
    save_profiles(profiles_data)
    _LOGGER.info("Profile deleted: id=%s", profile_id)


def _seed_default_sound_profiles() -> Dict[str, Any]:
    legacy_settings = load_settings().get("settings", {})
    profiles = json.loads(json.dumps(DEFAULT_SOUND_PROFILES))
    profile = profiles["sound-profiles"][0]
    profile["host-api"] = legacy_settings.get("host-api")
    profile["unnoised"] = bool(legacy_settings.get("unnoised", False))
    legacy_microphone = legacy_settings.get("microphone")
    if isinstance(legacy_microphone, str) and legacy_microphone:
        profile["microphone-name"] = legacy_microphone
    return profiles


def load_sound_profiles() -> Dict[str, Any]:
    if not _SOUND_PROFILES_PATH.exists():
        return _seed_default_sound_profiles()
    with _SOUND_PROFILES_PATH.open("r", encoding="utf-8") as sound_profiles_file:
        return json.load(sound_profiles_file)


def save_sound_profiles(sound_profiles: Dict[str, Any]) -> None:
    _SOUND_PROFILES_PATH.parent.mkdir(parents=True, exist_ok=True)
    with _SOUND_PROFILES_PATH.open("w", encoding="utf-8") as sound_profiles_file:
        json.dump(sound_profiles, sound_profiles_file, ensure_ascii=False, indent=2)
    _LOGGER.info("Sound profiles saved")


def list_sound_profiles() -> List[Dict[str, Any]]:
    return load_sound_profiles().get("sound-profiles", [])


def get_sound_profile_by_id(profile_id: int) -> Optional[Dict[str, Any]]:
    for profile in list_sound_profiles():
        if profile.get("id") == profile_id:
            return profile
    return None


def create_sound_profile(
    name: str,
    host_api: Optional[int] = None,
    microphone: Optional[int] = None,
    microphone_name: str = "Default",
    unnoised: bool = False,
    noise_algorithm: str = "adaptive",
    noise_threshold: float = 15.0,
    compressor_enabled: bool = False,
    compressor_threshold: float = 60.0,
    compressor_ratio: float = 4.0,
    effects: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    profiles_data = load_sound_profiles()
    profiles = profiles_data.setdefault("sound-profiles", [])
    new_profile = {
        "id": _next_id(profiles),
        "name": name,
        "host-api": host_api,
        "microphone": microphone,
        "microphone-name": microphone_name,
        "unnoised": unnoised,
        "noise-algorithm": noise_algorithm,
        "noise-threshold": noise_threshold,
        "compressor-enabled": compressor_enabled,
        "compressor-threshold": compressor_threshold,
        "compressor-ratio": compressor_ratio,
        "effects": effects or [],
    }
    profiles.append(new_profile)
    save_sound_profiles(profiles_data)
    _LOGGER.info("Sound profile created: id=%s name=%s", new_profile.get("id"), new_profile.get("name"))
    return new_profile


def update_sound_profile(updated_profile: Dict[str, Any]) -> None:
    profiles_data = load_sound_profiles()
    profiles = profiles_data.setdefault("sound-profiles", [])
    for idx, profile in enumerate(profiles):
        if profile.get("id") == updated_profile.get("id"):
            profiles[idx] = updated_profile
            save_sound_profiles(profiles_data)
            _LOGGER.info(
                "Sound profile updated: id=%s name=%s",
                updated_profile.get("id"),
                updated_profile.get("name"),
            )
            return
    profiles.append(updated_profile)
    save_sound_profiles(profiles_data)
    _LOGGER.info(
        "Sound profile inserted: id=%s name=%s",
        updated_profile.get("id"),
        updated_profile.get("name"),
    )


def delete_sound_profile(profile_id: int) -> None:
    profiles_data = load_sound_profiles()
    profiles = profiles_data.setdefault("sound-profiles", [])
    profiles_data["sound-profiles"] = [p for p in profiles if p.get("id") != profile_id]
    save_sound_profiles(profiles_data)
    _LOGGER.info("Sound profile deleted: id=%s", profile_id)
