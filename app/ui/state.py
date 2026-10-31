from typing import Any, Dict, List, Optional

from PySide6.QtCore import QObject, QTimer, Signal

from app.modules import (
    audio_manager as am,
    logging_manager as logm,
    logic_manager as lm,
    storage_manager as sm,
    web_manager as wm,
)
from app.ui import i18n

_LOGGER = logm.get_logger(__name__)

_VOLUME_FPS = 30
DEFAULT_PORT = 8642
HOST = "127.0.0.1"


def parse_port(value: Any) -> int:
    try:
        port = int(value)
    except (TypeError, ValueError):
        return DEFAULT_PORT
    return port if 1 <= port <= 65535 else DEFAULT_PORT


class AppState(QObject):
    """Single source of truth shared by the window, the screens and the tray."""

    volume_changed = Signal(float)
    server_changed = Signal()
    profiles_changed = Signal()
    microphone_changed = Signal()
    language_changed = Signal()
    images_changed = Signal()
    update_available = Signal(object)
    notify = Signal(str, str)  # message, kind: "info" | "error"

    def __init__(self) -> None:
        super().__init__()
        self._volume = 0.0
        self._mic_error: Optional[str] = am.get_monitor_error()
        self.pending_update: Optional[Any] = None
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._poll)
        self._timer.start(1000 // _VOLUME_FPS)

    def _poll(self) -> None:
        self._volume = am.get_current_volume()
        self.volume_changed.emit(self._volume)
        error = am.get_monitor_error()
        if error != self._mic_error:
            self._mic_error = error
            self.microphone_changed.emit()

    # --- volume / microphone -------------------------------------------------
    @property
    def volume(self) -> float:
        return self._volume

    @property
    def mic_error(self) -> Optional[str]:
        return self._mic_error

    # --- settings ------------------------------------------------------------
    def settings(self) -> Dict[str, Any]:
        return sm.load_settings().get("settings", {})

    def update_settings(self, **updates: Any) -> None:
        sm.update_settings({key.replace("_", "-"): value for key, value in updates.items()})

    # --- server --------------------------------------------------------------
    def port(self) -> int:
        if wm.is_running() and wm.current_port():
            return int(wm.current_port())
        return parse_port(self.settings().get("server-port", DEFAULT_PORT))

    def server_running(self) -> bool:
        return wm.is_running()

    def widget_url(self) -> str:
        return f"http://{HOST}:{self.port()}/widget"

    def start_server(self, port: Optional[int] = None) -> bool:
        port = parse_port(port if port is not None else self.port())
        self.update_settings(server_port=port)
        started, status = wm.start_server(HOST, port)
        self.server_changed.emit()
        if not started and status != "already_running":
            self.notify.emit(i18n.t("launch.server_start_failed", port=port), "error")
            return False
        return True

    def stop_server(self) -> None:
        wm.stop_server()
        self.server_changed.emit()

    # --- profiles ------------------------------------------------------------
    def sound_profiles(self) -> List[Dict[str, Any]]:
        return sm.list_sound_profiles()

    def image_profiles(self) -> List[Dict[str, Any]]:
        return sm.list_profiles()

    def _active_id(self, key: str) -> Optional[int]:
        try:
            return int(self.settings().get(key, 1))
        except (TypeError, ValueError):
            return None

    def active_sound_profile_id(self) -> Optional[int]:
        return self._active_id("active-sound-profile-id")

    def active_image_profile_id(self) -> Optional[int]:
        return self._active_id("active-image-profile-id")

    def active_sound_profile(self) -> Optional[Dict[str, Any]]:
        return lm.get_active_sound_profile()

    def active_image_profile(self) -> Optional[Dict[str, Any]]:
        return lm.get_active_image_profile()

    def set_active_sound_profile(self, profile_id: int) -> None:
        lm.activate_sound_profile(profile_id)
        self.profiles_changed.emit()

    def set_active_image_profile(self, profile_id: int) -> None:
        self.update_settings(active_image_profile_id=profile_id)
        self.profiles_changed.emit()

    def restart_microphone(self) -> None:
        profile = self.active_sound_profile()
        if profile:
            lm.apply_sound_profile(profile)
        self._poll()

    # --- language ------------------------------------------------------------
    def set_language(self, lang: str) -> None:
        if lang == i18n.get_language():
            return
        i18n.set_language(lang)
        self.language_changed.emit()
