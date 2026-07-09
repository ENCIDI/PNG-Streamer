from typing import Any, Dict, Optional

import flet as ft

from app.modules import (
    audio_manager as am,
    logging_manager as logm,
    logic_manager as lm,
    storage_manager as sm,
)
from app.modules.ui import i18n, style, volume_meter

_LOGGER = logm.get_logger(__name__)


def _algorithm_options() -> list[ft.DropdownOption]:
    return [
        ft.DropdownOption(key="adaptive", text=i18n.t("sound.algo_adaptive")),
        ft.DropdownOption(key="fixed", text=i18n.t("sound.algo_fixed")),
    ]


def build(page: ft.Page) -> ft.Control:
    state: Dict[str, Any] = {"selected_id": None}

    profile_list = ft.ListView(spacing=8, expand=True)
    editor_host = ft.Container(
        expand=True,
        content=ft.Text(i18n.t("common.empty_state"), italic=True),
    )

    def _active_profile_id() -> Optional[int]:
        settings = sm.load_settings().get("settings", {})
        try:
            return int(settings.get("active-sound-profile-id", 1))
        except (TypeError, ValueError):
            return None

    def _notify(message: str) -> None:
        page.show_dialog(ft.SnackBar(ft.Text(message)))

    def _select(profile_id: Optional[int]) -> None:
        state["selected_id"] = profile_id
        profile = sm.get_sound_profile_by_id(profile_id) if profile_id is not None else None
        editor_host.content = _build_editor(profile)
        _refresh_list()
        page.update()

    def _refresh_list() -> None:
        profiles = sm.list_sound_profiles()
        active_id = _active_profile_id()
        profile_list.controls.clear()
        for p in profiles:
            profile_list.controls.append(_profile_tile(p, active_id))
        page.update()

    def _profile_tile(profile: Dict[str, Any], active_id: Optional[int]) -> ft.Control:
        profile_id = profile.get("id")
        is_selected = state["selected_id"] == profile_id
        is_active = active_id == profile_id

        def _on_select(e: ft.ControlEvent) -> None:
            _select(profile_id)

        def _on_activate(e: ft.ControlEvent) -> None:
            lm.activate_sound_profile(profile_id)
            _notify(i18n.t("common.notify_activated", name=profile.get("name")))
            _refresh_list()

        def _on_delete(e: ft.ControlEvent) -> None:
            sm.delete_sound_profile(profile_id)
            if state["selected_id"] == profile_id:
                state["selected_id"] = None
                editor_host.content = ft.Text(i18n.t("common.empty_state"), italic=True)
            remaining = sm.list_sound_profiles()
            if active_id == profile_id and remaining:
                lm.activate_sound_profile(remaining[0].get("id"))
            _notify(i18n.t("common.notify_deleted", name=profile.get("name")))
            _refresh_list()

        return ft.Container(
            padding=10,
            border_radius=10,
            bgcolor=ft.Colors.with_opacity(0.35 if is_selected else 0.12, ft.Colors.DEEP_PURPLE),
            on_click=_on_select,
            content=ft.Row(
                [
                    ft.Column(
                        [
                            ft.Text(profile.get("name", "profile"), weight=ft.FontWeight.BOLD),
                            ft.Text(
                                i18n.t("common.active_badge") if is_active else "",
                                size=11,
                                color=ft.Colors.GREEN_300,
                            ),
                        ],
                        expand=True,
                        spacing=2,
                    ),
                    ft.IconButton(
                        icon=ft.Icons.CHECK_CIRCLE_OUTLINE,
                        tooltip=i18n.t("common.activate_tooltip"),
                        on_click=_on_activate,
                    ),
                    ft.IconButton(
                        icon=ft.Icons.DELETE_OUTLINE,
                        tooltip=i18n.t("common.delete_tooltip"),
                        on_click=_on_delete,
                    ),
                ]
            ),
        )

    def _populate_mics(host_api_dropdown: ft.Dropdown, mic_dropdown: ft.Dropdown, wanted_mic_id, wanted_mic_name) -> None:
        selected_api = int(host_api_dropdown.value) if host_api_dropdown.value else None
        devices = am.list_audio_devices(host_api_index=selected_api)
        mic_dropdown.options = [
            ft.DropdownOption(
                key=str(d.device_id) if d.device_id is not None else "None",
                text=d.name,
            )
            for d in devices
        ]
        option_keys = [o.key for o in mic_dropdown.options]
        target_key = str(wanted_mic_id) if wanted_mic_id is not None else "None"
        if target_key in option_keys:
            mic_dropdown.value = target_key
        else:
            matched = next((o.key for o in mic_dropdown.options if o.text == wanted_mic_name), None)
            mic_dropdown.value = matched if matched is not None else "None"

    def _build_editor(profile: Optional[Dict[str, Any]]) -> ft.Control:
        is_new = profile is None
        name_field = ft.TextField(
            label=i18n.t("common.profile_name"),
            value=profile.get("name", "") if profile else i18n.t("common.new_profile"),
        )
        host_api_dropdown = ft.Dropdown(label=i18n.t("sound.protocol"), expand=True)
        mic_dropdown = ft.Dropdown(label=i18n.t("sound.microphone"), expand=True)
        noise_checkbox = ft.Checkbox(
            label=i18n.t("sound.noise_suppression"),
            value=bool(profile.get("unnoised", False)) if profile else False,
        )
        algorithm_dropdown = ft.Dropdown(
            label=i18n.t("sound.noise_algorithm"),
            options=_algorithm_options(),
            value=profile.get("noise-algorithm", "adaptive") if profile else "adaptive",
            expand=True,
            disabled=not (profile.get("unnoised", False) if profile else False),
        )
        threshold_value = float(profile.get("noise-threshold", 15.0)) if profile else 15.0
        threshold_visible = algorithm_dropdown.value == "fixed" and not algorithm_dropdown.disabled
        threshold_label = ft.Text(
            i18n.t("sound.threshold", value=int(threshold_value)), visible=threshold_visible
        )
        threshold_slider = ft.Slider(
            min=0,
            max=100,
            value=threshold_value,
            expand=True,
            visible=threshold_visible,
            on_change=lambda e: (
                setattr(
                    threshold_label,
                    "value",
                    i18n.t("sound.threshold", value=int(threshold_slider.value)),
                ),
                threshold_label.update(),
            ),
        )

        compressor_checkbox = ft.Checkbox(
            label=i18n.t("sound.enabled"),
            value=bool(profile.get("compressor-enabled", False)) if profile else False,
        )
        compressor_threshold_value = float(profile.get("compressor-threshold", 60.0)) if profile else 60.0
        compressor_ratio_value = float(profile.get("compressor-ratio", 4.0)) if profile else 4.0
        compressor_threshold_label = ft.Text(
            i18n.t("sound.compressor_threshold", value=int(compressor_threshold_value)), size=12
        )
        compressor_threshold_slider = ft.Slider(
            min=0,
            max=100,
            value=compressor_threshold_value,
            disabled=not compressor_checkbox.value,
            on_change=lambda e: (
                setattr(
                    compressor_threshold_label,
                    "value",
                    i18n.t("sound.compressor_threshold", value=int(compressor_threshold_slider.value)),
                ),
                compressor_threshold_label.update(),
            ),
        )
        compressor_ratio_label = ft.Text(
            i18n.t("sound.compressor_ratio", value=f"{compressor_ratio_value:.0f}"), size=12
        )
        compressor_ratio_slider = ft.Slider(
            min=1,
            max=20,
            value=compressor_ratio_value,
            disabled=not compressor_checkbox.value,
            on_change=lambda e: (
                setattr(
                    compressor_ratio_label,
                    "value",
                    i18n.t("sound.compressor_ratio", value=f"{compressor_ratio_slider.value:.0f}"),
                ),
                compressor_ratio_label.update(),
            ),
        )

        def _on_compressor_toggle(e: ft.ControlEvent) -> None:
            compressor_threshold_slider.disabled = not compressor_checkbox.value
            compressor_ratio_slider.disabled = not compressor_checkbox.value
            editor_host.update()

        compressor_checkbox.on_change = _on_compressor_toggle

        apis = am.list_host_apis()
        host_api_dropdown.options = [ft.DropdownOption(key=str(a.index), text=a.name) for a in apis]

        current_host_api = profile.get("host-api") if profile else None
        if current_host_api is not None:
            host_api_dropdown.value = str(current_host_api)
        else:
            for a in apis:
                if "WASAPI" in a.name:
                    host_api_dropdown.value = str(a.index)
                    break

        wanted_mic_id = profile.get("microphone") if profile else None
        wanted_mic_name = profile.get("microphone-name", "Default") if profile else "Default"
        _populate_mics(host_api_dropdown, mic_dropdown, wanted_mic_id, wanted_mic_name)

        def _on_host_api_select(e: ft.ControlEvent) -> None:
            _populate_mics(host_api_dropdown, mic_dropdown, None, mic_dropdown.value)
            editor_host.update()

        host_api_dropdown.on_select = _on_host_api_select

        def _sync_threshold_visibility() -> None:
            visible = noise_checkbox.value and algorithm_dropdown.value == "fixed"
            threshold_slider.visible = visible
            threshold_label.visible = visible

        def _on_noise_toggle(e: ft.ControlEvent) -> None:
            algorithm_dropdown.disabled = not noise_checkbox.value
            _sync_threshold_visibility()
            editor_host.update()

        noise_checkbox.on_change = _on_noise_toggle

        def _on_algorithm_select(e: ft.ControlEvent) -> None:
            _sync_threshold_visibility()
            editor_host.update()

        algorithm_dropdown.on_select = _on_algorithm_select

        def _save(e: ft.ControlEvent) -> None:
            name = (name_field.value or "").strip() or "profile"
            host_api_value = int(host_api_dropdown.value) if host_api_dropdown.value else None
            mic_value = None if mic_dropdown.value in (None, "None") else int(mic_dropdown.value)
            mic_name = next(
                (o.text for o in mic_dropdown.options if o.key == mic_dropdown.value),
                "Default",
            )

            if is_new:
                created = sm.create_sound_profile(
                    name=name,
                    host_api=host_api_value,
                    microphone=mic_value,
                    microphone_name=mic_name,
                    unnoised=noise_checkbox.value,
                    noise_algorithm=algorithm_dropdown.value or "adaptive",
                    noise_threshold=threshold_slider.value,
                    compressor_enabled=compressor_checkbox.value,
                    compressor_threshold=compressor_threshold_slider.value,
                    compressor_ratio=compressor_ratio_slider.value,
                )
                sm.update_settings({"active-sound-profile-id": created.get("id")})
                lm.apply_sound_profile(created)
                state["selected_id"] = created.get("id")
                _notify(i18n.t("common.notify_created", name=name))
            else:
                updated = dict(profile)
                updated.update(
                    {
                        "name": name,
                        "host-api": host_api_value,
                        "microphone": mic_value,
                        "microphone-name": mic_name,
                        "unnoised": noise_checkbox.value,
                        "noise-algorithm": algorithm_dropdown.value or "adaptive",
                        "noise-threshold": threshold_slider.value,
                        "compressor-enabled": compressor_checkbox.value,
                        "compressor-threshold": compressor_threshold_slider.value,
                        "compressor-ratio": compressor_ratio_slider.value,
                    }
                )
                sm.update_sound_profile(updated)
                if _active_profile_id() == updated.get("id"):
                    lm.apply_sound_profile(updated)
                _notify(i18n.t("common.notify_saved", name=name))

            _refresh_list()
            _select(state["selected_id"])

        compressor_panel = ft.Container(
            padding=16,
            border_radius=14,
            bgcolor=ft.Colors.with_opacity(0.18, ft.Colors.DEEP_PURPLE_ACCENT),
            content=ft.Column(
                spacing=8,
                controls=[
                    ft.Row(
                        [
                            ft.Icon(ft.Icons.GRAPHIC_EQ, color=ft.Colors.DEEP_PURPLE_200),
                            ft.Text(i18n.t("sound.compressor"), weight=ft.FontWeight.BOLD),
                            ft.Container(expand=True),
                            compressor_checkbox,
                        ]
                    ),
                    compressor_threshold_label,
                    compressor_threshold_slider,
                    compressor_ratio_label,
                    compressor_ratio_slider,
                ],
            ),
        )

        return ft.Column(
            spacing=16,
            expand=True,
            scroll=ft.ScrollMode.AUTO,
            controls=[
                ft.Text(
                    i18n.t("common.new_profile") if is_new else i18n.t("common.editing", name=profile.get("name")),
                    size=18,
                    weight=ft.FontWeight.BOLD,
                ),
                name_field,
                ft.Row([host_api_dropdown, mic_dropdown]),
                ft.Column(
                    spacing=6,
                    controls=[
                        ft.Text(i18n.t("sound.mic_level"), size=12),
                        volume_meter.build(page, text_size=20, bar_width=None),
                    ],
                ),
                noise_checkbox,
                algorithm_dropdown,
                threshold_slider,
                threshold_label,
                ft.Divider(),
                compressor_panel,
                ft.Row([ft.Button(i18n.t("common.save"), icon=ft.Icons.SAVE, on_click=_save)]),
            ],
        )

    def _on_create(e: ft.ControlEvent) -> None:
        _select(None)
        editor_host.content = _build_editor(None)
        page.update()

    _refresh_list()
    initial_id = _active_profile_id()
    if initial_id is not None and sm.get_sound_profile_by_id(initial_id):
        state["selected_id"] = initial_id
        editor_host.content = _build_editor(sm.get_sound_profile_by_id(initial_id))
        _refresh_list()

    return style.panel(
        ft.Row(
            expand=True,
            vertical_alignment=ft.CrossAxisAlignment.STRETCH,
            controls=[
                ft.Column(
                    width=260,
                    controls=[
                        ft.Text(i18n.t("sound.title"), size=18, weight=ft.FontWeight.BOLD),
                        ft.Button(i18n.t("common.create_profile"), icon=ft.Icons.ADD, on_click=_on_create),
                        profile_list,
                    ],
                ),
                ft.VerticalDivider(width=1),
                editor_host,
            ],
        )
    )
