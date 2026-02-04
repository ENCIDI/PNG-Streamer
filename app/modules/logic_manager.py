from pathlib import Path
import random
import threading
import time
from typing import Any, Dict, List, Optional, Tuple

from app.modules import audio_manager as am, storage_manager as sm


_IMAGES_DIR = Path(__file__).resolve().parent.parent.parent / "images"
_BLINK_LOCK = threading.Lock()
_BLINK_SIGNATURE: Optional[Tuple[Any, int, int, int]] = None
_BLINK_NEXT_AT = 0.0
_BLINK_UNTIL = 0.0


def list_available_images() -> List[str]:
    if not _IMAGES_DIR.exists():
        return []
    images = []
    for path in _IMAGES_DIR.iterdir():
        if path.is_file() and path.suffix.lower() in {".png", ".jpg", ".jpeg", ".gif"}:
            images.append(path.name)
    return sorted(images)


def get_active_profile() -> Optional[Dict[str, Any]]:
    settings = sm.load_settings().get("settings", {})
    active_id = settings.get("active-profile-id", 1)
    try:
        active_id = int(active_id)
    except (TypeError, ValueError):
        active_id = 1
    return sm.get_profile_by_id(active_id)


def _resolve_image_path(image_value: str) -> Optional[Path]:
    if not image_value:
        return None
    candidate = Path(image_value)
    if candidate.is_absolute():
        return candidate if candidate.exists() else None
    if _IMAGES_DIR.exists():
        joined = _IMAGES_DIR / image_value
        if joined.exists():
            return joined
    return None


def _normalize_images(images: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    normalized = []
    for image in images:
        if not isinstance(image, dict):
            continue
        path_value = str(image.get("path-to-image", "")).strip()
        if not path_value:
            continue
        try:
            volume_level = int(image.get("volume-level", 0))
        except (TypeError, ValueError):
            volume_level = 0
        try:
            shake_level = int(image.get("shake-level", 0))
        except (TypeError, ValueError):
            shake_level = 0
        if shake_level < 0:
            shake_level = 0
        normalized.append(
            {
                "id": image.get("id"),
                "path-to-image": path_value,
                "volume-level": volume_level,
                "shake-level": shake_level,
            }
        )
    return normalized


def _pick_image_entry(profile: Dict[str, Any], volume: float) -> Optional[Dict[str, Any]]:
    images = _normalize_images(profile.get("images", []))
    if not images:
        return None
    images_sorted = sorted(images, key=lambda item: item.get("volume-level", 0))
    selected = None
    for image in images_sorted:
        if volume >= image.get("volume-level", 0):
            selected = image
        else:
            break
    if selected is None:
        selected = images_sorted[0]
    return selected


def pick_image_for_volume(profile: Dict[str, Any], volume: float) -> Optional[Path]:
    selected = _pick_image_entry(profile, volume)
    if not selected:
        return None
    return _resolve_image_path(str(selected.get("path-to-image", "")))


def _normalize_blink_images(images: List[Dict[str, Any]]) -> Dict[int, str]:
    normalized: Dict[int, str] = {}
    for image in images:
        if not isinstance(image, dict):
            continue
        try:
            image_id = int(image.get("id", -1))
        except (TypeError, ValueError):
            continue
        path_value = str(image.get("path-to-image", "")).strip()
        if not path_value:
            continue
        normalized[image_id] = path_value
    return normalized


def _blink_settings(profile: Dict[str, Any]) -> Tuple[int, int, int]:
    blink = profile.get("blink", {}) if isinstance(profile.get("blink", {}), dict) else {}
    try:
        min_ms = int(blink.get("interval-min-ms", 0))
    except (TypeError, ValueError):
        min_ms = 0
    try:
        max_ms = int(blink.get("interval-max-ms", 0))
    except (TypeError, ValueError):
        max_ms = 0
    try:
        duration_ms = int(blink.get("duration-ms", 0))
    except (TypeError, ValueError):
        duration_ms = 0
    if min_ms < 0:
        min_ms = 0
    if max_ms < 0:
        max_ms = 0
    if duration_ms < 0:
        duration_ms = 0
    if max_ms and min_ms and max_ms < min_ms:
        min_ms, max_ms = max_ms, min_ms
    return min_ms, max_ms, duration_ms


def _should_blink(profile: Dict[str, Any]) -> bool:
    global _BLINK_SIGNATURE, _BLINK_NEXT_AT, _BLINK_UNTIL
    min_ms, max_ms, duration_ms = _blink_settings(profile)
    if min_ms <= 0 or max_ms <= 0 or duration_ms <= 0:
        return False
    signature = (profile.get("id"), min_ms, max_ms, duration_ms)
    now = time.monotonic()
    with _BLINK_LOCK:
        if signature != _BLINK_SIGNATURE:
            _BLINK_SIGNATURE = signature
            _BLINK_UNTIL = 0.0
            _BLINK_NEXT_AT = now + random.uniform(min_ms, max_ms) / 1000.0
        if now < _BLINK_UNTIL:
            return True
        if now >= _BLINK_NEXT_AT:
            _BLINK_UNTIL = now + duration_ms / 1000.0
            _BLINK_NEXT_AT = now + random.uniform(min_ms, max_ms) / 1000.0
            return True
    return False


def _pick_blink_image(profile: Dict[str, Any], image_id: Optional[int]) -> Optional[Path]:
    if image_id is None:
        return None
    blink_images = _normalize_blink_images(profile.get("blink-images", []))
    path_value = blink_images.get(int(image_id)) if blink_images else None
    if not path_value:
        return None
    return _resolve_image_path(path_value)


def get_current_image_state(volume: Optional[float] = None) -> Tuple[Optional[Path], int]:
    profile = get_active_profile()
    if not profile:
        return None, 0
    current_volume = am.get_current_volume() if volume is None else volume
    selected = _pick_image_entry(profile, current_volume)
    if not selected:
        return None, 0
    base_path = _resolve_image_path(str(selected.get("path-to-image", "")))
    if base_path is None:
        return None, 0
    try:
        shake_level = int(selected.get("shake-level", 0))
    except (TypeError, ValueError):
        shake_level = 0
    if shake_level < 0:
        shake_level = 0
    if _should_blink(profile):
        blink_path = _pick_blink_image(profile, selected.get("id"))
        if blink_path is not None:
            return blink_path, shake_level
    return base_path, shake_level


def get_current_image_path(volume: Optional[float] = None) -> Optional[Path]:
    path, _ = get_current_image_state(volume)
    return path
