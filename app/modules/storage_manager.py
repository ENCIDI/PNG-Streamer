import copy
import json
import os
import shutil
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from app import paths
from app.modules import logging_manager as logm


_LOGGER = logm.get_logger(__name__)

_SETTINGS_FILE = "settings.json"
_PROFILES_FILE = "profiles.json"
_SOUND_PROFILES_FILE = "sound_profiles.json"
_DATA_FILES = (_SETTINGS_FILE, _PROFILES_FILE, _SOUND_PROFILES_FILE)
_MAX_BACKUPS = 10

# The preview and the OBS widget read the active profile many times per second,
# so parsed files are cached until their mtime/size changes.
_CACHE: Dict[Path, Tuple[Tuple[int, int], Any]] = {}

# Bump together with a new entry in _MIGRATIONS when the data format changes.
# Each migration upgrades the files in DATA_DIR from version (key - 1) to key.
SCHEMA_VERSION = 1
_MIGRATIONS: Dict[int, Callable[[], None]] = {}


DEFAULT_SETTINGS: Dict[str, Any] = {
    "schema-version": SCHEMA_VERSION,
    "settings": {
        "active-image-profile-id": 1,
        "active-sound-profile-id": 1,
        "server-port": 8642,
        "show-console": False,
        "minimize-to-tray-on-close": True,
        "start-minimized": False,
        "start-server-on-launch": False,
        "check-updates": True,
        "last-update-check": 0,
        "skipped-version": "",
        "tray-hint-shown": False,
        "window-geometry": "",
    },
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

IMAGE_PROFILE_TEMPLATE: Dict[str, Any] = {
    "images": [],
    "blink": {
        "interval-min-ms": 2000,
        "interval-max-ms": 5000,
        "duration-ms": 100,
    },
    "blink-images": [],
}

SOUND_PROFILE_TEMPLATE: Dict[str, Any] = {
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

DEFAULT_SOUND_PROFILES: Dict[str, Any] = {
    "sound-profiles": [
        {"id": 1, "name": "default", **SOUND_PROFILE_TEMPLATE},
    ]
}


def _settings_path() -> Path:
    return paths.DATA_DIR / _SETTINGS_FILE


def _profiles_path() -> Path:
    return paths.DATA_DIR / _PROFILES_FILE


def _sound_profiles_path() -> Path:
    return paths.DATA_DIR / _SOUND_PROFILES_FILE


def _merge(defaults: Any, stored: Any) -> Any:
    if not isinstance(defaults, dict) or not isinstance(stored, dict):
        return copy.deepcopy(stored)
    merged = copy.deepcopy(defaults)
    for key, value in stored.items():
        merged[key] = _merge(merged[key], value) if key in merged else copy.deepcopy(value)
    return merged


def _read_json(path: Path) -> Optional[Any]:
    try:
        stat = path.stat()
    except OSError:
        return None
    signature = (stat.st_mtime_ns, stat.st_size)
    cached = _CACHE.get(path)
    if cached is not None and cached[0] == signature:
        return copy.deepcopy(cached[1])
    try:
        with path.open("r", encoding="utf-8") as json_file:
            data = json.load(json_file)
        _CACHE[path] = (signature, data)
        return copy.deepcopy(data)
    except (OSError, ValueError):
        _CACHE.pop(path, None)
        broken = path.with_name(f"{path.name}.broken-{time.strftime('%Y%m%d-%H%M%S')}")
        _LOGGER.exception("Failed to read %s, moving it to %s", path, broken.name)
        try:
            path.replace(broken)
        except OSError:
            _LOGGER.exception("Failed to move broken file %s", path)
        return None


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_name(f"{path.name}.tmp")
    with tmp_path.open("w", encoding="utf-8") as json_file:
        json.dump(data, json_file, ensure_ascii=False, indent=2)
        json_file.flush()
        os.fsync(json_file.fileno())
    os.replace(tmp_path, path)
    _CACHE.pop(path, None)


def backup_data(label: str) -> Optional[Path]:
    files = [paths.DATA_DIR / name for name in _DATA_FILES if (paths.DATA_DIR / name).exists()]
    if not files:
        return None
    target = paths.BACKUPS_DIR / f"{time.strftime('%Y%m%d-%H%M%S')}-{label}"
    target.mkdir(parents=True, exist_ok=True)
    for file in files:
        shutil.copy2(file, target / file.name)
    backups = sorted(p for p in paths.BACKUPS_DIR.iterdir() if p.is_dir())
    for old in backups[:-_MAX_BACKUPS]:
        shutil.rmtree(old, ignore_errors=True)
    _LOGGER.info("Data backed up to %s", target)
    return target


def _migrate_legacy_files() -> None:
    for name in _DATA_FILES:
        target = paths.DATA_DIR / name
        legacy = paths.LEGACY_STORAGE_DIR / name
        if target.exists() or not legacy.exists():
            continue
        shutil.copy2(legacy, target)
        _LOGGER.info("Migrated %s from %s", name, legacy.parent)

    if not paths.IMAGES_DIR.exists():
        if paths.LEGACY_IMAGES_DIR.is_dir():
            shutil.copytree(paths.LEGACY_IMAGES_DIR, paths.IMAGES_DIR)
            _LOGGER.info("Migrated images from %s", paths.LEGACY_IMAGES_DIR)
        elif (paths.DEFAULTS_DIR / "images").is_dir():
            shutil.copytree(paths.DEFAULTS_DIR / "images", paths.IMAGES_DIR)
            _LOGGER.info("Seeded sample images")
        else:
            paths.IMAGES_DIR.mkdir(parents=True, exist_ok=True)


def _seed_missing_files() -> None:
    if not _profiles_path().exists():
        seed = _read_json(paths.DEFAULTS_DIR / _PROFILES_FILE)
        save_profiles(seed if seed is not None else copy.deepcopy(DEFAULT_PROFILES))
    if not _sound_profiles_path().exists():
        save_sound_profiles(_seed_default_sound_profiles())


def _run_schema_migrations() -> None:
    raw_settings = _read_json(_settings_path())
    if raw_settings is None:
        save_settings(copy.deepcopy(DEFAULT_SETTINGS))
        return
    try:
        current = int(raw_settings.get("schema-version", 0))
    except (TypeError, ValueError, AttributeError):
        current = 0
    if current >= SCHEMA_VERSION:
        return
    backup_data(f"schema-{current}")
    for version in range(current + 1, SCHEMA_VERSION + 1):
        migration = _MIGRATIONS.get(version)
        if migration is not None:
            migration()
            _LOGGER.info("Applied data migration to schema %s", version)
    settings = load_settings()
    settings["schema-version"] = SCHEMA_VERSION
    save_settings(settings)


def init_storage() -> None:
    paths.DATA_DIR.mkdir(parents=True, exist_ok=True)
    _migrate_legacy_files()
    # Sound profiles are seeded from legacy settings, so settings go first.
    _run_schema_migrations()
    _seed_missing_files()
    _LOGGER.info("Storage ready at %s", paths.DATA_DIR)


def load_settings() -> Dict[str, Any]:
    stored = _read_json(_settings_path())
    if not isinstance(stored, dict):
        return copy.deepcopy(DEFAULT_SETTINGS)
    return _merge(DEFAULT_SETTINGS, stored)


def save_settings(settings: Dict[str, Any]) -> None:
    _write_json(_settings_path(), settings)
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


def _with_template(items: Any, template: Dict[str, Any]) -> List[Dict[str, Any]]:
    if not isinstance(items, list):
        return []
    return [_merge(template, item) for item in items if isinstance(item, dict)]


def load_profiles() -> Dict[str, Any]:
    stored = _read_json(_profiles_path())
    if not isinstance(stored, dict):
        return copy.deepcopy(DEFAULT_PROFILES)
    stored["profiles"] = _with_template(stored.get("profiles"), IMAGE_PROFILE_TEMPLATE)
    return stored


def save_profiles(profiles: Dict[str, Any]) -> None:
    _write_json(_profiles_path(), profiles)
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
    profiles = copy.deepcopy(DEFAULT_SOUND_PROFILES)
    profile = profiles["sound-profiles"][0]
    profile["host-api"] = legacy_settings.get("host-api")
    profile["unnoised"] = bool(legacy_settings.get("unnoised", False))
    legacy_microphone = legacy_settings.get("microphone")
    if isinstance(legacy_microphone, str) and legacy_microphone:
        profile["microphone-name"] = legacy_microphone
    return profiles


def load_sound_profiles() -> Dict[str, Any]:
    stored = _read_json(_sound_profiles_path())
    if not isinstance(stored, dict):
        return _seed_default_sound_profiles()
    stored["sound-profiles"] = _with_template(stored.get("sound-profiles"), SOUND_PROFILE_TEMPLATE)
    return stored


def save_sound_profiles(sound_profiles: Dict[str, Any]) -> None:
    _write_json(_sound_profiles_path(), sound_profiles)
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
