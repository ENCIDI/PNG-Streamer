import copy
import sys
from typing import Any, Dict, List, Optional

from PySide6.QtGui import QFont
from PySide6.QtWidgets import QGridLayout, QHBoxLayout, QLabel, QVBoxLayout

from app.modules import audio_manager as am, storage_manager as sm
from app.ui import i18n, theme
from app.ui.screens.base import ProfileScreen
from app.ui.screens.launch import mic_error_text
from app.ui.state import AppState
from app.ui.widgets.common import Card, Combo, LabeledSlider, SwitchRow, muted
from app.ui.widgets.meter import LevelMeter

_DEFAULT_DEVICE = -1
_IS_LINUX = sys.platform.startswith("linux")
_PREFERRED_API = "ALSA" if _IS_LINUX else "WASAPI"


def host_api_label(name: str) -> str:
    if _IS_LINUX and name == "ALSA":
        return "ALSA · PipeWire / PulseAudio"
    return name


class SoundScreen(ProfileScreen):
    def __init__(self, state: AppState):
        super().__init__(state)
        self._applied_device: Any = object()
        self._devices: List[am.AudioDevice] = []

        # input
        self.input_card = Card()
        grid = QGridLayout()
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(6)
        self.api_label = muted()
        self.device_label = muted()
        self.api_combo = Combo()
        self.device_combo = Combo()
        grid.addWidget(self.api_label, 0, 0)
        grid.addWidget(self.device_label, 0, 1)
        grid.addWidget(self.api_combo, 1, 0)
        grid.addWidget(self.device_combo, 1, 1)
        grid.setColumnStretch(0, 2)
        grid.setColumnStretch(1, 3)
        self.input_card.body.addLayout(grid)
        self.linux_hint = muted("", "faint", wrap=True)
        self.linux_hint.setVisible(_IS_LINUX)
        self.input_card.body.addWidget(self.linux_hint)
        level_row = QHBoxLayout()
        self.level_label = muted()
        self.level_value = QLabel("0")
        self.level_value.setFont(theme.font(theme.BASE_POINT_SIZE, QFont.DemiBold))
        level_row.addWidget(self.level_label)
        level_row.addStretch()
        level_row.addWidget(self.level_value)
        self.input_card.body.addLayout(level_row)
        self.meter = LevelMeter(segments=48, show_scale=False)
        self.input_card.body.addWidget(self.meter)
        self.mic_error = muted("", "danger", wrap=True)
        self.input_card.body.addWidget(self.mic_error)
        self.editor_layout.addWidget(self.input_card)

        # noise
        self.noise_card = Card()
        self.noise_switch = SwitchRow()
        self.noise_switch.label.setFont(theme.font(10.5, QFont.DemiBold))
        self.noise_card.body.addWidget(self.noise_switch)
        self.algorithm_label = muted()
        self.algorithm_combo = Combo()
        algorithm = QVBoxLayout()
        algorithm.setSpacing(6)
        algorithm.addWidget(self.algorithm_label)
        algorithm.addWidget(self.algorithm_combo)
        self.noise_card.body.addLayout(algorithm)
        self.threshold = LabeledSlider(0, 100)
        self.noise_card.body.addWidget(self.threshold)
        self.editor_layout.addWidget(self.noise_card)

        # compressor
        self.compressor_card = Card()
        self.compressor_switch = SwitchRow()
        self.compressor_switch.label.setFont(theme.font(10.5, QFont.DemiBold))
        self.compressor_card.body.addWidget(self.compressor_switch)
        sliders = QHBoxLayout()
        sliders.setSpacing(24)
        self.comp_threshold = LabeledSlider(0, 100)
        self.comp_ratio = LabeledSlider(1, 20, lambda v: f"{v}:1")
        sliders.addWidget(self.comp_threshold, 1)
        sliders.addWidget(self.comp_ratio, 1)
        self.compressor_card.body.addLayout(sliders)
        self.editor_layout.addWidget(self.compressor_card)
        self.editor_layout.addStretch()

        self.api_combo.currentIndexChanged.connect(self._on_api_changed)
        self.device_combo.currentIndexChanged.connect(self._changed)
        self.noise_switch.toggled.connect(self._changed)
        self.algorithm_combo.currentIndexChanged.connect(self._changed)
        self.threshold.valueChanged.connect(self._changed)
        self.compressor_switch.toggled.connect(self._changed)
        self.comp_threshold.valueChanged.connect(self._changed)
        self.comp_ratio.valueChanged.connect(self._changed)
        state.volume_changed.connect(self._on_volume)
        state.microphone_changed.connect(self._refresh_mic_error)

        self.retranslate()
        self.reload()

    # --- ProfileScreen hooks -------------------------------------------------
    def list_profiles(self) -> List[Dict[str, Any]]:
        return sm.list_sound_profiles()

    def store_profile(self, profile: Dict[str, Any]) -> None:
        sm.update_sound_profile(profile)

    def remove_profile(self, profile_id: int) -> None:
        sm.delete_sound_profile(profile_id)

    def active_id(self) -> Optional[int]:
        return self.state.active_sound_profile_id()

    def set_active(self, profile_id: int) -> None:
        self.state.set_active_sound_profile(profile_id)
        self._applied_device = object()
        self._apply_live()

    def default_profile_data(self) -> Dict[str, Any]:
        return copy.deepcopy(sm.SOUND_PROFILE_TEMPLATE)

    def load_editor(self, profile: Dict[str, Any]) -> None:
        apis = am.list_host_apis()
        host_api = profile.get("host-api")
        if host_api is None:
            host_api = next((a.index for a in apis if _PREFERRED_API in a.name), apis[0].index if apis else None)
        self.api_combo.set_items([(host_api_label(a.name), a.index) for a in apis], host_api)
        self._fill_devices(profile.get("microphone"), profile.get("microphone-name", "Default"))
        self.noise_switch.setChecked(bool(profile.get("unnoised")))
        self.algorithm_combo.setCurrentIndex(max(0, self.algorithm_combo.findData(profile.get("noise-algorithm"))))
        self.threshold.setValue(float(profile.get("noise-threshold", 15.0)))
        self.compressor_switch.setChecked(bool(profile.get("compressor-enabled")))
        self.comp_threshold.setValue(float(profile.get("compressor-threshold", 60.0)))
        self.comp_ratio.setValue(float(profile.get("compressor-ratio", 4.0)))
        self._sync_enabled()
        self._apply_live()

    def editor_data(self) -> Dict[str, Any]:
        device = self.device_combo.currentData()
        device_id = None if device in (None, _DEFAULT_DEVICE) else int(device)
        if device_id is None:
            device_name = "Default"
        else:
            device_name = next((d.name for d in self._devices if d.device_id == device_id), "Default")
        return {
            "host-api": self.api_combo.currentData(),
            "microphone": device_id,
            "microphone-name": device_name,
            "unnoised": self.noise_switch.isChecked(),
            "noise-algorithm": self.algorithm_combo.currentData() or "adaptive",
            "noise-threshold": float(self.threshold.value()),
            "compressor-enabled": self.compressor_switch.isChecked(),
            "compressor-threshold": float(self.comp_threshold.value()),
            "compressor-ratio": float(self.comp_ratio.value()),
        }

    def on_saved(self, profile: Dict[str, Any]) -> None:
        self._apply_live()

    def revert(self) -> None:
        super().revert()
        self._apply_live()

    # --- editor --------------------------------------------------------------
    def _fill_devices(self, wanted_id: Optional[int], wanted_name: str) -> None:
        self._devices = am.list_audio_devices(host_api_index=self.api_combo.currentData())
        items = []
        for device in self._devices:
            if device.device_id is None:
                items.append((i18n.t("mic.default"), _DEFAULT_DEVICE))
            elif device.is_output:
                items.append((i18n.t("sound.output_suffix", name=device.name), device.device_id))
            else:
                items.append((device.name, device.device_id))
        current = _DEFAULT_DEVICE if wanted_id is None else wanted_id
        if wanted_id is not None and all(d.device_id != wanted_id for d in self._devices):
            # Device indexes shift when hardware changes; fall back to the saved name.
            clean = (wanted_name or "").lstrip("🎤🔊 ").strip()
            current = next((d.device_id for d in self._devices if d.name == clean), _DEFAULT_DEVICE)
        self.device_combo.set_items(items, current)

    def _on_api_changed(self, index: int) -> None:
        if self._loading:
            return
        device = self.device_combo.currentData()
        self._fill_devices(None if device == _DEFAULT_DEVICE else device, self.device_combo.currentText())
        self._changed()

    def _sync_enabled(self) -> None:
        noise = self.noise_switch.isChecked()
        self.algorithm_combo.setEnabled(noise)
        self.threshold.setVisible(self.algorithm_combo.currentData() == "fixed")
        self.threshold.setEnabled(noise)
        compressor = self.compressor_switch.isChecked()
        self.comp_threshold.setEnabled(compressor)
        self.comp_ratio.setEnabled(compressor)

    def _changed(self, *args) -> None:
        if self._loading:
            return
        self._sync_enabled()
        self._apply_live()
        self.mark_changed()

    def _apply_live(self) -> None:
        """Let the user hear (see) the edited processing immediately when editing the
        active profile; saved values are restored on revert."""
        if self._selected_id is None or self._selected_id != self.active_id():
            return
        data = self.editor_data()
        am.set_noise_suppression(data["unnoised"])
        am.set_noise_algorithm(data["noise-algorithm"])
        am.set_noise_threshold(data["noise-threshold"])
        am.set_compressor(data["compressor-enabled"])
        am.set_compressor_threshold(data["compressor-threshold"])
        am.set_compressor_ratio(data["compressor-ratio"])
        if data["microphone"] != self._applied_device:
            self._applied_device = data["microphone"]
            am.start_monitor(data["microphone"])

    def _on_volume(self, volume: float) -> None:
        if self.isVisible():
            self.meter.set_level(volume)
            self.level_value.setText(str(int(volume)))

    def _refresh_mic_error(self) -> None:
        text = mic_error_text(self.state.mic_error)
        self.mic_error.setText(text)
        self.mic_error.setVisible(bool(text))

    def retranslate(self) -> None:
        self.header.set_text(i18n.t("sound.title"), i18n.t("sound.subtitle"))
        self.profile_list.set_title(i18n.t("sound.profiles"))
        self.input_card.set_title(i18n.t("sound.input"))
        self.api_label.setText(i18n.t("sound.host_api"))
        self.device_label.setText(i18n.t("sound.microphone"))
        self.level_label.setText(i18n.t("sound.level"))
        self.linux_hint.setText(i18n.t("sound.linux_hint"))
        self.noise_switch.set_text(i18n.t("sound.noise"), i18n.t("sound.noise_hint"))
        self.algorithm_label.setText(i18n.t("sound.algorithm"))
        loading, self._loading = self._loading, True
        current = self.algorithm_combo.currentData()
        self.algorithm_combo.set_items(
            [(i18n.t("sound.algo_adaptive"), "adaptive"), (i18n.t("sound.algo_fixed"), "fixed")], current
        )
        if self.device_combo.count():
            data = self.editor_data()
            self._fill_devices(data["microphone"], data["microphone-name"])
        self._loading = loading
        self.threshold.set_label(i18n.t("sound.threshold"))
        self.compressor_switch.set_text(i18n.t("sound.compressor"), i18n.t("sound.compressor_hint"))
        self.comp_threshold.set_label(i18n.t("sound.comp_threshold"))
        self.comp_ratio.set_label(i18n.t("sound.comp_ratio"))
        self._refresh_mic_error()
        self.retranslate_base()
