from pathlib import Path
from typing import Any, Dict, List, Optional

from app.modules import audio_manager as am, storage_manager as sm


_IMAGES_DIR = Path(__file__).resolve().parent.parent.parent / "images"


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
        normalized.append(
            {
                "id": image.get("id"),
                "path-to-image": path_value,
                "volume-level": volume_level,
            }
        )
    return normalized


def pick_image_for_volume(profile: Dict[str, Any], volume: float) -> Optional[Path]:
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
    return _resolve_image_path(str(selected.get("path-to-image", "")))


def get_current_image_path(volume: Optional[float] = None) -> Optional[Path]:
    profile = get_active_profile()
    if not profile:
        return None
    current_volume = am.get_current_volume() if volume is None else volume
    return pick_image_for_volume(profile, current_volume)
