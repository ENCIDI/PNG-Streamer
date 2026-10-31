from typing import Optional

from PySide6.QtCore import QObject, QPointF, Qt, Signal
from PySide6.QtGui import QAction, QActionGroup, QGuiApplication, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import QMenu, QSystemTrayIcon

from app import paths
from app.ui import i18n, theme
from app.ui.state import AppState
from app.ui.updater import Updater

_ICON_SIZE = 64


def _status_icon(base: QPixmap, dot: Optional[str]) -> QIcon:
    pm = QPixmap(_ICON_SIZE, _ICON_SIZE)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    p.setRenderHint(QPainter.SmoothPixmapTransform)
    p.drawPixmap(pm.rect(), base)
    if dot:
        center = QPointF(_ICON_SIZE * 0.78, _ICON_SIZE * 0.78)
        p.setPen(Qt.NoPen)
        p.setBrush(theme.color(theme.BG))
        p.drawEllipse(center, _ICON_SIZE * 0.2, _ICON_SIZE * 0.2)
        p.setBrush(theme.color(dot))
        p.drawEllipse(center, _ICON_SIZE * 0.14, _ICON_SIZE * 0.14)
    p.end()
    return QIcon(pm)


class Tray(QObject):
    open_requested = Signal()
    toggle_requested = Signal()
    quit_requested = Signal()
    install_requested = Signal()

    def __init__(self, state: AppState, updater: Updater):
        super().__init__()
        self.state = state
        self.updater = updater
        base = QPixmap(str(paths.RESOURCES_DIR / "assets" / "icon.ico"))
        self._icons = {
            "live": _status_icon(base, theme.ACCENT),
            "stopped": _status_icon(base, theme.MUTED),
            "error": _status_icon(base, theme.DANGER),
        }
        self.icon = QSystemTrayIcon(self._icons["stopped"])
        self.menu = QMenu()
        self.menu.aboutToShow.connect(self._rebuild_menu)
        self.icon.setContextMenu(self.menu)
        self.icon.activated.connect(self._on_activated)
        self._rebuild_menu()
        for signal in (state.server_changed, state.microphone_changed, state.profiles_changed, state.language_changed):
            signal.connect(self.refresh)
        updater.update_found.connect(lambda _: self.refresh())
        self.refresh()

    @staticmethod
    def available() -> bool:
        return QSystemTrayIcon.isSystemTrayAvailable()

    def show(self) -> None:
        self.icon.show()

    def hide(self) -> None:
        self.icon.hide()

    def show_hint(self) -> None:
        self.icon.showMessage(i18n.t("tray.hint_title"), i18n.t("tray.hint_text"), self.icon.icon(), 4000)

    def _status_text(self) -> str:
        if self.state.server_running():
            return i18n.t("tray.status_live", port=self.state.port())
        return i18n.t("tray.status_stopped")

    def refresh(self) -> None:
        if self.state.mic_error in ("failed", "unavailable"):
            key = "error"
        else:
            key = "live" if self.state.server_running() else "stopped"
        self.icon.setIcon(self._icons[key])
        sound = self.state.active_sound_profile() or {}
        image = self.state.active_image_profile() or {}
        profiles = " / ".join(filter(None, [image.get("name"), sound.get("name")]))
        self.icon.setToolTip("\n".join(filter(None, ["PNG Streamer", self._status_text(), profiles])))
        if self.menu.isVisible():
            self._rebuild_menu()

    def _rebuild_menu(self) -> None:
        menu = self.menu
        menu.clear()
        status = menu.addAction(self._status_text())
        status.setEnabled(False)
        menu.addSeparator()
        if self.state.server_running():
            menu.addAction(i18n.t("tray.stop")).triggered.connect(self.state.stop_server)
            menu.addAction(i18n.t("tray.copy_url")).triggered.connect(
                lambda: QGuiApplication.clipboard().setText(self.state.widget_url())
            )
        else:
            menu.addAction(i18n.t("tray.start")).triggered.connect(lambda: self.state.start_server())
        self._profile_menu(
            menu.addMenu(i18n.t("tray.sound_profile")),
            self.state.sound_profiles(),
            self.state.active_sound_profile_id(),
            self.state.set_active_sound_profile,
        )
        self._profile_menu(
            menu.addMenu(i18n.t("tray.image_profile")),
            self.state.image_profiles(),
            self.state.active_image_profile_id(),
            self.state.set_active_image_profile,
        )
        menu.addSeparator()
        if self.updater.update is not None:
            menu.addAction(i18n.t("tray.update", version=self.updater.update.version)).triggered.connect(
                self._install_update
            )
        menu.addAction(i18n.t("tray.open")).triggered.connect(self.open_requested)
        menu.addAction(i18n.t("tray.quit")).triggered.connect(self.quit_requested)

    def _profile_menu(self, submenu: QMenu, profiles, active_id, activate) -> None:
        group = QActionGroup(submenu)
        group.setExclusive(True)
        for profile in profiles:
            action = QAction(profile.get("name", "profile"), submenu, checkable=True)
            action.setChecked(profile.get("id") == active_id)
            action.triggered.connect(lambda _=False, pid=profile.get("id"): activate(pid))
            group.addAction(action)
            submenu.addAction(action)

    def _install_update(self) -> None:
        self.open_requested.emit()
        self.install_requested.emit()

    def _on_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason in (QSystemTrayIcon.Trigger, QSystemTrayIcon.DoubleClick):
            self.toggle_requested.emit()
