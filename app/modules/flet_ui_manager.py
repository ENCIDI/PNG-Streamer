from pathlib import Path
from typing import Optional

import flet as ft

from app.modules import (
    logging_manager as logm,
    logic_manager as lm,
    storage_manager as sm,
)
from app.modules.ui import i18n, image_settings_view, launch_view, sound_settings_view, tray

_LOGGER = logm.get_logger(__name__)

_ICON_PATH = Path(__file__).resolve().parent.parent / "ui" / "PNGStreamer.ico"
_FLAGS_DIR = Path(__file__).resolve().parent.parent / "ui" / "flags"


def _icon_path() -> Optional[str]:
    return str(_ICON_PATH) if _ICON_PATH.exists() else None


def _flag_path(lang: str) -> str:
    return str(_FLAGS_DIR / f"{lang}.png")


def _blob(
    size: float,
    color: str,
    top: Optional[float] = None,
    left: Optional[float] = None,
    right: Optional[float] = None,
    bottom: Optional[float] = None,
    border_radius: Optional[float] = None,
    rotate: Optional[float] = None,
) -> ft.Control:
    return ft.Container(
        width=size,
        height=size,
        top=top,
        left=left,
        right=right,
        bottom=bottom,
        rotate=rotate,
        border_radius=size / 2 if border_radius is None else border_radius,
        blur=70,
        gradient=ft.RadialGradient(
            colors=[ft.Colors.with_opacity(0.35, color), ft.Colors.with_opacity(0.0, color)],
        ),
    )


def _background_geometry() -> ft.Control:
    return ft.Stack(
        controls=[
            _blob(480, ft.Colors.DEEP_PURPLE, top=-180, left=-160),
            _blob(320, ft.Colors.PURPLE, bottom=-120, right=-100),
            _blob(220, ft.Colors.DEEP_PURPLE_ACCENT, top=200, right=40, border_radius=56, rotate=0.5),
        ],
        expand=True,
    )


def _nav_destinations() -> list[ft.NavigationRailDestination]:
    return [
        ft.NavigationRailDestination(
            icon=ft.Icons.PLAY_ARROW_OUTLINED,
            selected_icon=ft.Icons.PLAY_ARROW,
            label=i18n.t("nav.launch"),
        ),
        ft.NavigationRailDestination(
            icon=ft.Icons.MIC_OUTLINED,
            selected_icon=ft.Icons.MIC,
            label=i18n.t("nav.sound"),
        ),
        ft.NavigationRailDestination(
            icon=ft.Icons.IMAGE_OUTLINED,
            selected_icon=ft.Icons.IMAGE,
            label=i18n.t("nav.images"),
        ),
    ]


def main(page: ft.Page) -> None:
    i18n.init_language()
    page.title = "PNG Streamer"
    page.theme_mode = ft.ThemeMode.DARK
    page.theme = ft.Theme(color_scheme_seed=ft.Colors.DEEP_PURPLE)
    page.bgcolor = "#0B0710"
    page.window.width = 1210
    page.window.height = 750
    page.window.min_width = 1210
    page.window.min_height = 750
    page.window.resizable = True

    icon_path = _icon_path()
    if icon_path:
        page.window.icon = icon_path

    page.window.prevent_close = True

    def _on_window_event(e: ft.WindowEvent) -> None:
        if e.type == ft.WindowEventType.CLOSE:
            page.window.visible = False
            page.window.skip_task_bar = True
            page.update()

    page.window.on_event = _on_window_event

    settings = sm.load_settings().get("settings", {})
    active_sound_profile_id = settings.get("active-sound-profile-id", 1)
    try:
        active_sound_profile_id = int(active_sound_profile_id)
    except (TypeError, ValueError):
        active_sound_profile_id = 1
    lm.activate_sound_profile(active_sound_profile_id)

    body = ft.Container(expand=True)

    view_builders = {
        0: launch_view.build,
        1: sound_settings_view.build,
        2: image_settings_view.build,
    }

    def _show(index: int) -> None:
        body.content = view_builders[index](page)
        page.update()

    def _on_nav_change(e: ft.ControlEvent) -> None:
        _show(nav_rail.selected_index)

    language_button = ft.TextButton(
        content=ft.Container(
            padding=4,
            content=ft.Image(
                src=_flag_path(i18n.get_language()),
                width=28,
                height=20,
                fit=ft.BoxFit.CONTAIN,
                border_radius=3,
            ),
        ),
        tooltip="RU / EN",
    )

    def _on_language_toggle(e: ft.ControlEvent) -> None:
        i18n.set_language("en" if i18n.get_language() == "ru" else "ru")
        language_button.content.content.src = _flag_path(i18n.get_language())
        nav_rail.destinations = _nav_destinations()
        _show(nav_rail.selected_index)
        page.update()

    language_button.on_click = _on_language_toggle

    nav_rail = ft.NavigationRail(
        selected_index=0,
        label_type=ft.NavigationRailLabelType.ALL,
        min_width=100,
        bgcolor=ft.Colors.TRANSPARENT,
        destinations=_nav_destinations(),
        trailing=language_button,
        pin_trailing_to_bottom=True,
        on_change=_on_nav_change,
    )

    content_row = ft.Row([nav_rail, ft.VerticalDivider(width=1), body], expand=True)
    page.add(ft.Stack([_background_geometry(), content_row], expand=True))
    _show(0)

    tray.start(page, icon_path)
    _LOGGER.info("UI initialized")


def start_program() -> None:
    ft.run(main)
