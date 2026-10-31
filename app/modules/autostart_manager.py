import os
import shlex
import sys
from pathlib import Path
from typing import List

from app import paths
from app.modules import logging_manager as logm

_LOGGER = logm.get_logger(__name__)

APP_ID = "PNGStreamer"
AUTOSTART_ARG = "--autostart"
_RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"


def launch_command() -> List[str]:
    """Command that starts this exact installation of the app."""
    if paths.is_frozen():
        appimage = os.environ.get("APPIMAGE")
        return [appimage or sys.executable]
    python = Path(sys.executable)
    if sys.platform == "win32" and python.name.lower() == "python.exe":
        windowless = python.with_name("pythonw.exe")
        if windowless.exists():
            python = windowless
    return [str(python), str(paths.APP_ROOT / "main.py")]


def _desktop_file() -> Path:
    config = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config")
    return config / "autostart" / "pngstreamer.desktop"


def is_supported() -> bool:
    return sys.platform == "win32" or sys.platform.startswith("linux")


def is_enabled() -> bool:
    if sys.platform == "win32":
        import winreg

        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _RUN_KEY) as key:
                winreg.QueryValueEx(key, APP_ID)
                return True
        except OSError:
            return False
    if sys.platform.startswith("linux"):
        return _desktop_file().exists()
    return False


def set_enabled(enabled: bool) -> bool:
    try:
        if sys.platform == "win32":
            _set_windows(enabled)
        elif sys.platform.startswith("linux"):
            _set_linux(enabled)
        else:
            return False
    except OSError:
        _LOGGER.exception("Failed to change autostart")
        return False
    _LOGGER.info("Autostart %s", "enabled" if enabled else "disabled")
    return True


def _set_windows(enabled: bool) -> None:
    import subprocess
    import winreg

    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _RUN_KEY, 0, winreg.KEY_SET_VALUE) as key:
        if enabled:
            command = subprocess.list2cmdline(launch_command() + [AUTOSTART_ARG])
            winreg.SetValueEx(key, APP_ID, 0, winreg.REG_SZ, command)
        else:
            try:
                winreg.DeleteValue(key, APP_ID)
            except FileNotFoundError:
                pass


def _set_linux(enabled: bool) -> None:
    desktop = _desktop_file()
    if not enabled:
        desktop.unlink(missing_ok=True)
        return
    desktop.parent.mkdir(parents=True, exist_ok=True)
    command = " ".join(shlex.quote(part) for part in launch_command() + [AUTOSTART_ARG])
    desktop.write_text(
        "[Desktop Entry]\n"
        "Type=Application\n"
        "Name=PNG Streamer\n"
        f"Exec={command}\n"
        "Icon=pngstreamer\n"
        "X-GNOME-Autostart-enabled=true\n"
        "Terminal=false\n",
        encoding="utf-8",
    )


def refresh() -> None:
    """Rewrite the entry so it points at the current location (e.g. after the
    AppImage was moved or the app was reinstalled into another folder)."""
    if is_enabled():
        set_enabled(True)
