import math
from pathlib import Path
from typing import Optional

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QFont, QPainter, QPixmap, QRadialGradient
from PySide6.QtWidgets import QSizePolicy, QWidget

from app.ui import pixmaps, theme

# The OBS widget shakes by `shake-level` CSS pixels on a ~600px source;
# the preview scales the same motion down to its own size.
_WIDGET_REFERENCE_SIZE = 600.0
_SHAKE_SPEED = 2.2


def _smooth_noise(t: float, freq_a: float, freq_b: float) -> float:
    return math.sin(t * freq_a) * 0.65 + math.sin(t * freq_b + 1.7) * 0.35


class AvatarStage(QWidget):
    def __init__(self, minimum: int = 280):
        super().__init__()
        self._path: Optional[Path] = None
        self._shake = 0
        self._caption = ""
        self._empty_text = ""
        self._time = 0.0
        self._scaled: Optional[QPixmap] = None
        self._scaled_key = None
        self._background: Optional[QPixmap] = None
        self.setMinimumSize(minimum, minimum)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def set_frame(self, path: Optional[Path], shake: int, caption: str = "", empty_text: str = "") -> None:
        changed = path != self._path or caption != self._caption or empty_text != self._empty_text
        self._path = path
        self._shake = max(0, shake)
        self._caption = caption
        self._empty_text = empty_text
        if changed or self._shake:
            self.update()

    def tick(self, dt: float) -> None:
        self._time += dt
        if self._shake and self.isVisible():
            self.update()

    def _image(self, side: int) -> Optional[QPixmap]:
        key = (self._path, side)
        if key != self._scaled_key:
            source = pixmaps.load(self._path)
            dpr = self.devicePixelRatioF()
            if source is None:
                self._scaled = None
            else:
                self._scaled = source.scaled(
                    int(side * dpr), int(side * dpr), Qt.KeepAspectRatio, Qt.SmoothTransformation
                )
                self._scaled.setDevicePixelRatio(dpr)
            self._scaled_key = key
        return self._scaled

    def _render_background(self) -> QPixmap:
        dpr = self.devicePixelRatioF()
        background = QPixmap(int(self.width() * dpr), int(self.height() * dpr))
        background.setDevicePixelRatio(dpr)
        background.fill(Qt.transparent)
        p = QPainter(background)
        p.setRenderHint(QPainter.Antialiasing)
        rect = QRectF(self.rect())
        gradient = QRadialGradient(rect.center(), max(rect.width(), rect.height()) * 0.6)
        gradient.setColorAt(0, theme.color("#1D2028"))
        gradient.setColorAt(1, theme.color("#111318"))
        p.setPen(Qt.NoPen)
        p.setBrush(gradient)
        p.drawRoundedRect(rect, 12, 12)
        p.setBrush(theme.color(theme.TEXT, 0.05))
        step = 18
        for x in range(step // 2, int(rect.width()), step):
            for y in range(step // 2, int(rect.height()), step):
                p.drawEllipse(QPointF(x, y), 0.9, 0.9)
        p.end()
        return background

    def resizeEvent(self, event) -> None:
        self._background = None
        super().resizeEvent(event)

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.SmoothPixmapTransform)
        rect = QRectF(self.rect())
        if self._background is None:
            self._background = self._render_background()
        p.drawPixmap(QPointF(0, 0), self._background)

        side = int(min(rect.width(), rect.height()) * 0.84)
        image = self._image(side) if self._path else None
        if image is None:
            if self._empty_text:
                p.setPen(theme.color(theme.MUTED))
                p.drawText(rect, Qt.AlignCenter, self._empty_text)
            return

        scale = side / _WIDGET_REFERENCE_SIZE
        t = self._time * _SHAKE_SPEED
        dx = _smooth_noise(t, 12.0, 23.0) * self._shake * scale if self._shake else 0.0
        dy = _smooth_noise(t + 3.1, 15.0, 27.0) * self._shake * scale if self._shake else 0.0
        w = image.width() / image.devicePixelRatio()
        h = image.height() / image.devicePixelRatio()
        x = rect.center().x() - w / 2 + dx
        y = rect.center().y() - h / 2 + dy
        p.save()
        p.setClipRect(rect)
        p.drawPixmap(QPointF(x, y), image)
        p.restore()

        if self._caption:
            p.setFont(theme.font(8.5, QFont.DemiBold))
            width = p.fontMetrics().horizontalAdvance(self._caption) + 20
            chip = QRectF(12, rect.height() - 38, width, 26)
            p.setPen(Qt.NoPen)
            p.setBrush(theme.color(theme.BG, 0.78))
            p.drawRoundedRect(chip, 8, 8)
            p.setPen(theme.color(theme.TEXT))
            p.drawText(chip, Qt.AlignCenter, self._caption)
