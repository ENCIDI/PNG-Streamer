"""Global hotkeys for Studio parameters (triggers and toggles).

Windows: RegisterHotKey on a dedicated thread with its own message loop.
Linux: there is no portable way for an app to grab keys on Wayland, so the UI
offers a command (curl to the control API) that the user binds in the system
keyboard settings instead; see shortcut_command().
"""
import sys
import threading
from typing import Dict, List, Optional, Tuple

from PySide6.QtCore import QObject, Qt, Signal
from PySide6.QtGui import QKeySequence
from PySide6.QtWidgets import QKeySequenceEdit, QLineEdit

from app.modules import logging_manager as logm, logic_manager as lm

_LOGGER = logm.get_logger(__name__)

SUPPORTED = sys.platform == "win32"

Binding = str  # param id of the active Studio avatar


def shortcut_command(param_id: str, port: int) -> str:
    return f"curl -fsS -X POST http://127.0.0.1:{port}/api/param/{param_id}"


def _active_params() -> List[Dict]:
    from app.modules.studio_bridge import bound_params

    return bound_params(lm.get_active_image_profile())


def collect_bindings() -> Dict[str, Binding]:
    """Press hotkeys: fire triggers, toggle bools (hold-mode keys are polled instead)."""
    bindings: Dict[str, Binding] = {}
    for param in _active_params():
        hotkey = str(param.get("hotkey") or "").strip()
        if hotkey and hotkey not in bindings and not (param["type"] == "bool" and param.get("hotkey_mode") == "hold"):
            bindings[hotkey] = param["id"]
    return bindings


def collect_held() -> Dict[str, int]:
    """Bools in "hold" mode: param id -> virtual key, polled every frame."""
    held = {}
    for param in _active_params():
        if param["type"] == "bool" and param.get("hotkey_mode") == "hold" and param.get("hotkey"):
            parsed = to_windows(param["hotkey"])
            if parsed is not None:
                held[param["id"]] = parsed[1]
    return held


# --- Windows key mapping -------------------------------------------------------
_MOD_ALT, _MOD_CONTROL, _MOD_SHIFT, _MOD_WIN, _MOD_NOREPEAT = 0x1, 0x2, 0x4, 0x8, 0x4000

_SPECIAL_KEYS = {
    Qt.Key_Space: 0x20, Qt.Key_PageUp: 0x21, Qt.Key_PageDown: 0x22, Qt.Key_End: 0x23, Qt.Key_Home: 0x24,
    Qt.Key_Left: 0x25, Qt.Key_Up: 0x26, Qt.Key_Right: 0x27, Qt.Key_Down: 0x28, Qt.Key_Print: 0x2C,
    Qt.Key_Insert: 0x2D, Qt.Key_Delete: 0x2E, Qt.Key_Pause: 0x13, Qt.Key_Tab: 0x09,
    Qt.Key_Backspace: 0x08, Qt.Key_Return: 0x0D, Qt.Key_Enter: 0x0D, Qt.Key_Escape: 0x1B,
}
_NUMPAD = {
    Qt.Key_Asterisk: 0x6A, Qt.Key_Plus: 0x6B, Qt.Key_Minus: 0x6D, Qt.Key_Period: 0x6E, Qt.Key_Slash: 0x6F,
}


def to_windows(hotkey: str) -> Optional[Tuple[int, int]]:
    """Qt portable key text ("Ctrl+Shift+F1") -> (modifiers, virtual key)."""
    sequence = QKeySequence(hotkey, QKeySequence.PortableText)
    if sequence.isEmpty():
        return None
    combination = sequence[0]
    key = combination.key()
    modifiers = combination.keyboardModifiers()
    mods = _MOD_NOREPEAT
    if modifiers & Qt.AltModifier:
        mods |= _MOD_ALT
    if modifiers & Qt.ControlModifier:
        mods |= _MOD_CONTROL
    if modifiers & Qt.ShiftModifier:
        mods |= _MOD_SHIFT
    if modifiers & Qt.MetaModifier:
        mods |= _MOD_WIN
    keypad = bool(modifiers & Qt.KeypadModifier)
    if Qt.Key_F1 <= key <= Qt.Key_F24:
        return mods, 0x70 + (key - Qt.Key_F1)
    if Qt.Key_0 <= key <= Qt.Key_9:
        return mods, (0x60 if keypad else 0x30) + (key - Qt.Key_0)
    if Qt.Key_A <= key <= Qt.Key_Z:
        return mods, 0x41 + (key - Qt.Key_A)
    if keypad and key in _NUMPAD:
        return mods, _NUMPAD[key]
    if key in _SPECIAL_KEYS:
        return mods, _SPECIAL_KEYS[key]
    if 0x20 < int(key) < 0x7F and sys.platform == "win32":
        import ctypes

        scan = ctypes.windll.user32.VkKeyScanW(int(key))
        if scan != -1:
            return mods, scan & 0xFF
    return None


class _WindowsHotkeyThread(threading.Thread):
    _WM_HOTKEY = 0x0312
    _WM_APP_RELOAD = 0x8000 + 1
    _WM_QUIT = 0x0012

    def __init__(self, on_hotkey, on_failed):
        super().__init__(daemon=True, name="hotkeys")
        self._on_hotkey = on_hotkey
        self._on_failed = on_failed
        self._pending: Dict[str, Binding] = {}
        self._lock = threading.Lock()
        self._ready = threading.Event()
        self._thread_id = 0

    def run(self) -> None:
        import ctypes
        from ctypes import wintypes

        user32 = ctypes.windll.user32
        user32.RegisterHotKey.argtypes = [wintypes.HWND, ctypes.c_int, wintypes.UINT, wintypes.UINT]
        user32.GetMessageW.argtypes = [ctypes.POINTER(wintypes.MSG), wintypes.HWND, wintypes.UINT, wintypes.UINT]
        self._thread_id = ctypes.windll.kernel32.GetCurrentThreadId()
        msg = wintypes.MSG()
        # Make sure the thread has a message queue before anyone posts to it.
        user32.PeekMessageW(ctypes.byref(msg), None, 0, 0, 0)
        self._ready.set()
        registered: Dict[int, Binding] = {}
        self._register(user32, registered)
        while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
            if msg.message == self._WM_HOTKEY and msg.wParam in registered:
                self._on_hotkey(registered[msg.wParam])
            elif msg.message == self._WM_APP_RELOAD:
                self._register(user32, registered)
        for hotkey_id in registered:
            user32.UnregisterHotKey(None, hotkey_id)

    def _register(self, user32, registered: Dict[int, Binding]) -> None:
        for hotkey_id in list(registered):
            user32.UnregisterHotKey(None, hotkey_id)
        registered.clear()
        with self._lock:
            bindings = dict(self._pending)
        failed: List[str] = []
        for index, (hotkey, binding) in enumerate(bindings.items(), start=1):
            parsed = to_windows(hotkey)
            if parsed is None or not user32.RegisterHotKey(None, index, parsed[0], parsed[1]):
                failed.append(hotkey)
                continue
            registered[index] = binding
        _LOGGER.info("Hotkeys registered: %s, failed: %s", len(registered), failed)
        self._on_failed(failed)

    def update(self, bindings: Dict[str, Binding]) -> None:
        import ctypes

        with self._lock:
            self._pending = dict(bindings)
        self._ready.wait(2)
        ctypes.windll.user32.PostThreadMessageW(self._thread_id, self._WM_APP_RELOAD, 0, 0)

    def stop(self) -> None:
        import ctypes

        if self._thread_id:
            ctypes.windll.user32.PostThreadMessageW(self._thread_id, self._WM_QUIT, 0, 0)


class HotkeyManager(QObject):
    triggered = Signal(str)  # param id
    failed_changed = Signal(list)

    def __init__(self):
        super().__init__()
        self.failed: List[str] = []
        self._thread: Optional[_WindowsHotkeyThread] = None
        if SUPPORTED:
            self._thread = _WindowsHotkeyThread(self.triggered.emit, self._set_failed)
            self._thread.start()
            self.reload()

    def _set_failed(self, failed: List[str]) -> None:
        self.failed = failed
        self.failed_changed.emit(failed)

    def reload(self) -> None:
        if self._thread is not None:
            self._thread.update(collect_bindings())
            from app.modules.studio_bridge import service

            service.set_held_keys(collect_held())

    def stop(self) -> None:
        if self._thread is not None:
            self._thread.stop()


class HotkeyEdit(QKeySequenceEdit):
    """Captures a single key combination; stored as Qt portable text."""

    def __init__(self):
        super().__init__()
        self.setMaximumSequenceLength(1)
        self.setClearButtonEnabled(True)
        self.setMinimumWidth(150)

    def set_placeholder(self, text: str) -> None:
        editor = self.findChild(QLineEdit)
        if editor is not None:
            editor.setPlaceholderText(text)

    def value(self) -> str:
        return self.keySequence().toString(QKeySequence.PortableText)

    def set_value(self, text: str) -> None:
        self.blockSignals(True)
        self.setKeySequence(QKeySequence(text or "", QKeySequence.PortableText))
        self.blockSignals(False)
