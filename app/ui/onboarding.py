"""First-run wizard: language, microphone, avatar images, voice calibration, OBS."""
import copy
from pathlib import Path
from typing import List, Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QGuiApplication
from PySide6.QtWidgets import (
    QButtonGroup,
    QDialog,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from app.modules import audio_manager as am, calibration, logic_manager as lm, storage_manager as sm
from app.ui import i18n, icons, pixmaps, theme
from app.ui.calibration_panel import CalibrationPanel, apply_gate
from app.ui.state import AppState
from app.ui.widgets.common import Combo, SwitchRow, clear_layout, muted
from app.ui.widgets.meter import LevelMeter


_DEFAULT_DEVICE = -1
_THUMB = 72


def default_thresholds(count: int) -> List[int]:
    if count <= 1:
        return [0][:count]
    return [0] + [int(round(20 + 60 * i / max(count - 2, 1))) for i in range(count - 1)]


def _page(title_widget: QLabel, text_widget: QLabel) -> QVBoxLayout:
    layout = QVBoxLayout()
    layout.setSpacing(12)
    title_widget.setFont(theme.font(16, QFont.DemiBold))
    title_widget.setWordWrap(True)
    text_widget.setWordWrap(True)
    layout.addWidget(title_widget)
    layout.addWidget(text_widget)
    return layout


class OnboardingDialog(QDialog):
    def __init__(self, parent: QWidget, state: AppState):
        super().__init__(parent)
        self.state = state
        self.setWindowTitle("PNG Streamer")
        self.setMinimumSize(720, 560)
        self._own_images: List[str] = []
        self._calibration: Optional[calibration.Calibration] = None

        root = QVBoxLayout(self)
        root.setContentsMargins(28, 24, 28, 20)
        root.setSpacing(16)
        self.step_label = muted()
        root.addWidget(self.step_label)
        self.pages = QStackedWidget()
        root.addWidget(self.pages, 1)

        self._build_welcome()
        self._build_microphone()
        self._build_avatar()
        self._build_calibration()
        self._build_done()

        buttons = QHBoxLayout()
        self.skip_button = QPushButton()
        self.skip_button.setObjectName("flat")
        self.skip_button.setCursor(Qt.PointingHandCursor)
        self.skip_button.clicked.connect(self._skip)
        self.back_button = QPushButton()
        self.back_button.setCursor(Qt.PointingHandCursor)
        self.back_button.clicked.connect(lambda: self._go(self.pages.currentIndex() - 1))
        self.next_button = QPushButton()
        self.next_button.setObjectName("primary")
        self.next_button.setCursor(Qt.PointingHandCursor)
        self.next_button.clicked.connect(self._next)
        buttons.addWidget(self.skip_button)
        buttons.addStretch()
        buttons.addWidget(self.back_button)
        buttons.addWidget(self.next_button)
        root.addLayout(buttons)

        state.volume_changed.connect(self._on_volume)
        state.language_changed.connect(self._retranslate)
        self._retranslate()
        self._go(0)

    # --- pages ---------------------------------------------------------------
    def _build_welcome(self) -> None:
        page = QWidget()
        self.welcome_title, self.welcome_text = QLabel(), muted()
        layout = _page(self.welcome_title, self.welcome_text)
        language = Combo()
        language.setMinimumWidth(220)
        language.set_items([(i18n.LANGUAGE_NAMES[code], code) for code in i18n.LANGUAGES], i18n.get_language())
        language.currentIndexChanged.connect(lambda _: self.state.set_language(language.currentData()))
        holder = QHBoxLayout()
        holder.addWidget(language)
        holder.addStretch()
        layout.addSpacing(8)
        layout.addLayout(holder)
        layout.addStretch()
        page.setLayout(layout)
        self.pages.addWidget(page)

    def _build_microphone(self) -> None:
        page = QWidget()
        self.mic_title, self.mic_text = QLabel(), muted()
        layout = _page(self.mic_title, self.mic_text)
        grid = QGridLayout()
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(6)
        self.api_label, self.device_label = muted(), muted()
        self.api_combo, self.device_combo = Combo(), Combo()
        grid.addWidget(self.api_label, 0, 0)
        grid.addWidget(self.device_label, 0, 1)
        grid.addWidget(self.api_combo, 1, 0)
        grid.addWidget(self.device_combo, 1, 1)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 2)
        self.api_combo.setMinimumWidth(190)  # "Windows WASAPI" fits
        layout.addLayout(grid)
        self.mic_meter = LevelMeter(segments=40, show_scale=False)
        layout.addSpacing(8)
        layout.addWidget(self.mic_meter)
        self.mic_hint = muted("", "faint", wrap=True)
        layout.addWidget(self.mic_hint)
        layout.addStretch()
        page.setLayout(layout)
        self.pages.addWidget(page)

        sound = lm.get_active_sound_profile() or {}
        apis = am.list_host_apis()
        preferred = "WASAPI" if not self._is_linux() else "ALSA"
        host_api = sound.get("host-api")
        if host_api is None:
            host_api = next((a.index for a in apis if preferred in a.name), apis[0].index if apis else None)
        self.api_combo.set_items([(a.name, a.index) for a in apis], host_api)
        self._fill_devices(sound.get("microphone"))
        self.api_combo.currentIndexChanged.connect(lambda _: (self._fill_devices(None), self._apply_device()))
        self.device_combo.currentIndexChanged.connect(lambda _: self._apply_device())

    @staticmethod
    def _is_linux() -> bool:
        import sys

        return sys.platform.startswith("linux")

    def _fill_devices(self, wanted: Optional[int]) -> None:
        self._devices = [d for d in am.list_audio_devices(self.api_combo.currentData()) if not d.is_output]
        items = [
            (i18n.t("mic.default") if d.device_id is None else d.name, _DEFAULT_DEVICE if d.device_id is None else d.device_id)
            for d in self._devices
        ]
        self.device_combo.set_items(items, _DEFAULT_DEVICE if wanted is None else wanted)

    def _apply_device(self) -> None:
        profile = lm.get_active_sound_profile()
        if profile is None:
            return
        device = self.device_combo.currentData()
        device_id = None if device in (None, _DEFAULT_DEVICE) else int(device)
        name = next((d.name for d in self._devices if d.device_id == device_id), "Default")
        profile.update({"host-api": self.api_combo.currentData(), "microphone": device_id, "microphone-name": name})
        sm.update_sound_profile(profile)
        am.start_monitor(device_id)

    def _build_avatar(self) -> None:
        page = QWidget()
        self.avatar_title, self.avatar_text = QLabel(), muted()
        layout = _page(self.avatar_title, self.avatar_text)
        segmented = QFrame()
        segmented.setObjectName("segmented")
        row = QHBoxLayout(segmented)
        row.setContentsMargins(3, 3, 3, 3)
        row.setSpacing(2)
        self.sample_button = QPushButton()
        self.own_button = QPushButton()
        group = QButtonGroup(self)
        for button in (self.sample_button, self.own_button):
            button.setObjectName("segment")
            button.setCheckable(True)
            button.setCursor(Qt.PointingHandCursor)
            group.addButton(button)
            row.addWidget(button)
            button.clicked.connect(self._refresh_avatar)
        self.sample_button.setChecked(True)
        holder = QHBoxLayout()
        holder.addWidget(segmented)
        holder.addStretch()
        layout.addLayout(holder)

        self.pick_button = QPushButton()
        self.pick_button.setIcon(icons.icon("upload", theme.TEXT))
        self.pick_button.setCursor(Qt.PointingHandCursor)
        self.pick_button.clicked.connect(self._pick_images)
        self.own_hint = muted("", "faint", wrap=True)
        self.thumbs = QHBoxLayout()
        self.thumbs.setSpacing(8)
        thumbs_holder = QHBoxLayout()
        thumbs_holder.addLayout(self.thumbs)
        thumbs_holder.addStretch()
        layout.addWidget(self.pick_button, 0, Qt.AlignLeft)
        layout.addWidget(self.own_hint)
        layout.addLayout(thumbs_holder)
        layout.addStretch()
        page.setLayout(layout)
        page.setAcceptDrops(True)
        page.dragEnterEvent = self._drag_enter
        page.dropEvent = self._drop
        self.pages.addWidget(page)

    def _refresh_avatar(self) -> None:
        own = self.own_button.isChecked()
        self.pick_button.setVisible(own)
        self.own_hint.setVisible(own)
        clear_layout(self.thumbs)
        names = self._own_images if own else [f.get("path-to-image") for f in self._sample_frames()]
        for name in names:
            label = QLabel()
            label.setFixedSize(_THUMB, _THUMB)
            label.setAlignment(Qt.AlignCenter)
            label.setStyleSheet(f"background: {theme.FIELD}; border: 1px solid {theme.BORDER}; border-radius: 10px;")
            pm = pixmaps.load(lm.resolve_image_path(name), _THUMB - 8)
            if pm is not None:
                label.setPixmap(pm)
            label.setToolTip(name)
            self.thumbs.addWidget(label)
        self._update_buttons()

    def _sample_frames(self) -> list:
        profile = lm.get_active_image_profile()
        return lm.sorted_frames(profile) if profile and not lm.is_advanced(profile) else []

    def _pick_images(self) -> None:
        files, _ = QFileDialog.getOpenFileNames(self, i18n.t("images.import"), "", i18n.t("images.import_filter"))
        self._add_images([Path(f) for f in files])

    def _add_images(self, files: List[Path]) -> None:
        imported = lm.import_images(sorted(files, key=lambda f: f.name.lower()))
        for name in imported:
            if name not in self._own_images:
                self._own_images.append(name)
        if imported:
            self.own_button.setChecked(True)
            self.state.images_changed.emit()
        self._refresh_avatar()

    def _drag_enter(self, event) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def _drop(self, event) -> None:
        self._add_images([Path(u.toLocalFile()) for u in event.mimeData().urls() if u.isLocalFile()])
        event.acceptProposedAction()

    def _frame_count(self) -> int:
        return len(self._own_images) if self.own_button.isChecked() else len(self._sample_frames())

    def _build_calibration(self) -> None:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(12)
        self.calibration_panel = CalibrationPanel(self.state, self._frame_count)
        self.calibration_panel.finished.connect(self._on_calibrated)
        layout.addWidget(self.calibration_panel)
        self.calibration_skip_hint = muted("", "faint", wrap=True)
        layout.addWidget(self.calibration_skip_hint)
        layout.addStretch()
        self.pages.addWidget(page)

    def _on_calibrated(self, result) -> None:
        self._calibration = result

    def _build_done(self) -> None:
        page = QWidget()
        self.done_title, self.done_text = QLabel(), muted()
        layout = _page(self.done_title, self.done_text)
        row = QHBoxLayout()
        self.url = QLineEdit()
        self.url.setObjectName("url")
        self.url.setReadOnly(True)
        self.url.setFont(theme.mono_font())
        self.copy_button = QPushButton()
        self.copy_button.setObjectName("primary")
        self.copy_button.setIcon(icons.icon("copy", theme.ACCENT_INK))
        self.copy_button.setCursor(Qt.PointingHandCursor)
        self.copy_button.clicked.connect(lambda: QGuiApplication.clipboard().setText(self.url.text()))
        row.addWidget(self.url, 1)
        row.addWidget(self.copy_button)
        layout.addLayout(row)
        self.obs_steps = muted("", wrap=True)
        layout.addWidget(self.obs_steps)
        self.autostart_server = SwitchRow()
        self.autostart_server.setChecked(True)
        layout.addSpacing(6)
        layout.addWidget(self.autostart_server)
        layout.addStretch()
        page.setLayout(layout)
        self.pages.addWidget(page)

    # --- navigation ----------------------------------------------------------
    def _go(self, index: int) -> None:
        index = max(0, min(index, self.pages.count() - 1))
        if self.pages.currentIndex() == 3 and index != 3:
            self.calibration_panel.cancel()
        if index == 2:
            self._refresh_avatar()
        if index == self.pages.count() - 1:
            self._prepare_done()
        self.pages.setCurrentIndex(index)
        self._update_buttons()

    def _update_buttons(self) -> None:
        index = self.pages.currentIndex()
        last = index == self.pages.count() - 1
        self.step_label.setText(i18n.t("onboarding.step", current=index + 1, total=self.pages.count()))
        self.back_button.setVisible(index > 0)
        self.skip_button.setVisible(not last)
        self.next_button.setText(i18n.t("onboarding.finish" if last else "onboarding.next"))
        self.next_button.setEnabled(not (index == 2 and self.own_button.isChecked() and not self._own_images))

    def _next(self) -> None:
        if self.pages.currentIndex() == self.pages.count() - 1:
            self._finish()
        else:
            self._go(self.pages.currentIndex() + 1)

    def _on_volume(self, volume: float) -> None:
        if self.isVisible() and self.pages.currentIndex() == 1:
            self.mic_meter.set_level(volume)

    # --- result --------------------------------------------------------------
    def _apply_avatar(self) -> None:
        result = self._calibration
        if result is not None:
            apply_gate(result)
        if self.own_button.isChecked() and self._own_images:
            thresholds = result.thresholds if result and len(result.thresholds) == len(self._own_images) else None
            thresholds = thresholds or default_thresholds(len(self._own_images))
            frames = [
                {"id": i, "path-to-image": name, "volume-level": level, "shake-level": 0}
                for i, (name, level) in enumerate(zip(self._own_images, thresholds))
            ]
            data = {"images": frames}
            created = sm.create_profile(i18n.t("onboarding.avatar_name"), data)
            self.state.set_active_image_profile(created["id"])
        elif result is not None:
            profile = lm.get_active_image_profile()
            if profile and not lm.is_advanced(profile) and profile.get("images"):
                profile = copy.deepcopy(profile)
                ordered = sorted(profile["images"], key=lambda f: f.get("volume-level", 0))
                for frame, level in zip(ordered, result.thresholds):
                    frame["volume-level"] = level
                sm.update_profile(profile)
        self.state.profiles_changed.emit()

    def _prepare_done(self) -> None:
        if not self.state.server_running():
            self.state.start_server()
        self.url.setText(self.state.widget_url() if self.state.server_running() else "")

    def _finish(self) -> None:
        self._apply_avatar()
        self.state.update_settings(
            onboarding_done=True, start_server_on_launch=self.autostart_server.isChecked()
        )
        self.accept()

    def _skip(self) -> None:
        self.reject()

    def reject(self) -> None:
        # Skip button, Esc and the window's close button all end up here.
        self.calibration_panel.cancel()
        self.state.update_settings(onboarding_done=True)
        super().reject()

    def _retranslate(self) -> None:
        self.welcome_title.setText(i18n.t("onboarding.welcome_title"))
        self.welcome_text.setText(i18n.t("onboarding.welcome_text"))
        self.mic_title.setText(i18n.t("onboarding.mic_title"))
        self.mic_text.setText(i18n.t("onboarding.mic_text"))
        self.api_label.setText(i18n.t("sound.host_api"))
        self.device_label.setText(i18n.t("sound.microphone"))
        self.mic_hint.setText(i18n.t("sound.linux_hint") if self._is_linux() else "")
        self.mic_hint.setVisible(self._is_linux())
        self.avatar_title.setText(i18n.t("onboarding.avatar_title"))
        self.avatar_text.setText(i18n.t("onboarding.avatar_text"))
        self.sample_button.setText(i18n.t("onboarding.use_sample"))
        self.own_button.setText(i18n.t("onboarding.use_own"))
        self.pick_button.setText(" " + i18n.t("onboarding.pick_images"))
        self.own_hint.setText(i18n.t("onboarding.own_hint"))
        self.calibration_skip_hint.setText(i18n.t("onboarding.calibration_skip"))
        self.done_title.setText(i18n.t("onboarding.done_title"))
        self.done_text.setText(i18n.t("onboarding.done_text"))
        self.copy_button.setText(" " + i18n.t("launch.copy"))
        self.obs_steps.setText(i18n.t("launch.obs_hint"))
        self.autostart_server.set_text(i18n.t("settings.start_server"))
        self.skip_button.setText(i18n.t("onboarding.skip"))
        self.back_button.setText(i18n.t("onboarding.back"))
        self.calibration_panel._show_idle()
        self._update_buttons()
