from typing import Callable, Optional

from PySide6.QtCore import Property, QEasingCurve, QPointF, QPropertyAnimation, QRectF, QSize, Qt, Signal
from PySide6.QtGui import QFont, QPainter, QPen
from PySide6.QtWidgets import (
    QAbstractButton,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QSlider,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from app.ui import icons, theme


def eyebrow(text: str = "") -> QLabel:
    label = QLabel(text)
    f = theme.font(8, QFont.DemiBold)
    f.setCapitalization(QFont.AllUppercase)
    f.setLetterSpacing(QFont.AbsoluteSpacing, 1.0)
    label.setFont(f)
    label.setObjectName("muted")
    return label


def chip(text: str = "") -> QLabel:
    label = QLabel(text)
    label.setObjectName("chip")
    label.setFont(theme.font(8.5))
    label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
    return label


def muted(text: str = "", object_name: str = "muted", wrap: bool = False) -> QLabel:
    label = QLabel(text)
    label.setObjectName(object_name)
    label.setWordWrap(wrap)
    return label


def number_field(minimum: int, maximum: int, step: int = 1) -> QSpinBox:
    field = QSpinBox()
    field.setRange(minimum, maximum)
    field.setSingleStep(step)
    field.setButtonSymbols(QSpinBox.NoButtons)
    # QSS padding does not reach the spin box's inner editor.
    field.lineEdit().setTextMargins(10, 0, 10, 0)
    return field


def clear_layout(layout) -> None:
    while layout.count():
        item = layout.takeAt(0)
        widget = item.widget()
        if widget is not None:
            widget.deleteLater()
        elif item.layout() is not None:
            clear_layout(item.layout())


class Card(QFrame):
    def __init__(self, title: str = "", aside: str = "", object_name: str = "card", margins: int = 20):
        super().__init__()
        self.setObjectName(object_name)
        self.body = QVBoxLayout(self)
        self.body.setContentsMargins(margins, margins - 2, margins, margins)
        self.body.setSpacing(14)
        self.title_label = eyebrow(title)
        self.aside_label = muted(aside, "faint")
        self.head_widget = QWidget()
        self.head = QHBoxLayout(self.head_widget)
        self.head.setContentsMargins(0, 0, 0, 0)
        self.head.setSpacing(8)
        self.head.addWidget(self.title_label)
        self.head.addStretch()
        self.head.addWidget(self.aside_label)
        self.body.addWidget(self.head_widget)
        self._sync_head()

    def _sync_head(self) -> None:
        has_actions = self.head.count() > 3
        self.head_widget.setVisible(bool(self.title_label.text() or self.aside_label.text()) or has_actions)

    def set_title(self, title: str, aside: Optional[str] = None) -> None:
        self.title_label.setText(title)
        if aside is not None:
            self.aside_label.setText(aside)
        self._sync_head()


class PageHeader(QWidget):
    def __init__(self):
        super().__init__()
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        titles = QVBoxLayout()
        titles.setSpacing(2)
        self.title = QLabel()
        self.title.setFont(theme.font(19, QFont.DemiBold))
        self.subtitle = muted()
        titles.addWidget(self.title)
        titles.addWidget(self.subtitle)
        layout.addLayout(titles)
        layout.addStretch()
        self.actions = QHBoxLayout()
        self.actions.setSpacing(10)
        layout.addLayout(self.actions)

    def set_text(self, title: str, subtitle: str) -> None:
        self.title.setText(title)
        self.subtitle.setText(subtitle)


class Combo(QComboBox):
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setCursor(Qt.PointingHandCursor)
        self.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
        self.setMinimumContentsLength(8)

    def wheelEvent(self, event) -> None:
        # Scrolling a page must not silently change profile/device selections.
        event.ignore()

    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        p = QPainter(self)
        color = theme.MUTED if self.isEnabled() else theme.FAINT
        icons.paint(p, "chevron_down", QRectF(self.width() - 26, self.height() / 2 - 8, 16, 16), color)

    def set_items(self, items, current_data=None) -> None:
        """items: iterable of (text, data). Keeps signals quiet while repopulating."""
        self.blockSignals(True)
        self.clear()
        for text, data in items:
            self.addItem(text, data)
        index = self.findData(current_data) if current_data is not None else -1
        self.setCurrentIndex(index if index >= 0 else (0 if self.count() else -1))
        self.blockSignals(False)


class Switch(QAbstractButton):
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setCheckable(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedSize(38, 22)
        self._offset = 0.0
        self._animation = QPropertyAnimation(self, b"offset", self)
        self._animation.setDuration(140)
        self._animation.setEasingCurve(QEasingCurve.OutCubic)
        self.toggled.connect(self._animate)

    def _get_offset(self) -> float:
        return self._offset

    def _set_offset(self, value: float) -> None:
        self._offset = value
        self.update()

    offset = Property(float, _get_offset, _set_offset)

    def _animate(self, checked: bool) -> None:
        self._animation.stop()
        self._animation.setEndValue(1.0 if checked else 0.0)
        self._animation.start()

    def setChecked(self, checked: bool) -> None:  # noqa: N802 - Qt API
        super().setChecked(checked)
        self._animation.stop()
        self._offset = 1.0 if checked else 0.0
        self.update()

    def sizeHint(self) -> QSize:
        return QSize(38, 22)

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        enabled = self.isEnabled()
        track_off = theme.color(theme.SURFACE_3)
        track_on = theme.color(theme.ACCENT if enabled else theme.FAINT)
        t = self._offset
        track = track_off if t < 0.5 else track_on
        p.setPen(QPen(theme.color(theme.BORDER_HOVER), 1) if t < 0.5 else Qt.NoPen)
        p.setBrush(track)
        p.drawRoundedRect(QRectF(0.5, 0.5, self.width() - 1, self.height() - 1), 11, 11)
        knob_x = 11 + t * (self.width() - 22)
        p.setPen(Qt.NoPen)
        knob = theme.ACCENT_INK if t >= 0.5 else (theme.TEXT if enabled else theme.FAINT)
        p.setBrush(theme.color(knob))
        p.drawEllipse(QPointF(knob_x, self.height() / 2), 7.5, 7.5)


class SwitchRow(QWidget):
    """A label (with optional hint) and a switch on the right."""

    toggled = Signal(bool)

    def __init__(self, text: str = "", hint: str = ""):
        super().__init__()
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        texts = QVBoxLayout()
        texts.setSpacing(2)
        self.label = QLabel(text)
        self.label.setWordWrap(True)
        self.hint = muted(hint, "faint", wrap=True)
        self.hint.setVisible(bool(hint))
        texts.addWidget(self.label)
        texts.addWidget(self.hint)
        layout.addLayout(texts, 1)
        self.switch = Switch()
        self.switch.toggled.connect(self.toggled)
        layout.addWidget(self.switch, 0, Qt.AlignTop)

    def set_text(self, text: str, hint: Optional[str] = None) -> None:
        self.label.setText(text)
        if hint is not None:
            self.hint.setText(hint)
            self.hint.setVisible(bool(hint))

    def isChecked(self) -> bool:  # noqa: N802 - mirrors Qt API
        return self.switch.isChecked()

    def setChecked(self, checked: bool) -> None:  # noqa: N802 - mirrors Qt API
        self.switch.blockSignals(True)
        self.switch.setChecked(checked)
        self.switch.blockSignals(False)

    def setEnabled(self, enabled: bool) -> None:  # noqa: N802 - mirrors Qt API
        super().setEnabled(enabled)
        self.label.setObjectName("" if enabled else "faint")
        self.label.style().polish(self.label)


class LabeledSlider(QWidget):
    valueChanged = Signal(int)

    def __init__(
        self,
        minimum: int,
        maximum: int,
        formatter: Callable[[int], str] = str,
        label: str = "",
    ):
        super().__init__()
        self._formatter = formatter
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        top = QHBoxLayout()
        self.label = muted(label)
        self.value_label = QLabel()
        self.value_label.setFont(theme.font(theme.BASE_POINT_SIZE, QFont.DemiBold))
        top.addWidget(self.label)
        top.addStretch()
        top.addWidget(self.value_label)
        layout.addLayout(top)
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(minimum, maximum)
        self.slider.setCursor(Qt.PointingHandCursor)
        self.slider.valueChanged.connect(self._on_change)
        layout.addWidget(self.slider)
        self._on_change(self.slider.value())

    def _on_change(self, value: int) -> None:
        self.value_label.setText(self._formatter(value))
        self.valueChanged.emit(value)

    def set_label(self, text: str) -> None:
        self.label.setText(text)

    def value(self) -> int:
        return self.slider.value()

    def setValue(self, value: float) -> None:  # noqa: N802 - mirrors Qt API
        self.slider.blockSignals(True)
        self.slider.setValue(int(round(value)))
        self.slider.blockSignals(False)
        self.value_label.setText(self._formatter(self.slider.value()))

    def setEnabled(self, enabled: bool) -> None:  # noqa: N802 - mirrors Qt API
        super().setEnabled(enabled)
        self.value_label.setObjectName("" if enabled else "faint")
        self.value_label.style().polish(self.value_label)


class StatusPill(QWidget):
    def __init__(self):
        super().__init__()
        self._text = ""
        self._live = False
        self._phase = 0.0
        self.setFont(theme.font(theme.BASE_POINT_SIZE, QFont.DemiBold))
        self.setFixedHeight(32)

    def set_state(self, live: bool, text: str) -> None:
        self._live = live
        self._text = text
        self.setFixedWidth(self.fontMetrics().horizontalAdvance(text) + 46)
        self.update()

    def tick(self, dt: float) -> None:
        if self._live and self.isVisible():
            self._phase = (self._phase + dt / 1.6) % 1.0
            self.update()

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        base = theme.ACCENT if self._live else theme.MUTED
        p.setPen(QPen(theme.color(base, 0.28 if self._live else 0.3), 1))
        p.setBrush(theme.color(base, 0.08 if self._live else 0.06))
        p.drawRoundedRect(QRectF(0.5, 0.5, self.width() - 1, self.height() - 1), 16, 16)
        center = QPointF(17, self.height() / 2)
        p.setPen(Qt.NoPen)
        if self._live:
            radius = 3.5 + 6 * self._phase
            p.setBrush(theme.color(base, 0.45 * (1 - self._phase)))
            p.drawEllipse(center, radius, radius)
        p.setBrush(theme.color(base))
        p.drawEllipse(center, 3.5, 3.5)
        p.setPen(theme.color(base))
        p.drawText(QRectF(30, 0, self.width() - 30, self.height()), Qt.AlignVCenter, self._text)
