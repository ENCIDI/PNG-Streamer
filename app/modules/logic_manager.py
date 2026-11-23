from pathlib import Path
import random
import shutil
import threading
import time
from typing import Any, Dict, List, Optional, Tuple

from app import features, paths
from app.modules import audio_manager as am, storage_manager as sm


_BLINK_LOCK = threading.Lock()
_BLINK_SIGNATURE: Optional[Tuple[Any, int, int, int]] = None
_BLINK_NEXT_AT = 0.0
_BLINK_UNTIL = 0.0

# _REVISION changes whenever something is switched outside of the UI (API,
# hotkeys, Studio parameters), so the UI can refresh.
_STATE_LOCK = threading.RLock()
_REVISION = 0


IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".webp"}


def list_available_images() -> List[str]:
    if not paths.IMAGES_DIR.exists():
        return []
    images = []
    for path in paths.IMAGES_DIR.iterdir():
        if path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES:
            images.append(path.name)
    return sorted(images, key=str.lower)


def import_images(files: List[Path]) -> List[str]:
    """Copy image files into the images folder, renaming on name clashes."""
    paths.IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    imported = []
    for source in files:
        source = Path(source)
        if not source.is_file() or source.suffix.lower() not in IMAGE_SUFFIXES:
            continue
        if source.resolve().parent == paths.IMAGES_DIR.resolve():
            imported.append(source.name)
            continue
        target = paths.IMAGES_DIR / source.name
        counter = 2
        while target.exists():
            target = paths.IMAGES_DIR / f"{source.stem}-{counter}{source.suffix}"
            counter += 1
        shutil.copy2(source, target)
        imported.append(target.name)
    return imported


def active_image_profile_id() -> int:
    settings = sm.load_settings().get("settings", {})
    try:
        return int(settings.get("active-image-profile-id", 1))
    except (TypeError, ValueError):
        return 1


def get_active_image_profile() -> Optional[Dict[str, Any]]:
    return sm.get_profile_by_id(active_image_profile_id())


def _bump() -> None:
    global _REVISION
    _REVISION += 1


def revision() -> int:
    return _REVISION


def notify_changed() -> None:
    """Tell the UI that something changed outside of it (API, hotkeys)."""
    with _STATE_LOCK:
        _bump()


def activate_image_profile(profile_id: int) -> bool:
    if sm.get_profile_by_id(profile_id) is None:
        return False
    with _STATE_LOCK:
        sm.update_settings({"active-image-profile-id": profile_id})
        _bump()
    return True


def is_advanced(profile: Optional[Dict[str, Any]]) -> bool:
    # Without the Studio an advanced profile plays its frames like a simple one.
    return features.STUDIO and (profile or {}).get("mode") == "advanced"


def find_image_profile(key: Any) -> Optional[Dict[str, Any]]:
    """Look a profile up by id or (case-insensitive) name."""
    profiles = sm.list_profiles()
    text = str(key).strip()
    found = next((p for p in profiles if str(p.get("id")) == text), None)
    if found is None:
        found = next((p for p in profiles if str(p.get("name", "")).casefold() == text.casefold()), None)
    return found


def referenced_images(profile: Dict[str, Any]) -> List[str]:
    """Image files a simple profile uses (frames and blink frames)."""
    names: List[str] = []
    for item in list((profile or {}).get("images", [])) + list((profile or {}).get("blink-images", [])):
        value = str(item.get("path-to-image", "")).strip() if isinstance(item, dict) else ""
        if value and value not in names:
            names.append(value)
    return names


def get_active_sound_profile() -> Optional[Dict[str, Any]]:
    settings = sm.load_settings().get("settings", {})
    active_id = settings.get("active-sound-profile-id", 1)
    try:
        active_id = int(active_id)
    except (TypeError, ValueError):
        active_id = 1
    return sm.get_sound_profile_by_id(active_id)


def apply_sound_profile(profile: Dict[str, Any]) -> None:
    am.set_noise_suppression(bool(profile.get("unnoised", False)))
    am.set_noise_algorithm(profile.get("noise-algorithm", "adaptive"))
    am.set_noise_threshold(profile.get("noise-threshold", 15.0))
    am.set_compressor(bool(profile.get("compressor-enabled", False)))
    am.set_compressor_threshold(profile.get("compressor-threshold", 60.0))
    am.set_compressor_ratio(profile.get("compressor-ratio", 4.0))
    am.start_monitor(profile.get("microphone"))


def activate_sound_profile(profile_id: int) -> None:
    sm.update_settings({"active-sound-profile-id": profile_id})
    profile = sm.get_sound_profile_by_id(profile_id)
    if profile:
        apply_sound_profile(profile)


def resolve_image_path(image_value: str) -> Optional[Path]:
    if not image_value:
        return None
    candidate = Path(image_value)
    if candidate.is_absolute():
        return candidate if candidate.exists() else None
    if paths.IMAGES_DIR.exists():
        joined = paths.IMAGES_DIR / image_value
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


def sorted_frames(profile: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Frames of a simple profile ordered by threshold."""
    return sorted(_normalize_images(profile.get("images", [])), key=lambda item: item.get("volume-level", 0))


def pick_frame(profile: Dict[str, Any], volume: float) -> Optional[Dict[str, Any]]:
    return _pick_image_entry(profile, volume)


def blink_settings(profile: Dict[str, Any]) -> Tuple[int, int, int]:
    return _blink_settings(profile)


def blink_image_path(profile: Dict[str, Any], image_id: Optional[int]) -> Optional[Path]:
    return _pick_blink_image(profile, image_id)


def pick_image_for_volume(profile: Dict[str, Any], volume: float) -> Optional[Path]:
    selected = _pick_image_entry(profile, volume)
    if not selected:
        return None
    return resolve_image_path(str(selected.get("path-to-image", "")))


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
    return resolve_image_path(path_value)


def compute_state(volume: Optional[float] = None, profile: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """What a simple profile shows right now; used by the preview and the OBS widget."""
    profile = profile if profile is not None else get_active_image_profile()
    current_volume = am.get_current_volume() if volume is None else volume
    state: Dict[str, Any] = {
        "profile": profile.get("id") if profile else None,
        "frame": None,
        "level": 0,
        "image": None,
        "shake": 0,
        "speaking": False,
        "blink": False,
        "volume": round(float(current_volume), 1),
    }
    if profile is None or is_advanced(profile):
        return state
    frames = sorted_frames(profile)
    selected = _pick_image_entry(profile, current_volume)
    if selected is None:
        return state
    index = next((i for i, frame in enumerate(frames) if frame == selected), 0)
    state.update(
        frame=index,
        level=selected.get("volume-level", 0),
        image=selected.get("path-to-image"),
        shake=max(0, int(selected.get("shake-level", 0) or 0)),
        speaking=index > 0,
    )
    if _should_blink(profile):
        blink = _normalize_blink_images(profile.get("blink-images", [])).get(selected.get("id"))
        if blink and resolve_image_path(blink) is not None:
            state["image"] = blink
            state["blink"] = True
    return state


def get_current_image_state(volume: Optional[float] = None) -> Tuple[Optional[Path], int]:
    state = compute_state(volume)
    return resolve_image_path(state["image"] or ""), state["shake"]


def get_current_image_path(volume: Optional[float] = None) -> Optional[Path]:
    path, _ = get_current_image_state(volume)
    return path
