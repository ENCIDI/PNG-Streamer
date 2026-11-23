import time
from typing import Callable, List, Optional

from PySide6.QtCore import QTimer, Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QDialog, QHBoxLayout, QLabel, QProgressBar, QPushButton, QVBoxLayout, QWidget

from app.modules import audio_manager as am, calibration, logic_manager as lm, storage_manager as sm
from app.ui import i18n, theme
from app.ui.state import AppState
from app.ui.widgets.common import muted
from app.ui.widgets.meter import LevelMeter

SILENCE_SECONDS = 3.0
SPEECH_SECONDS = 6.0


class CalibrationPanel(QWidget):
    """Records a few seconds of silence and speech and emits the result."""

    finished = Signal(object)  # calibration.Calibration

    def __init__(self, state: AppState, frame_count: Callable[[], int]):
        super().__init__()
        self.state = state
        self._frame_count = frame_count
        self._phase = "idle"
        self._started = 0.0
        self._silence: List[float] = []
        self._speech: List[float] = []
        self.result: Optional[calibration.Calibration] = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        self.instruction = QLabel()
        self.instruction.setFont(theme.font(12, QFont.DemiBold))
        self.instruction.setWordWrap(True)
        layout.addWidget(self.instruction)
        self.detail = muted("", wrap=True)
        layout.addWidget(self.detail)
        self.meter = LevelMeter(segments=40, show_scale=False)
        layout.addWidget(self.meter)
        self.progress = QProgressBar()
        self.progress.setRange(0, 1000)
        self.progress.setTextVisible(False)
        layout.addWidget(self.progress)
        row = QHBoxLayout()
        self.start_button = QPushButton()
        self.start_button.setObjectName("primary")
        self.start_button.setCursor(Qt.PointingHandCursor)
        self.start_button.clicked.connect(self.start)
        row.addWidget(self.start_button)
        row.addStretch()
        layout.addLayout(row)

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        state.volume_changed.connect(self._on_volume)
        self._show_idle()

    def _show_idle(self) -> None:
        self.instruction.setText(i18n.t("calibration.title"))
        self.detail.setText(i18n.t("calibration.intro"))
        self.start_button.setText(i18n.t("calibration.start"))
        self.start_button.setEnabled(True)
        self.progress.setValue(0)

    def start(self) -> None:
        self._silence, self._speech = [], []
        self.result = None
        # Raw levels: the gate and the compressor would hide what we measure.
        am.set_noise_suppression(False)
        am.set_compressor(False)
        self._phase = "silence"
        self._started = time.monotonic()
        self.instruction.setText(i18n.t("calibration.silence"))
        self.detail.setText(i18n.t("calibration.silence_hint"))
        self.start_button.setEnabled(False)
        self._timer.start(50)

    def _on_volume(self, volume: float) -> None:
        if not self.isVisible():
            return
        self.meter.set_level(volume)
        if self._phase == "silence":
            self._silence.append(volume)
        elif self._phase == "speech":
            self._speech.append(volume)

    def _tick(self) -> None:
        elapsed = time.monotonic() - self._started
        if self._phase == "silence":
            self.progress.setValue(int(elapsed / (SILENCE_SECONDS + SPEECH_SECONDS) * 1000))
            if elapsed >= SILENCE_SECONDS:
                self._phase = "speech"
                self.instruction.setText(i18n.t("calibration.speech"))
                self.detail.setText(i18n.t("calibration.speech_hint"))
        elif self._phase == "speech":
            self.progress.setValue(int(min(elapsed / (SILENCE_SECONDS + SPEECH_SECONDS), 1) * 1000))
            if elapsed >= SILENCE_SECONDS + SPEECH_SECONDS:
                self._finish()

    def _finish(self) -> None:
        self._timer.stop()
        self._phase = "idle"
        restore_processing()
        try:
            self.result = calibration.analyze(self._silence, self._speech, max(self._frame_count(), 1))
        except calibration.CalibrationError:
            self.instruction.setText(i18n.t("calibration.failed"))
            self.detail.setText(i18n.t("calibration.failed_hint"))
            self.start_button.setText(i18n.t("calibration.retry"))
            self.start_button.setEnabled(True)
            return
        self.instruction.setText(i18n.t("calibration.done"))
        self.detail.setText(
            i18n.t(
                "calibration.result",
                gate=self.result.gate,
                thresholds=", ".join(str(t) for t in self.result.thresholds),
            )
        )
        self.start_button.setText(i18n.t("calibration.retry"))
        self.start_button.setEnabled(True)
        self.finished.emit(self.result)

    def cancel(self) -> None:
        if self._phase != "idle":
            self._timer.stop()
            self._phase = "idle"
            restore_processing()


def restore_processing() -> None:
    profile = lm.get_active_sound_profile() or {}
    am.set_noise_suppression(bool(profile.get("unnoised", False)))
    am.set_compressor(bool(profile.get("compressor-enabled", False)))


def apply_gate(result: calibration.Calibration) -> None:
    """Store the measured noise gate in the active sound profile."""
    profile = lm.get_active_sound_profile()
    if profile is None:
        return
    profile.update({"unnoised": True, "noise-algorithm": "fixed", "noise-threshold": float(result.gate)})
    sm.update_sound_profile(profile)
    am.set_noise_algorithm("fixed")
    am.set_noise_threshold(result.gate)
    am.set_noise_suppression(True)


class CalibrationDialog(QDialog):
    def __init__(self, parent: QWidget, state: AppState, frame_count: int):
        super().__init__(parent)
        self.setWindowTitle("PNG Streamer")
        self.setMinimumWidth(480)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 22, 24, 20)
        self.panel = CalibrationPanel(state, lambda: frame_count)
        layout.addWidget(self.panel)
        buttons = QHBoxLayout()
        buttons.addStretch()
        self.cancel_button = QPushButton(i18n.t("common.cancel"))
        self.cancel_button.clicked.connect(self.reject)
        self.apply_button = QPushButton(i18n.t("calibration.apply"))
        self.apply_button.setObjectName("primary")
        self.apply_button.setEnabled(False)
        self.apply_button.clicked.connect(self.accept)
        buttons.addWidget(self.cancel_button)
        buttons.addWidget(self.apply_button)
        layout.addSpacing(8)
        layout.addLayout(buttons)
        self.panel.finished.connect(lambda _: self.apply_button.setEnabled(True))

    def done(self, code: int) -> None:
        self.panel.cancel()
        super().done(code)
