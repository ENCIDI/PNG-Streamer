from typing import Any, Dict, List, Optional

from PySide6.QtCore import QRectF, QSize, Qt, Signal
from PySide6.QtGui import QFont, QPainter
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMenu,
    QPushButton,
    QScrollArea,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from app.ui import i18n, icons, theme
from app.ui.widgets.common import eyebrow


class _ProfileItem(QFrame):
    clicked = Signal()

    def __init__(self, name: str, active: bool, selected: bool, dirty: bool, menu: QMenu):
        super().__init__()
        self._selected = selected
        self._hover = False
        self._active = active
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(48)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 0, 6, 0)
        layout.setSpacing(8)
        texts = QVBoxLayout()
        texts.setSpacing(0)
        texts.addStretch()
        title = QLabel(name + (" •" if dirty else ""))
        title.setFont(theme.font(theme.BASE_POINT_SIZE, QFont.DemiBold if selected else QFont.Normal))
        texts.addWidget(title)
        if active:
            badge = QLabel(i18n.t("profiles.active"))
            badge.setFont(theme.font(8))
            badge.setStyleSheet(f"color: {theme.ACCENT};")
            texts.addWidget(badge)
        texts.addStretch()
        layout.addLayout(texts, 1)
        more = QToolButton()
        more.setObjectName("flat")
        more.setText("⋯")
        more.setFont(theme.font(12))
        more.setCursor(Qt.PointingHandCursor)
        more.setPopupMode(QToolButton.InstantPopup)
        more.setMenu(menu)
        more.setFixedSize(QSize(30, 30))
        more.setStyleSheet("QToolButton::menu-indicator { image: none; width: 0; }")
        layout.addWidget(more)

    def enterEvent(self, event) -> None:
        self._hover = True
        self.update()

    def leaveEvent(self, event) -> None:
        self._hover = False
        self.update()

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.LeftButton and self.rect().contains(event.position().toPoint()):
            self.clicked.emit()

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(Qt.NoPen)
        if self._selected:
            p.setBrush(theme.color(theme.SURFACE_3))
        elif self._hover:
            p.setBrush(theme.color(theme.SURFACE_2))
        else:
            p.setBrush(Qt.NoBrush)
        p.drawRoundedRect(QRectF(self.rect()), 10, 10)
        if self._active:
            p.setBrush(theme.color(theme.ACCENT))
            p.drawRoundedRect(QRectF(0, 14, 3, self.height() - 28), 1.5, 1.5)


class ProfileList(QWidget):
    selected = Signal(int)
    create_requested = Signal()
    activate_requested = Signal(int)
    rename_requested = Signal(int)
    duplicate_requested = Signal(int)
    delete_requested = Signal(int)

    def __init__(self):
        super().__init__()
        self.setFixedWidth(240)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        head = QHBoxLayout()
        self.title = eyebrow()
        head.addWidget(self.title)
        head.addStretch()
        self.create_button = QPushButton()
        self.create_button.setObjectName("flat")
        self.create_button.setFixedSize(QSize(30, 30))
        self.create_button.setIcon(icons.icon("plus", theme.TEXT))
        self.create_button.setCursor(Qt.PointingHandCursor)
        self.create_button.clicked.connect(self.create_requested)
        head.addWidget(self.create_button)
        layout.addLayout(head)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        holder = QWidget()
        self._items = QVBoxLayout(holder)
        self._items.setContentsMargins(0, 0, 0, 0)
        self._items.setSpacing(2)
        self._items.addStretch()
        scroll.setWidget(holder)
        layout.addWidget(scroll, 1)

    def set_title(self, title: str) -> None:
        self.title.setText(title)
        self.create_button.setToolTip(i18n.t("profiles.create"))

    def set_profiles(
        self,
        profiles: List[Dict[str, Any]],
        active_id: Optional[int],
        selected_id: Optional[int],
        dirty_id: Optional[int] = None,
    ) -> None:
        while self._items.count() > 1:
            item = self._items.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        for index, profile in enumerate(profiles):
            profile_id = profile.get("id")
            row = _ProfileItem(
                profile.get("name") or "profile",
                profile_id == active_id,
                profile_id == selected_id,
                profile_id == dirty_id,
                self._menu(profile_id, profile_id == active_id, len(profiles) > 1),
            )
            row.clicked.connect(lambda pid=profile_id: self.selected.emit(pid))
            self._items.insertWidget(index, row)

    def _menu(self, profile_id: int, is_active: bool, can_delete: bool) -> QMenu:
        menu = QMenu(self)
        activate = menu.addAction(icons.icon("check_circle", theme.TEXT), i18n.t("profiles.activate"))
        activate.setEnabled(not is_active)
        activate.triggered.connect(lambda: self.activate_requested.emit(profile_id))
        menu.addAction(icons.icon("edit", theme.TEXT), i18n.t("profiles.rename")).triggered.connect(
            lambda: self.rename_requested.emit(profile_id)
        )
        menu.addAction(icons.icon("duplicate", theme.TEXT), i18n.t("profiles.duplicate")).triggered.connect(
            lambda: self.duplicate_requested.emit(profile_id)
        )
        menu.addSeparator()
        delete = menu.addAction(icons.icon("trash", theme.DANGER), i18n.t("profiles.delete"))
        delete.setEnabled(can_delete)
        if not can_delete:
            delete.setToolTip(i18n.t("profiles.delete_last"))
        delete.triggered.connect(lambda: self.delete_requested.emit(profile_id))
        return menu
