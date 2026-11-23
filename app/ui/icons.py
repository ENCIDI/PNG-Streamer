"""Line icons drawn with QPainter on a 20x20 grid, so they stay crisp and recolorable."""
from typing import Callable, Dict

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPainterPath, QPen, QPixmap

from app.ui import theme

_GRID = 20.0


def _launch(p: QPainter) -> None:
    p.drawEllipse(QRectF(2.5, 2.5, 15, 15))
    path = QPainterPath(QPointF(8.5, 7))
    path.lineTo(13.5, 10)
    path.lineTo(8.5, 13)
    path.closeSubpath()
    p.drawPath(path)


def _mic(p: QPainter) -> None:
    p.drawRoundedRect(QRectF(7.5, 2.5, 5, 9.5), 2.5, 2.5)
    p.drawArc(QRectF(4.5, 5.5, 11, 9.5), 180 * 16, 180 * 16)
    p.drawLine(QPointF(10, 15), QPointF(10, 17.5))


def _image(p: QPainter) -> None:
    p.drawRoundedRect(QRectF(2.5, 3.5, 15, 13), 3, 3)
    p.drawEllipse(QPointF(7, 8), 1.4, 1.4)
    path = QPainterPath(QPointF(3, 15))
    for x, y in ((8, 11), (11, 13.5), (14, 10.5), (17.5, 14)):
        path.lineTo(x, y)
    p.drawPath(path)


def _settings(p: QPainter) -> None:
    for y, x in ((5, 13), (10, 7), (15, 11)):
        p.drawLine(QPointF(3, y), QPointF(x - 2.2, y))
        p.drawLine(QPointF(x + 2.2, y), QPointF(17, y))
        p.drawEllipse(QPointF(x, y), 2.2, 2.2)


def _copy(p: QPainter) -> None:
    p.drawRoundedRect(QRectF(6.5, 6.5, 10, 10), 2.5, 2.5)
    p.drawPolyline([QPointF(3.5, 12.5), QPointF(3.5, 5), QPointF(5, 3.5), QPointF(12.5, 3.5)])


def _plus(p: QPainter) -> None:
    p.drawLine(QPointF(10, 4), QPointF(10, 16))
    p.drawLine(QPointF(4, 10), QPointF(16, 10))


def _trash(p: QPainter) -> None:
    p.drawLine(QPointF(3.5, 5.5), QPointF(16.5, 5.5))
    p.drawPolyline([QPointF(8, 5.5), QPointF(8, 3.5), QPointF(12, 3.5), QPointF(12, 5.5)])
    p.drawPolyline([QPointF(5, 5.5), QPointF(6, 16.5), QPointF(14, 16.5), QPointF(15, 5.5)])


def _check(p: QPainter) -> None:
    p.drawPolyline([QPointF(4.5, 10.5), QPointF(8.5, 14.5), QPointF(15.5, 6)])


def _check_circle(p: QPainter) -> None:
    p.drawEllipse(QRectF(2.5, 2.5, 15, 15))
    p.drawPolyline([QPointF(6.8, 10.2), QPointF(9.2, 12.6), QPointF(13.4, 7.6)])


def _duplicate(p: QPainter) -> None:
    p.drawRoundedRect(QRectF(6.5, 6.5, 10, 10), 2.5, 2.5)
    p.drawPolyline([QPointF(3.5, 12.5), QPointF(3.5, 5), QPointF(5, 3.5), QPointF(12.5, 3.5)])
    p.drawLine(QPointF(11.5, 9), QPointF(11.5, 14))
    p.drawLine(QPointF(9, 11.5), QPointF(14, 11.5))


def _edit(p: QPainter) -> None:
    path = QPainterPath(QPointF(4, 16))
    path.lineTo(4.5, 12.5)
    path.lineTo(13, 4)
    path.lineTo(16, 7)
    path.lineTo(7.5, 15.5)
    path.closeSubpath()
    p.drawPath(path)
    p.drawLine(QPointF(11, 6), QPointF(14, 9))


def _folder(p: QPainter) -> None:
    path = QPainterPath(QPointF(2.5, 15.5))
    for x, y in ((2.5, 4.5), (8, 4.5), (9.5, 6.5), (17.5, 6.5), (17.5, 15.5)):
        path.lineTo(x, y)
    path.closeSubpath()
    p.drawPath(path)


def _upload(p: QPainter) -> None:
    p.drawLine(QPointF(10, 3.5), QPointF(10, 13))
    p.drawPolyline([QPointF(6, 7.5), QPointF(10, 3.5), QPointF(14, 7.5)])
    p.drawPolyline([QPointF(3.5, 12.5), QPointF(3.5, 16.5), QPointF(16.5, 16.5), QPointF(16.5, 12.5)])


def _chevron_down(p: QPainter) -> None:
    p.drawPolyline([QPointF(6, 8), QPointF(10, 12), QPointF(14, 8)])


def _chevron_up(p: QPainter) -> None:
    p.drawPolyline([QPointF(6, 12), QPointF(10, 8), QPointF(14, 12)])


def _pause(p: QPainter) -> None:
    p.drawLine(QPointF(7.5, 5), QPointF(7.5, 15))
    p.drawLine(QPointF(12.5, 5), QPointF(12.5, 15))


def _undo(p: QPainter) -> None:
    path = QPainterPath(QPointF(5, 9))
    path.cubicTo(QPointF(8, 5.5), QPointF(15.5, 6), QPointF(15.5, 11.5))
    p.drawPath(path)
    p.drawPolyline([QPointF(4.5, 5), QPointF(4.5, 9.5), QPointF(9, 9.5)])


def _redo(p: QPainter) -> None:
    path = QPainterPath(QPointF(15, 9))
    path.cubicTo(QPointF(12, 5.5), QPointF(4.5, 6), QPointF(4.5, 11.5))
    p.drawPath(path)
    p.drawPolyline([QPointF(15.5, 5), QPointF(15.5, 9.5), QPointF(11, 9.5)])


def _key(p: QPainter) -> None:
    path = QPainterPath(QPointF(10, 4))
    for x, y in ((16, 10), (10, 16), (4, 10)):
        path.lineTo(x, y)
    path.closeSubpath()
    p.drawPath(path)


def _grid(p: QPainter) -> None:
    p.drawRect(QRectF(3.5, 3.5, 13, 13))
    p.drawLine(QPointF(8, 3.5), QPointF(8, 16.5))
    p.drawLine(QPointF(12, 3.5), QPointF(12, 16.5))
    p.drawLine(QPointF(3.5, 8), QPointF(16.5, 8))
    p.drawLine(QPointF(3.5, 12), QPointF(16.5, 12))


def _move(p: QPainter) -> None:
    p.drawLine(QPointF(10, 3), QPointF(10, 17))
    p.drawLine(QPointF(3, 10), QPointF(17, 10))
    for a, b, c in (((8, 5), (10, 3), (12, 5)), ((8, 15), (10, 17), (12, 15)),
                    ((5, 8), (3, 10), (5, 12)), ((15, 8), (17, 10), (15, 12))):
        p.drawPolyline([QPointF(*a), QPointF(*b), QPointF(*c)])


def _record(p: QPainter) -> None:
    p.drawEllipse(QPointF(10, 10), 5, 5)


def _close(p: QPainter) -> None:
    p.drawLine(QPointF(5.5, 5.5), QPointF(14.5, 14.5))
    p.drawLine(QPointF(14.5, 5.5), QPointF(5.5, 14.5))


def _play(p: QPainter) -> None:
    path = QPainterPath(QPointF(6.5, 4.5))
    path.lineTo(15.5, 10)
    path.lineTo(6.5, 15.5)
    path.closeSubpath()
    p.drawPath(path)


def _stop(p: QPainter) -> None:
    p.drawRoundedRect(QRectF(5, 5, 10, 10), 2, 2)


def _download(p: QPainter) -> None:
    p.drawLine(QPointF(10, 3.5), QPointF(10, 13))
    p.drawPolyline([QPointF(6, 9), QPointF(10, 13), QPointF(14, 9)])
    p.drawLine(QPointF(4, 16.5), QPointF(16, 16.5))


def _info(p: QPainter) -> None:
    p.drawEllipse(QRectF(2.5, 2.5, 15, 15))
    p.drawLine(QPointF(10, 9), QPointF(10, 14))
    p.drawPoint(QPointF(10, 6.3))


def _warning(p: QPainter) -> None:
    path = QPainterPath(QPointF(10, 3))
    path.lineTo(17.5, 16.5)
    path.lineTo(2.5, 16.5)
    path.closeSubpath()
    p.drawPath(path)
    p.drawLine(QPointF(10, 8), QPointF(10, 11.5))
    p.drawPoint(QPointF(10, 14))


def _chat(p: QPainter) -> None:
    path = QPainterPath(QPointF(5.5, 3.5))
    path.lineTo(14.5, 3.5)
    path.quadTo(17, 3.5, 17, 6)
    path.lineTo(17, 11)
    path.quadTo(17, 13.5, 14.5, 13.5)
    path.lineTo(9, 13.5)
    path.lineTo(5.5, 16.5)
    path.lineTo(5.5, 13.5)
    path.quadTo(3, 13.5, 3, 11)
    path.lineTo(3, 6)
    path.quadTo(3, 3.5, 5.5, 3.5)
    p.drawPath(path)
    p.drawLine(QPointF(7, 7.5), QPointF(13, 7.5))
    p.drawLine(QPointF(7, 10), QPointF(11, 10))


def _eye(p: QPainter) -> None:
    path = QPainterPath(QPointF(2.5, 10))
    path.quadTo(QPointF(10, 2.5), QPointF(17.5, 10))
    path.quadTo(QPointF(10, 17.5), QPointF(2.5, 10))
    p.drawPath(path)
    p.drawEllipse(QPointF(10, 10), 2.6, 2.6)


def _eye_off(p: QPainter) -> None:
    _eye(p)
    p.drawLine(QPointF(4, 16), QPointF(16, 4))


def _lock(p: QPainter) -> None:
    p.drawRoundedRect(QRectF(4.5, 9, 11, 8), 1.8, 1.8)
    p.drawArc(QRectF(6.5, 3.5, 7, 9), 0, 180 * 16)
    p.drawLine(QPointF(6.5, 8), QPointF(6.5, 9))
    p.drawLine(QPointF(13.5, 8), QPointF(13.5, 9))


def _unlock(p: QPainter) -> None:
    p.drawRoundedRect(QRectF(4.5, 9, 11, 8), 1.8, 1.8)
    p.drawArc(QRectF(6.5, 2.5, 7, 9), 30 * 16, 150 * 16)
    p.drawLine(QPointF(6.5, 7), QPointF(6.5, 9))


def _to_start(p: QPainter) -> None:
    p.drawLine(QPointF(5.5, 5), QPointF(5.5, 15))
    path = QPainterPath(QPointF(15, 5))
    path.lineTo(8, 10)
    path.lineTo(15, 15)
    path.closeSubpath()
    p.drawPath(path)


def _to_end(p: QPainter) -> None:
    p.drawLine(QPointF(14.5, 5), QPointF(14.5, 15))
    path = QPainterPath(QPointF(5, 5))
    path.lineTo(12, 10)
    path.lineTo(5, 15)
    path.closeSubpath()
    p.drawPath(path)


def _loop(p: QPainter) -> None:
    p.drawArc(QRectF(3.5, 5, 13, 10), 30 * 16, 300 * 16)
    p.drawLine(QPointF(15.2, 6.5), QPointF(16.5, 9.5))
    p.drawLine(QPointF(16.5, 9.5), QPointF(13.3, 9.6))


def _key_prev(p: QPainter) -> None:
    path = QPainterPath(QPointF(13, 5))
    for x, y in ((18, 10), (13, 15), (8, 10)):
        path.lineTo(x, y)
    path.closeSubpath()
    p.drawPath(path)
    p.drawLine(QPointF(6, 6), QPointF(2.5, 10))
    p.drawLine(QPointF(2.5, 10), QPointF(6, 14))


def _key_next(p: QPainter) -> None:
    path = QPainterPath(QPointF(7, 5))
    for x, y in ((12, 10), (7, 15), (2, 10)):
        path.lineTo(x, y)
    path.closeSubpath()
    p.drawPath(path)
    p.drawLine(QPointF(14, 6), QPointF(17.5, 10))
    p.drawLine(QPointF(17.5, 10), QPointF(14, 14))


def _points(p: QPainter) -> None:
    for x in (4, 10, 16):
        for y in (4, 10, 16):
            p.drawEllipse(QPointF(x, y), 1.3, 1.3)
    p.drawLine(QPointF(4, 4), QPointF(16, 4))
    p.drawLine(QPointF(4, 4), QPointF(4, 16))


def _brush(p: QPainter) -> None:
    p.drawLine(QPointF(16.5, 3.5), QPointF(9, 11))
    path = QPainterPath(QPointF(9, 11))
    path.cubicTo(QPointF(5, 10), QPointF(4, 14), QPointF(3.5, 16.5))
    path.cubicTo(QPointF(7, 16.5), QPointF(10, 15), QPointF(9, 11))
    p.drawPath(path)


def _panel(p: QPainter, side: str) -> None:
    p.drawRoundedRect(QRectF(2.5, 3.5, 15, 13), 2, 2)
    p.setBrush(p.pen().color())
    if side == "left":
        p.drawRect(QRectF(3.5, 4.5, 4, 11))
    elif side == "right":
        p.drawRect(QRectF(12.5, 4.5, 4, 11))
    else:
        p.drawRect(QRectF(3.5, 11.5, 13, 4))
    p.setBrush(Qt.NoBrush)


def _history(p: QPainter) -> None:
    p.drawArc(QRectF(3, 3, 14, 14), 90 * 16, 290 * 16)
    p.drawLine(QPointF(10, 6.5), QPointF(10, 10))
    p.drawLine(QPointF(10, 10), QPointF(12.8, 11.8))
    p.drawLine(QPointF(3, 5), QPointF(4, 8.4))
    p.drawLine(QPointF(4, 8.4), QPointF(7.2, 7.2))


_DRAWERS: Dict[str, Callable[[QPainter], None]] = {
    "panel_left": lambda p: _panel(p, "left"),
    "panel_right": lambda p: _panel(p, "right"),
    "panel_bottom": lambda p: _panel(p, "bottom"),
    "history": _history,
    "to_start": _to_start,
    "to_end": _to_end,
    "loop": _loop,
    "key_prev": _key_prev,
    "key_next": _key_next,
    "points": _points,
    "brush": _brush,
    "eye": _eye,
    "eye_off": _eye_off,
    "lock": _lock,
    "unlock": _unlock,
    "chat": _chat,
    "launch": _launch,
    "mic": _mic,
    "image": _image,
    "settings": _settings,
    "copy": _copy,
    "plus": _plus,
    "trash": _trash,
    "check": _check,
    "check_circle": _check_circle,
    "duplicate": _duplicate,
    "edit": _edit,
    "folder": _folder,
    "upload": _upload,
    "chevron_down": _chevron_down,
    "chevron_up": _chevron_up,
    "pause": _pause,
    "undo": _undo,
    "redo": _redo,
    "key": _key,
    "grid": _grid,
    "move": _move,
    "record": _record,
    "close": _close,
    "play": _play,
    "stop": _stop,
    "download": _download,
    "info": _info,
    "warning": _warning,
}


def paint(painter: QPainter, kind: str, rect: QRectF, color: str, stroke: float = 1.6) -> None:
    painter.save()
    painter.setRenderHint(QPainter.Antialiasing)
    painter.translate(rect.topLeft())
    painter.scale(rect.width() / _GRID, rect.height() / _GRID)
    painter.setPen(QPen(QColor(color), stroke, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
    painter.setBrush(Qt.NoBrush)
    _DRAWERS[kind](painter)
    painter.restore()


def pixmap(kind: str, color: str, size: int = 20, dpr: float = 2.0) -> QPixmap:
    pm = QPixmap(int(size * dpr), int(size * dpr))
    pm.setDevicePixelRatio(dpr)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    paint(p, kind, QRectF(0, 0, size, size), color)
    p.end()
    return pm


def icon(kind: str, color: str = theme.MUTED, active_color: str = "", size: int = 20) -> QIcon:
    result = QIcon()
    result.addPixmap(pixmap(kind, color, size), QIcon.Normal, QIcon.Off)
    result.addPixmap(pixmap(kind, theme.FAINT, size), QIcon.Disabled, QIcon.Off)
    if active_color:
        result.addPixmap(pixmap(kind, active_color, size), QIcon.Normal, QIcon.On)
        result.addPixmap(pixmap(kind, active_color, size), QIcon.Active, QIcon.On)
    return result
