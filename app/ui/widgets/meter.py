from typing import List, Optional, Tuple

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QPainter, QPainterPath, QPen, QPixmap
from PySide6.QtWidgets import QSizePolicy, QWidget

from app.ui import theme

_THUMB = 26
_BAR_HEIGHT = 24
_GAP = 3
_PEAK_DECAY_PER_SECOND = 25.0


class LevelMeter(QWidget):
    """Segmented volume meter. Optional frame thumbnails sit on their thresholds,
    the frame that is currently shown gets highlighted."""

    def __init__(self, segments: int = 44, show_scale: bool = True):
        super().__init__()
        self._segments = segments
        self._show_scale = show_scale
        self._frames: List[Tuple[int, Optional[QPixmap]]] = []
        self._level = 0.0
        self._peak = 0.0
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self._update_height()

    def _update_height(self) -> None:
        top = _THUMB + 14 if self._frames else 0
        bottom = 22 if self._show_scale else 0
        self.setFixedHeight(top + _BAR_HEIGHT + bottom)

    def set_frames(self, frames: List[Tuple[int, Optional[QPixmap]]]) -> None:
        size = _THUMB * 2  # rendered at 2x for HiDPI screens
        self._frames = sorted(
            (
                (threshold, pm.scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation) if pm else None)
                for threshold, pm in frames
            ),
            key=lambda item: item[0],
        )
        self._update_height()
        self.update()

    def set_level(self, level: float, dt: float = 1 / 30) -> None:
        self._level = max(0.0, min(level, 100.0))
        self._peak = max(self._peak - _PEAK_DECAY_PER_SECOND * dt, self._level)
        self.update()

    def active_index(self) -> int:
        index = 0
        for i, (threshold, _) in enumerate(self._frames):
            if self._level >= threshold:
                index = i
        return index

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w = self.width()
        top = _THUMB + 14 if self._frames else 0
        n = self._segments
        seg = (w - _GAP * (n - 1)) / n
        peak_seg = min(int(self._peak / 100 * n), n - 1)
        p.setPen(Qt.NoPen)
        for i in range(n):
            x = i * (seg + _GAP)
            if (i + 0.5) / n * 100 <= self._level:
                c = theme.color(theme.ACCENT, 0.55 + 0.45 * (i / n))
            elif i == peak_seg and self._peak > 2:
                c = theme.color(theme.ACCENT, 0.9)
            else:
                c = theme.color(theme.DIM_SEGMENT)
            p.setBrush(c)
            p.drawRoundedRect(QRectF(x, top, seg, _BAR_HEIGHT), 2, 2)

        if self._frames:
            active = self.active_index()
            half = _THUMB / 2
            for i, (threshold, pm) in enumerate(self._frames):
                x = min(max(threshold / 100 * w, half + 1), w - half - 1)
                is_active = i == active
                line = theme.color(theme.TEXT if is_active else theme.FAINT, 0.9 if is_active else 0.6)
                p.setPen(QPen(line, 1.2, Qt.SolidLine if is_active else Qt.DashLine))
                p.drawLine(QPointF(x, _THUMB + 4), QPointF(x, top + _BAR_HEIGHT + 4))
                r = QRectF(x - half, 2, _THUMB, _THUMB)
                p.setPen(Qt.NoPen)
                p.setBrush(theme.color(theme.SURFACE_2))
                p.drawEllipse(r)
                if pm is not None and not pm.isNull():
                    clip = QPainterPath()
                    clip.addEllipse(r)
                    p.save()
                    p.setClipPath(clip)
                    p.setOpacity(1.0 if is_active else 0.55)
                    target = QRectF(0, 0, pm.width() / 2, pm.height() / 2)
                    target.moveCenter(r.center())
                    p.drawPixmap(target, pm, QRectF(pm.rect()))
                    p.restore()
                p.setBrush(Qt.NoBrush)
                p.setPen(QPen(theme.color(theme.ACCENT if is_active else theme.BORDER), 1.6))
                p.drawEllipse(r)

        if self._show_scale:
            p.setPen(theme.color(theme.FAINT))
            p.setFont(theme.font(8))
            y = top + _BAR_HEIGHT + 6
            for value in (0, 25, 50, 75, 100):
                x = value / 100 * w
                if value == 0:
                    p.drawText(QRectF(x, y, 40, 16), Qt.AlignLeft, str(value))
                elif value == 100:
                    p.drawText(QRectF(x - 40, y, 40, 16), Qt.AlignRight, str(value))
                else:
                    p.drawText(QRectF(x - 20, y, 40, 16), Qt.AlignHCenter, str(value))
