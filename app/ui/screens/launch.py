from typing import Any, Dict, Optional

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont, QGuiApplication
from PySide6.QtWidgets import QGridLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QVBoxLayout

from app.modules import audio_manager as am, logic_manager as lm
from app.ui import i18n, icons, pixmaps, theme
from app.ui.screens.base import Screen
from app.ui.state import AppState
from app.ui.widgets.common import Card, Combo, StatusPill, chip, clear_layout, muted, number_field
from app.ui.widgets.meter import LevelMeter
from app.ui.widgets.stage import AvatarStage


def sound_chips(profile: Optional[Dict[str, Any]]) -> list:
    if not profile:
        return []
    if not profile.get("unnoised"):
        noise = i18n.t("chip.noise_off")
    elif profile.get("noise-algorithm") == "fixed":
        noise = i18n.t("chip.noise_fixed", value=int(float(profile.get("noise-threshold", 0))))
    else:
        noise = i18n.t("chip.noise_adaptive")
    chips = [noise]
    if profile.get("compressor-enabled"):
        chips.append(i18n.t("chip.compressor", ratio=f"{float(profile.get('compressor-ratio', 4)):.0f}"))
    return chips


def image_chips(profile: Optional[Dict[str, Any]]) -> list:
    if not profile:
        return []
    chips = [i18n.t("chip.frames", count=len(lm.sorted_frames(profile)))]
    min_ms, max_ms, duration_ms = lm.blink_settings(profile)
    if min_ms and max_ms and duration_ms and profile.get("blink-images"):
        chips.append(i18n.t("chip.blink", min=f"{min_ms / 1000:g}", max=f"{max_ms / 1000:g}"))
    else:
        chips.append(i18n.t("chip.no_blink"))
    return chips


def frame_thumbnails(profile: Optional[Dict[str, Any]]) -> list:
    if not profile:
        return []
    return [
        (int(frame.get("volume-level", 0)), pixmaps.load(lm.resolve_image_path(frame.get("path-to-image", "")), 96))
        for frame in lm.sorted_frames(profile)
    ]


def frame_caption(profile: Optional[Dict[str, Any]], volume: float) -> str:
    if not profile:
        return ""
    frame = lm.pick_frame(profile, volume)
    if frame is None:
        return ""
    frames = lm.sorted_frames(profile)
    index = next((i for i, f in enumerate(frames) if f is frame or f == frame), 0)
    return i18n.t("preview.frame", index=index + 1, level=frame.get("volume-level", 0))


def mic_error_text(error: Optional[str]) -> str:
    return {
        "failed": i18n.t("mic.error_failed"),
        "fallback": i18n.t("mic.error_fallback"),
        "unavailable": i18n.t("mic.error_unavailable"),
    }.get(error or "", "")


class LaunchScreen(Screen):
    def __init__(self, state: AppState):
        super().__init__(state)
        self.pill = StatusPill()
        self.server_button = QPushButton()
        self.server_button.setCursor(Qt.PointingHandCursor)
        self.server_button.clicked.connect(self._toggle_server)
        self.header.actions.addWidget(self.pill, 0, Qt.AlignVCenter)
        self.header.actions.addWidget(self.server_button, 0, Qt.AlignVCenter)

        grid = QGridLayout()
        grid.setHorizontalSpacing(16)
        grid.setVerticalSpacing(16)

        self.preview_card = Card()
        self.stage = AvatarStage()
        self.preview_card.body.addWidget(self.stage, 1)

        self.mic_card = Card()
        value_row = QHBoxLayout()
        value_row.setSpacing(6)
        self.value = QLabel("0")
        self.value.setFont(theme.font(30, QFont.DemiBold))
        self.value.setMinimumWidth(64)
        self.unit = muted()
        self.unit.setContentsMargins(0, 0, 0, 9)
        value_row.addWidget(self.value)
        value_row.addWidget(self.unit, 0, Qt.AlignBottom)
        value_row.addStretch()
        self.sound_chips = QHBoxLayout()
        self.sound_chips.setSpacing(6)
        value_row.addLayout(self.sound_chips)
        self.mic_card.body.addLayout(value_row)
        self.meter = LevelMeter()
        self.mic_card.body.addWidget(self.meter)
        self.mic_error = muted("", "danger", wrap=True)
        self.mic_card.body.addWidget(self.mic_error)

        self.profiles_card = Card()
        row = QHBoxLayout()
        row.setSpacing(12)
        self.sound_label = muted()
        self.sound_combo = Combo()
        self.image_label = muted()
        self.image_combo = Combo()
        for label, combo in ((self.sound_label, self.sound_combo), (self.image_label, self.image_combo)):
            column = QVBoxLayout()
            column.setSpacing(6)
            column.addWidget(label)
            column.addWidget(combo)
            row.addLayout(column, 1)
        self.profiles_card.body.addLayout(row)
        self.image_chips = QHBoxLayout()
        self.image_chips.setSpacing(6)
        self.profiles_card.body.addLayout(self.image_chips)
        self.profiles_card.body.addStretch()
        self.sound_combo.currentIndexChanged.connect(self._on_sound_profile)
        self.image_combo.currentIndexChanged.connect(self._on_image_profile)

        self.obs_card = Card()
        obs_row = QHBoxLayout()
        obs_row.setSpacing(10)
        self.url = QLineEdit()
        self.url.setObjectName("url")
        self.url.setReadOnly(True)
        self.url.setFont(theme.mono_font())
        self.copy_button = QPushButton()
        self.copy_button.setObjectName("primary")
        self.copy_button.setIcon(icons.icon("copy", theme.ACCENT_INK))
        self.copy_button.setCursor(Qt.PointingHandCursor)
        self.copy_button.clicked.connect(self._copy_url)
        self.port_label = muted()
        self.port = number_field(1, 65535)
        self.port.setFixedWidth(90)
        self.port.editingFinished.connect(lambda: state.update_settings(server_port=self.port.value()))
        obs_row.addWidget(self.url, 1)
        obs_row.addWidget(self.copy_button)
        obs_row.addSpacing(8)
        obs_row.addWidget(self.port_label)
        obs_row.addWidget(self.port)
        self.obs_card.body.addLayout(obs_row)
        self.obs_hint = muted("", "faint", wrap=True)
        self.obs_card.body.addWidget(self.obs_hint)

        grid.addWidget(self.preview_card, 0, 0, 2, 1)
        grid.addWidget(self.mic_card, 0, 1)
        grid.addWidget(self.profiles_card, 1, 1)
        grid.addWidget(self.obs_card, 2, 0, 1, 2)
        grid.setColumnStretch(0, 5)
        grid.setColumnStretch(1, 6)
        grid.setRowStretch(1, 1)
        self.root.addLayout(grid, 1)

        self._copied = False
        self._image_profile: Optional[Dict[str, Any]] = None

        state.volume_changed.connect(self._on_volume)
        state.server_changed.connect(self._refresh_server)
        state.profiles_changed.connect(self._refresh_profiles)
        state.images_changed.connect(self._refresh_profiles)
        state.microphone_changed.connect(self._refresh_mic)
        self.retranslate()

    def retranslate(self) -> None:
        self.header.set_text(i18n.t("launch.title"), i18n.t("launch.subtitle"))
        self.preview_card.set_title(i18n.t("launch.preview"), i18n.t("launch.preview_hint"))
        self.profiles_card.set_title(i18n.t("launch.profiles"))
        self.obs_card.set_title(i18n.t("launch.obs_source"))
        self.unit.setText(i18n.t("launch.volume"))
        self.sound_label.setText(i18n.t("launch.sound_profile"))
        self.image_label.setText(i18n.t("launch.image_profile"))
        self.port_label.setText(i18n.t("launch.port"))
        self.obs_hint.setText(i18n.t("launch.obs_hint"))
        self.copy_button.setText(" " + i18n.t("launch.copied" if self._copied else "launch.copy"))
        self._refresh_server()
        self._refresh_profiles()
        self._refresh_mic()

    def _refresh_server(self) -> None:
        running = self.state.server_running()
        self.pill.set_state(running, i18n.t("status.live" if running else "status.stopped"))
        self.server_button.setText(" " + i18n.t("launch.stop" if running else "launch.start"))
        self.server_button.setObjectName("" if running else "primary")
        self.server_button.setIcon(icons.icon("stop" if running else "play", theme.TEXT if running else theme.ACCENT_INK))
        self.server_button.style().polish(self.server_button)
        self.port.setValue(self.state.port())
        self.port.setEnabled(not running)
        self.url.setText(self.state.widget_url() if running else "")
        self.url.setPlaceholderText(i18n.t("launch.url_stopped"))
        self.copy_button.setEnabled(running)

    def _refresh_profiles(self) -> None:
        self.sound_combo.set_items(
            [(p.get("name", "profile"), p.get("id")) for p in self.state.sound_profiles()],
            self.state.active_sound_profile_id(),
        )
        self.image_combo.set_items(
            [(p.get("name", "profile"), p.get("id")) for p in self.state.image_profiles()],
            self.state.active_image_profile_id(),
        )
        sound = self.state.active_sound_profile()
        self._image_profile = self.state.active_image_profile()
        clear_layout(self.sound_chips)
        for text in sound_chips(sound):
            self.sound_chips.addWidget(chip(text))
        clear_layout(self.image_chips)
        for text in image_chips(self._image_profile):
            self.image_chips.addWidget(chip(text))
        self.image_chips.addStretch()
        self.meter.set_frames(frame_thumbnails(self._image_profile))
        self._refresh_mic()

    def _refresh_mic(self) -> None:
        sound = self.state.active_sound_profile() or {}
        apis = {api.index: api.name for api in am.list_host_apis()}
        mic_name = sound.get("microphone-name") or "Default"
        if mic_name == "Default":
            mic_name = i18n.t("mic.default")
        api_name = apis.get(sound.get("host-api"))
        self.mic_card.set_title(i18n.t("launch.microphone"), " · ".join(filter(None, [mic_name, api_name])))
        text = mic_error_text(self.state.mic_error)
        self.mic_error.setText(text)
        self.mic_error.setVisible(bool(text))

    def _on_volume(self, volume: float) -> None:
        if not self.isVisible():
            return
        self.value.setText(str(int(volume)))
        self.meter.set_level(volume)
        path, shake = lm.get_current_image_state(volume)
        self.stage.set_frame(
            path, shake, frame_caption(self._image_profile, volume), i18n.t("preview.empty")
        )

    def tick(self, dt: float) -> None:
        self.pill.tick(dt)
        self.stage.tick(dt)

    def _toggle_server(self) -> None:
        if self.state.server_running():
            self.state.stop_server()
        else:
            self.state.start_server(self.port.value())

    def _copy_url(self) -> None:
        QGuiApplication.clipboard().setText(self.state.widget_url())
        self._copied = True
        self.copy_button.setText(" " + i18n.t("launch.copied"))
        QTimer.singleShot(1200, self._reset_copy)

    def _reset_copy(self) -> None:
        self._copied = False
        self.copy_button.setText(" " + i18n.t("launch.copy"))

    def _on_sound_profile(self, index: int) -> None:
        profile_id = self.sound_combo.itemData(index)
        if profile_id is not None and profile_id != self.state.active_sound_profile_id():
            self.state.set_active_sound_profile(profile_id)

    def _on_image_profile(self, index: int) -> None:
        profile_id = self.image_combo.itemData(index)
        if profile_id is not None and profile_id != self.state.active_image_profile_id():
            self.state.set_active_image_profile(profile_id)
