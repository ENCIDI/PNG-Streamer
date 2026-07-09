from typing import Any, Dict, List, Optional

import flet as ft

from app.modules import (
    logging_manager as logm,
    logic_manager as lm,
    storage_manager as sm,
)
from app.modules.ui import i18n, style

_LOGGER = logm.get_logger(__name__)

_ROW_COUNT = 10
_THUMB_SIZE = 68


def _make_thumb_box() -> tuple[ft.Container, ft.Image]:
    thumbnail = ft.Image(src="", fit=ft.BoxFit.CONTAIN, visible=False)
    box = ft.Container(
        width=_THUMB_SIZE,
        height=_THUMB_SIZE,
        border_radius=8,
        bgcolor=ft.Colors.with_opacity(0.08, ft.Colors.WHITE),
        alignment=ft.Alignment(0, 0),
        content=thumbnail,
    )
    return box, thumbnail


class _ImageRow:
    def __init__(self, index: int, image_options: List[ft.DropdownOption]):
        self.index = index
        self.image_dropdown = ft.Dropdown(
            options=[ft.DropdownOption(key="", text="")] + image_options,
            width=105,
        )
        self.blink_dropdown = ft.Dropdown(
            options=[ft.DropdownOption(key="", text="")] + image_options,
            width=105,
        )
        self.threshold_field = ft.TextField(value="0", width=60)
        self.shake_slider = ft.Slider(min=0, max=100, value=0, width=120)
        self.image_thumb_box, self.image_thumbnail = _make_thumb_box()
        self.blink_thumb_box, self.blink_thumbnail = _make_thumb_box()

        def _on_image_select(e: ft.ControlEvent) -> None:
            self._update_thumb(self.image_dropdown, self.image_thumbnail)
            self.image_thumbnail.update()

        def _on_blink_select(e: ft.ControlEvent) -> None:
            self._update_thumb(self.blink_dropdown, self.blink_thumbnail)
            self.blink_thumbnail.update()

        self.image_dropdown.on_select = _on_image_select
        self.blink_dropdown.on_select = _on_blink_select

    @staticmethod
    def _update_thumb(dropdown: ft.Dropdown, thumbnail: ft.Image) -> None:
        path = lm.resolve_image_path(dropdown.value or "")
        if path:
            thumbnail.src = str(path)
            thumbnail.visible = True
        else:
            thumbnail.visible = False

    def load(self, image_data: Optional[Dict[str, Any]], blink_data: Optional[Dict[str, Any]]) -> None:
        if image_data:
            self.image_dropdown.value = image_data.get("path-to-image", "")
            self.threshold_field.value = str(image_data.get("volume-level", 0))
            self.shake_slider.value = max(0, int(image_data.get("shake-level", 0) or 0))
            self._update_thumb(self.image_dropdown, self.image_thumbnail)
        if blink_data:
            self.blink_dropdown.value = blink_data.get("path-to-image", "")
            self._update_thumb(self.blink_dropdown, self.blink_thumbnail)

    def to_image_entry(self) -> Optional[Dict[str, Any]]:
        path_value = (self.image_dropdown.value or "").strip()
        if not path_value:
            return None
        try:
            volume_level = int(self.threshold_field.value or 0)
        except (TypeError, ValueError):
            volume_level = 0
        return {
            "id": self.index,
            "path-to-image": path_value,
            "volume-level": volume_level,
            "shake-level": int(self.shake_slider.value),
        }

    def to_blink_entry(self) -> Optional[Dict[str, Any]]:
        path_value = (self.blink_dropdown.value or "").strip()
        if not path_value:
            return None
        return {"id": self.index, "path-to-image": path_value}

    def row_control(self) -> ft.Control:
        return ft.Row(
            [
                ft.Text(str(self.index + 1), width=20),
                self.image_dropdown,
                self.image_thumb_box,
                self.blink_dropdown,
                self.blink_thumb_box,
                self.threshold_field,
                self.shake_slider,
            ],
            spacing=8,
        )


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
            return int(settings.get("active-image-profile-id", 1))
        except (TypeError, ValueError):
            return None

    def _notify(message: str) -> None:
        page.show_dialog(ft.SnackBar(ft.Text(message)))

    def _select(profile_id: Optional[int]) -> None:
        state["selected_id"] = profile_id
        profile = sm.get_profile_by_id(profile_id) if profile_id is not None else None
        editor_host.content = _build_editor(profile)
        _refresh_list()
        page.update()

    def _refresh_list() -> None:
        profiles = sm.list_profiles()
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
            sm.update_settings({"active-image-profile-id": profile_id})
            _notify(i18n.t("common.notify_activated", name=profile.get("name")))
            _refresh_list()

        def _on_delete(e: ft.ControlEvent) -> None:
            sm.delete_profile(profile_id)
            if state["selected_id"] == profile_id:
                state["selected_id"] = None
                editor_host.content = ft.Text(i18n.t("common.empty_state"), italic=True)
            remaining = sm.list_profiles()
            if active_id == profile_id and remaining:
                sm.update_settings({"active-image-profile-id": remaining[0].get("id")})
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

    def _build_editor(profile: Optional[Dict[str, Any]]) -> ft.Control:
        is_new = profile is None
        image_names = lm.list_available_images()
        image_options = [ft.DropdownOption(key=name, text=name) for name in image_names]

        name_field = ft.TextField(
            label=i18n.t("common.profile_name"),
            value=profile.get("name", "") if profile else i18n.t("common.new_profile"),
        )
        blink_settings = profile.get("blink", {}) if profile else {}
        blink_min = ft.TextField(
            label=i18n.t("images.blink_min"), value=str(blink_settings.get("interval-min-ms", "2000")), width=110
        )
        blink_max = ft.TextField(
            label=i18n.t("images.blink_max"), value=str(blink_settings.get("interval-max-ms", "5000")), width=110
        )
        blink_dur = ft.TextField(
            label=i18n.t("images.blink_dur"), value=str(blink_settings.get("duration-ms", "100")), width=110
        )

        images_by_id = {img.get("id"): img for img in (profile.get("images", []) if profile else [])}
        blink_by_id = {img.get("id"): img for img in (profile.get("blink-images", []) if profile else [])}

        rows = [_ImageRow(i, image_options) for i in range(_ROW_COUNT)]
        for row in rows:
            row.load(images_by_id.get(row.index), blink_by_id.get(row.index))

        def _save(e: ft.ControlEvent) -> None:
            new_profile_data = {
                "name": (name_field.value or "").strip() or "profile",
                "images": [row.to_image_entry() for row in rows if row.to_image_entry()],
                "blink-images": [row.to_blink_entry() for row in rows if row.to_blink_entry()],
                "blink": {
                    "interval-min-ms": int(blink_min.value or 0),
                    "interval-max-ms": int(blink_max.value or 0),
                    "duration-ms": int(blink_dur.value or 0),
                },
            }
            if is_new:
                created = sm.create_profile(
                    name=new_profile_data["name"],
                    images=new_profile_data["images"],
                    blink=new_profile_data["blink"],
                    blink_images=new_profile_data["blink-images"],
                )
                sm.update_settings({"active-image-profile-id": created.get("id")})
                state["selected_id"] = created.get("id")
                _notify(i18n.t("common.notify_created", name=new_profile_data["name"]))
            else:
                new_profile_data["id"] = profile["id"]
                sm.update_profile(new_profile_data)
                _notify(i18n.t("common.notify_saved", name=new_profile_data["name"]))

            _refresh_list()
            _select(state["selected_id"])

        header_row = ft.Row(
            [
                ft.Text(i18n.t("images.col_index"), width=20),
                ft.Text(i18n.t("images.col_image"), width=105),
                ft.Text("", width=_THUMB_SIZE),
                ft.Text(i18n.t("images.col_blink"), width=105),
                ft.Text("", width=_THUMB_SIZE),
                ft.Text(i18n.t("images.col_threshold"), width=60),
                ft.Text(i18n.t("images.col_shake"), width=120),
            ],
            spacing=8,
        )

        return ft.Column(
            spacing=12,
            expand=True,
            controls=[
                ft.Text(
                    i18n.t("common.new_profile") if is_new else i18n.t("common.editing", name=profile.get("name")),
                    size=18,
                    weight=ft.FontWeight.BOLD,
                ),
                name_field,
                ft.Row([blink_min, blink_max, blink_dur]),
                ft.Divider(),
                header_row,
                ft.Column(
                    [row.row_control() for row in rows],
                    expand=True,
                    scroll=ft.ScrollMode.ALWAYS,
                    spacing=6,
                ),
                ft.Row([ft.Button(i18n.t("common.save"), icon=ft.Icons.SAVE, on_click=_save)]),
            ],
        )

    def _on_create(e: ft.ControlEvent) -> None:
        _select(None)
        editor_host.content = _build_editor(None)
        page.update()

    _refresh_list()
    initial_id = _active_profile_id()
    if initial_id is not None and sm.get_profile_by_id(initial_id):
        state["selected_id"] = initial_id
        editor_host.content = _build_editor(sm.get_profile_by_id(initial_id))
        _refresh_list()

    return style.panel(
        ft.Row(
            expand=True,
            vertical_alignment=ft.CrossAxisAlignment.STRETCH,
            controls=[
                ft.Column(
                    width=260,
                    controls=[
                        ft.Text(i18n.t("images.title"), size=18, weight=ft.FontWeight.BOLD),
                        ft.Button(i18n.t("common.create_profile"), icon=ft.Icons.ADD, on_click=_on_create),
                        profile_list,
                    ],
                ),
                ft.VerticalDivider(width=1),
                editor_host,
            ],
        )
    )
