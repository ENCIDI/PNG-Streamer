from PySide6.QtCore import QEasingCurve, QPoint, QPropertyAnimation, QTimer, Qt
from PySide6.QtWidgets import QFrame, QGraphicsOpacityEffect, QHBoxLayout, QLabel, QWidget

from app.ui import icons, theme

_VISIBLE_MS = 2600


class Toast(QFrame):
    """Short in-window notification shown at the bottom center of its parent."""

    def __init__(self, parent: QWidget):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 10, 16, 10)
        layout.setSpacing(10)
        self._icon = QLabel()
        self._text = QLabel()
        layout.addWidget(self._icon)
        layout.addWidget(self._text)
        self._opacity = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self._opacity)
        self._fade = QPropertyAnimation(self._opacity, b"opacity", self)
        self._fade.setDuration(180)
        self._slide = QPropertyAnimation(self, b"pos", self)
        self._slide.setDuration(220)
        self._slide.setEasingCurve(QEasingCurve.OutCubic)
        self._hide_timer = QTimer(self)
        self._hide_timer.setSingleShot(True)
        self._hide_timer.timeout.connect(self._fade_out)
        self._fade.finished.connect(self._on_fade_finished)
        self.hide()

    def show_message(self, text: str, kind: str = "info") -> None:
        error = kind == "error"
        accent = theme.DANGER if error else theme.ACCENT
        self.setStyleSheet(
            f"Toast {{ background: {theme.SURFACE_3}; border: 1px solid {theme.rgba(accent, 0.45)};"
            f" border-radius: 12px; }}"
        )
        self._icon.setPixmap(icons.pixmap("warning" if error else "check_circle", accent, 18))
        self._text.setText(text)
        self._text.setWordWrap(False)
        self.adjustSize()
        max_width = int(self.parentWidget().width() * 0.8)
        if self.width() > max_width:
            self._text.setWordWrap(True)
            self.setFixedWidth(max_width)
            self.adjustSize()
        else:
            self.setMinimumWidth(0)
            self.setMaximumWidth(16777215)
        target = self._target_pos()
        self.move(target + QPoint(0, 16))
        self.show()
        self.raise_()
        self._slide.stop()
        self._slide.setStartValue(self.pos())
        self._slide.setEndValue(target)
        self._slide.start()
        self._fade.stop()
        self._fade.setStartValue(self._opacity.opacity() if self.isVisible() else 0.0)
        self._fade.setEndValue(1.0)
        self._fade.start()
        self._hide_timer.start(_VISIBLE_MS + (1400 if error else 0))

    def _target_pos(self) -> QPoint:
        parent = self.parentWidget()
        return QPoint((parent.width() - self.width()) // 2, parent.height() - self.height() - 28)

    def reposition(self) -> None:
        if self.isVisible():
            self.move(self._target_pos())

    def _fade_out(self) -> None:
        self._fade.stop()
        self._fade.setStartValue(self._opacity.opacity())
        self._fade.setEndValue(0.0)
        self._fade.start()

    def _on_fade_finished(self) -> None:
        if self._opacity.opacity() <= 0.01:
            self.hide()
