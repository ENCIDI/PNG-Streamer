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

_RESIZE_EDGE_SIZE = 6
_RESIZE_CORNER_SIZE = 10


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


def _resize_handles(page: ft.Page) -> list[ft.Control]:
    def _handler(edge: ft.WindowResizeEdge):
        async def _on_pan_start(e: ft.DragStartEvent) -> None:
            await page.window.start_resizing(edge)

        return _on_pan_start

    def _handle(
        edge: ft.WindowResizeEdge,
        cursor: ft.MouseCursor,
        *,
        top: Optional[float] = None,
        left: Optional[float] = None,
        right: Optional[float] = None,
        bottom: Optional[float] = None,
        width: Optional[float] = None,
        height: Optional[float] = None,
    ) -> ft.Control:
        return ft.GestureDetector(
            top=top,
            left=left,
            right=right,
            bottom=bottom,
            width=width,
            height=height,
            mouse_cursor=cursor,
            on_pan_start=_handler(edge),
        )

    e = _RESIZE_EDGE_SIZE
    c = _RESIZE_CORNER_SIZE
    return [
        _handle(ft.WindowResizeEdge.TOP, ft.MouseCursor.RESIZE_UP_DOWN, top=0, left=c, right=c, height=e),
        _handle(ft.WindowResizeEdge.BOTTOM, ft.MouseCursor.RESIZE_UP_DOWN, bottom=0, left=c, right=c, height=e),
        _handle(ft.WindowResizeEdge.LEFT, ft.MouseCursor.RESIZE_LEFT_RIGHT, left=0, top=c, bottom=c, width=e),
        _handle(ft.WindowResizeEdge.RIGHT, ft.MouseCursor.RESIZE_LEFT_RIGHT, right=0, top=c, bottom=c, width=e),
        _handle(ft.WindowResizeEdge.TOP_LEFT, ft.MouseCursor.RESIZE_UP_LEFT_DOWN_RIGHT, top=0, left=0, width=c, height=c),
        _handle(ft.WindowResizeEdge.BOTTOM_RIGHT, ft.MouseCursor.RESIZE_UP_LEFT_DOWN_RIGHT, bottom=0, right=0, width=c, height=c),
        _handle(ft.WindowResizeEdge.TOP_RIGHT, ft.MouseCursor.RESIZE_UP_RIGHT_DOWN_LEFT, top=0, right=0, width=c, height=c),
        _handle(ft.WindowResizeEdge.BOTTOM_LEFT, ft.MouseCursor.RESIZE_UP_RIGHT_DOWN_LEFT, bottom=0, left=0, width=c, height=c),
    ]


def main(page: ft.Page) -> None:
    i18n.init_language()
    page.title = "PNG Streamer"
    page.theme_mode = ft.ThemeMode.DARK
    page.theme = ft.Theme(color_scheme_seed=ft.Colors.DEEP_PURPLE)
    page.window.width = 1210
    page.window.height = 750
    page.window.min_width = 1210
    page.window.min_height = 750
    page.window.resizable = True
    page.window.title_bar_hidden = True
    page.window.frameless = True
    page.window.shadow = False
    page.window.bgcolor = ft.Colors.TRANSPARENT
    page.bgcolor = ft.Colors.TRANSPARENT

    icon_path = _icon_path()
    if icon_path:
        page.window.icon = icon_path

    page.window.prevent_close = True

    def _hide_to_tray() -> None:
        page.window.visible = False
        page.window.skip_task_bar = True
        page.update()

    def _on_window_event(e: ft.WindowEvent) -> None:
        if e.type == ft.WindowEventType.CLOSE:
            _hide_to_tray()

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
        title_bar_text.value = "PNG Streamer"
        _refresh_window_button_tooltips()
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

    def _on_minimize_click(e: ft.ControlEvent) -> None:
        page.window.minimized = True
        page.update()

    def _on_maximize_click(e: ft.ControlEvent) -> None:
        page.window.maximized = not page.window.maximized
        maximize_button.icon = ft.Icons.FILTER_NONE if page.window.maximized else ft.Icons.CROP_SQUARE
        maximize_button.tooltip = i18n.t("window.restore") if page.window.maximized else i18n.t("window.maximize")
        page.update()

    def _on_close_click(e: ft.ControlEvent) -> None:
        _hide_to_tray()

    minimize_button = ft.IconButton(
        icon=ft.Icons.REMOVE,
        icon_size=16,
        tooltip=i18n.t("window.minimize"),
        on_click=_on_minimize_click,
    )
    maximize_button = ft.IconButton(
        icon=ft.Icons.CROP_SQUARE,
        icon_size=14,
        tooltip=i18n.t("window.maximize"),
        on_click=_on_maximize_click,
    )
    close_button = ft.IconButton(
        icon=ft.Icons.CLOSE,
        icon_size=16,
        tooltip=i18n.t("window.close"),
        on_click=_on_close_click,
        icon_color=ft.Colors.WHITE,
        hover_color=ft.Colors.RED_400,
    )

    def _refresh_window_button_tooltips() -> None:
        minimize_button.tooltip = i18n.t("window.minimize")
        maximize_button.tooltip = i18n.t("window.restore") if page.window.maximized else i18n.t("window.maximize")
        close_button.tooltip = i18n.t("window.close")

    title_bar_text = ft.Text("PNG Streamer", size=13, weight=ft.FontWeight.W_500)

    title_bar = ft.WindowDragArea(
        content=ft.Container(
            height=40,
            bgcolor=ft.Colors.with_opacity(0.4, "#160F22"),
            padding=ft.Padding(left=14, right=6, top=0, bottom=0),
            content=ft.Row(
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Image(src=icon_path, width=18, height=18) if icon_path else ft.Container(width=18),
                    ft.Container(width=8),
                    title_bar_text,
                    ft.Container(expand=True),
                    minimize_button,
                    maximize_button,
                    close_button,
                ],
            ),
        ),
    )

    content_column = ft.Column(
        spacing=0,
        expand=True,
        controls=[
            title_bar,
            ft.Row([nav_rail, ft.VerticalDivider(width=1), body], expand=True),
        ],
    )

    page.add(
        ft.Container(
            expand=True,
            bgcolor="#0B0710",
            border_radius=16,
            clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
            content=ft.Stack(
                [_background_geometry(), content_column, *_resize_handles(page)],
                expand=True,
            ),
        )
    )
    _show(0)

    tray.start(page, icon_path)
    _LOGGER.info("UI initialized")


def start_program() -> None:
    ft.run(main)
