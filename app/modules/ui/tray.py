import threading
from typing import Optional

import flet as ft
import pystray
from PIL import Image

from app.modules import audio_manager as am, logging_manager as logm, web_manager as wm
from app.modules.ui import i18n

_LOGGER = logm.get_logger(__name__)

_icon: Optional[pystray.Icon] = None


async def quit_app(page: ft.Page) -> None:
    wm.stop_server()
    am.stop_monitor()
    if _icon is not None:
        _icon.stop()
    await page.window.destroy()


def start(page: ft.Page, icon_path: Optional[str]) -> None:
    global _icon
    if not icon_path:
        return

    async def _restore(page: ft.Page) -> None:
        page.window.visible = True
        page.window.skip_task_bar = False
        await page.window.to_front()
        page.update()

    def _on_show(icon, item) -> None:
        page.run_task(_restore, page)

    def _on_quit(icon, item) -> None:
        page.run_task(quit_app, page)

    _icon = pystray.Icon(
        "PNGStreamer",
        icon=Image.open(icon_path),
        title="PNG Streamer",
        menu=pystray.Menu(
            pystray.MenuItem(lambda item: i18n.t("tray.show"), _on_show, default=True),
            pystray.MenuItem(lambda item: i18n.t("tray.quit"), _on_quit),
        ),
    )
    threading.Thread(target=_icon.run, daemon=True).start()
    _LOGGER.info("Tray icon started")
