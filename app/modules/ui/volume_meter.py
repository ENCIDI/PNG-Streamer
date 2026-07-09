import threading
import time
from typing import Any, Dict, Optional

import flet as ft

from app.modules import audio_manager as am

_FPS = 30
_INTERVAL_SECONDS = 1.0 / _FPS

_state: Dict[str, Any] = {"text": None, "bar": None, "page": None}
_lock = threading.Lock()
_started = False


async def _push(value: float) -> None:
    text = _state.get("text")
    bar = _state.get("bar")
    try:
        if text is not None:
            text.value = str(int(value))
            text.update()
        if bar is not None:
            bar.value = max(min(value / 100.0, 1.0), 0.0)
            bar.update()
    except RuntimeError:
        pass


def _ensure_thread() -> None:
    global _started
    with _lock:
        if _started:
            return
        _started = True

        def _loop() -> None:
            while True:
                page = _state.get("page")
                if page is not None:
                    try:
                        page.run_task(_push, am.get_current_volume())
                    except Exception:
                        pass
                time.sleep(_INTERVAL_SECONDS)

        threading.Thread(target=_loop, daemon=True).start()


def build(page: ft.Page, *, text_size: int = 28, bar_width: Optional[int] = 300) -> ft.Control:
    volume_text = ft.Text("0", size=text_size, weight=ft.FontWeight.BOLD)
    volume_bar = ft.ProgressBar(value=0, width=bar_width, expand=bar_width is None)
    _state["text"] = volume_text
    _state["bar"] = volume_bar
    _state["page"] = page
    _ensure_thread()
    return ft.Row([volume_bar, volume_text])
