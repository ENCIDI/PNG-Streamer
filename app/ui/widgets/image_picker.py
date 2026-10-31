from typing import Callable, List, Optional

from PySide6.QtCore import QPoint, QRectF, QSize, Qt, Signal
from PySide6.QtGui import QPainter, QPen
from PySide6.QtWidgets import QAbstractButton, QFrame, QGridLayout, QLabel, QPushButton, QScrollArea, QVBoxLayout, QWidget

from app.modules import logic_manager as lm
from app.ui import i18n, icons, pixmaps, theme

_COLUMNS = 5
_CELL = 64


class _Thumb(QAbstractButton):
    """Square thumbnail button; empty name renders as "none"."""

    def __init__(self, name: str, size: int, selected: bool = False, placeholder: str = ""):
        super().__init__()
        self.name = name
        self.selected = selected
        self.placeholder = placeholder
        self.setFixedSize(size, size)
        self.setCursor(Qt.PointingHandCursor)
        self.setToolTip(name or placeholder)
        self._hover = False

    def set_name(self, name: str) -> None:
        self.name = name
        self.setToolTip(name or self.placeholder)
        self.update()

    def enterEvent(self, event) -> None:
        self._hover = True
        self.update()

    def leaveEvent(self, event) -> None:
        self._hover = False
        self.update()

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.SmoothPixmapTransform)
        rect = QRectF(self.rect()).adjusted(1, 1, -1, -1)
        p.setPen(Qt.NoPen)
        p.setBrush(theme.color(theme.FIELD))
        p.drawRoundedRect(rect, 10, 10)
        pm = pixmaps.load(lm.resolve_image_path(self.name), self.width() * 2) if self.name else None
        if pm is not None:
            target = QRectF(0, 0, pm.width() / 2, pm.height() / 2)
            target.moveCenter(rect.center())
            p.drawPixmap(target, pm, QRectF(pm.rect()))
        elif self.name:
            icons.paint(p, "warning", QRectF(rect.center().x() - 10, rect.center().y() - 10, 20, 20), theme.WARNING)
        else:
            p.setPen(theme.color(theme.FAINT))
            p.setFont(theme.font(8.5))
            p.drawText(rect, Qt.AlignCenter, self.placeholder)
        if self.selected:
            border = QPen(theme.color(theme.ACCENT), 1.6)
        elif self._hover:
            border = QPen(theme.color(theme.BORDER_HOVER), 1.2)
        else:
            border = QPen(theme.color(theme.BORDER), 1)
        p.setPen(border)
        p.setBrush(Qt.NoBrush)
        p.drawRoundedRect(rect, 10, 10)


class _PickerPopup(QFrame):
    picked = Signal(str)

    def __init__(self, current: str, allow_none: bool, on_import: Callable[[], List[str]]):
        super().__init__(None, Qt.Popup | Qt.FramelessWindowHint | Qt.NoDropShadowWindowHint)
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.setObjectName("card")
        self._on_import = on_import
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)
        title = QLabel(i18n.t("images.pick_title"))
        title.setObjectName("muted")
        layout.addWidget(title)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        holder = QWidget()
        grid = QGridLayout(holder)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(6)
        names = ([""] if allow_none else []) + lm.list_available_images()
        for i, name in enumerate(names):
            thumb = _Thumb(name, _CELL, name == current, i18n.t("images.none"))
            thumb.clicked.connect(lambda _=False, n=name: self._pick(n))
            grid.addWidget(thumb, i // _COLUMNS, i % _COLUMNS)
        rows = max(1, (len(names) + _COLUMNS - 1) // _COLUMNS)
        scroll.setWidget(holder)
        scroll.setFixedSize(
            _COLUMNS * (_CELL + 6) + 4, min(rows, 4) * (_CELL + 6) + 2
        )
        layout.addWidget(scroll)

        add = QPushButton(" " + i18n.t("images.import"))
        add.setIcon(icons.icon("upload", theme.TEXT))
        add.setCursor(Qt.PointingHandCursor)
        add.clicked.connect(self._import)
        layout.addWidget(add)

    def _pick(self, name: str) -> None:
        self.picked.emit(name)
        self.close()

    def _import(self) -> None:
        imported = self._on_import()
        if imported:
            self._pick(imported[0])


class ImagePicker(_Thumb):
    changed = Signal(str)

    def __init__(self, on_import: Callable[[], List[str]], allow_none: bool = False, size: int = 72):
        super().__init__("", size, placeholder=i18n.t("images.none"))
        self._allow_none = allow_none
        self._on_import = on_import
        self.clicked.connect(self._open)

    def value(self) -> str:
        return self.name

    def set_value(self, name: str) -> None:
        self.set_name(name or "")

    def retranslate(self) -> None:
        self.placeholder = i18n.t("images.none")
        self.setToolTip(self.name or self.placeholder)
        self.update()

    def _open(self) -> None:
        popup = _PickerPopup(self.name, self._allow_none, self._on_import)
        popup.picked.connect(self._on_picked)
        popup.adjustSize()
        pos = self.mapToGlobal(QPoint(0, self.height() + 6))
        screen = self.screen().availableGeometry()
        if pos.y() + popup.height() > screen.bottom():
            pos = self.mapToGlobal(QPoint(0, -popup.height() - 6))
        pos.setX(min(pos.x(), screen.right() - popup.width()))
        popup.move(pos)
        popup.show()

    def _on_picked(self, name: str) -> None:
        if name != self.name:
            self.set_value(name)
            self.changed.emit(name)

    def sizeHint(self) -> QSize:
        return self.size()
