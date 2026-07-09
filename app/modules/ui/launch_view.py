from typing import Optional

import flet as ft

from app.modules import (
    logging_manager as logm,
    logic_manager as lm,
    storage_manager as sm,
    web_manager as wm,
)
from app.modules.ui import i18n, style, volume_meter

_LOGGER = logm.get_logger(__name__)


def _parse_port(value: str) -> int:
    try:
        port = int(value)
    except (TypeError, ValueError):
        return 8642
    if port < 1 or port > 65535:
        return 8642
    return port


def build(page: ft.Page) -> ft.Control:
    settings = sm.load_settings().get("settings", {})

    sound_profiles = sm.list_sound_profiles()
    image_profiles = sm.list_profiles()

    sound_dropdown = ft.Dropdown(
        label=i18n.t("launch.sound_profile"),
        options=[
            ft.DropdownOption(key=str(p.get("id")), text=p.get("name", "profile"))
            for p in sound_profiles
        ],
        value=str(settings.get("active-sound-profile-id", 1)),
        expand=True,
    )

    image_dropdown = ft.Dropdown(
        label=i18n.t("launch.image_profile"),
        options=[
            ft.DropdownOption(key=str(p.get("id")), text=p.get("name", "profile"))
            for p in image_profiles
        ],
        value=str(settings.get("active-image-profile-id", 1)),
        expand=True,
    )

    port_field = ft.TextField(
        label=i18n.t("launch.server_port"),
        value=str(settings.get("server-port", 8642)),
        width=150,
    )
    status_text = ft.Text(
        i18n.t("launch.status_stopped"),
        color=ft.Colors.RED_400,
        weight=ft.FontWeight.BOLD,
    )
    widget_url_field = ft.TextField(
        label=i18n.t("launch.widget_url"),
        value="",
        read_only=True,
        expand=True,
    )
    console_checkbox = ft.Checkbox(
        label=i18n.t("launch.show_console"),
        value=bool(settings.get("show-console", False)),
    )

    def _refresh_server_status() -> None:
        if wm.is_running():
            status_text.value = i18n.t("launch.status_running")
            status_text.color = ft.Colors.GREEN_400
            widget_url_field.value = f"http://127.0.0.1:{_parse_port(port_field.value)}/widget"
        else:
            status_text.value = i18n.t("launch.status_stopped")
            status_text.color = ft.Colors.RED_400
            widget_url_field.value = ""
        page.update()

    def _on_sound_profile_select(e: ft.ControlEvent) -> None:
        if not sound_dropdown.value:
            return
        lm.activate_sound_profile(int(sound_dropdown.value))

    def _on_image_profile_select(e: ft.ControlEvent) -> None:
        if not image_dropdown.value:
            return
        sm.update_settings({"active-image-profile-id": int(image_dropdown.value)})

    def _on_start_server(e: ft.ControlEvent) -> None:
        port = _parse_port(port_field.value)
        sm.update_settings({"server-port": port})
        started, status = wm.start_server("127.0.0.1", port)
        if not started and status != "already_running":
            page.show_dialog(ft.SnackBar(ft.Text(i18n.t("launch.server_start_failed"))))
        _refresh_server_status()

    def _on_stop_server(e: ft.ControlEvent) -> None:
        wm.stop_server()
        _refresh_server_status()

    def _on_console_changed(e: ft.ControlEvent) -> None:
        sm.update_settings({"show-console": console_checkbox.value})

    sound_dropdown.on_select = _on_sound_profile_select
    image_dropdown.on_select = _on_image_profile_select
    console_checkbox.on_change = _on_console_changed

    volume_row = volume_meter.build(page)

    _refresh_server_status()

    return style.panel(
        ft.Column(
            spacing=24,
            controls=[
                ft.Text(i18n.t("nav.launch"), size=22, weight=ft.FontWeight.BOLD),
                ft.Row([sound_dropdown, image_dropdown]),
                ft.Column(
                    spacing=6,
                    controls=[
                        ft.Text(i18n.t("launch.current_volume")),
                        volume_row,
                    ],
                ),
                ft.Divider(),
                ft.Text(i18n.t("launch.server_section"), size=16, weight=ft.FontWeight.BOLD),
                ft.Row([port_field, ft.Text(i18n.t("launch.status_label")), status_text]),
                ft.Row(
                    [
                        ft.Button(i18n.t("launch.start"), icon=ft.Icons.PLAY_ARROW, on_click=_on_start_server),
                        ft.Button(i18n.t("launch.stop"), icon=ft.Icons.STOP, on_click=_on_stop_server),
                    ]
                ),
                widget_url_field,
                console_checkbox,
            ],
        ),
    )
