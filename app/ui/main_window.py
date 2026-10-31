from typing import List, Optional

from PySide6.QtCore import QByteArray, QSize, QTimer, QUrl, Qt, Signal
from PySide6.QtGui import QDesktopServices, QFont, QIcon, QPixmap
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QProgressBar,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from app import paths
from app.ui import i18n, icons, theme
from app.ui.screens.base import Screen
from app.ui.screens.images import ImagesScreen
from app.ui.screens.launch import LaunchScreen
from app.ui.screens.settings import SettingsScreen
from app.ui.screens.sound import SoundScreen
from app.ui.state import AppState
from app.ui.updater import Updater
from app.ui.widgets.toast import Toast
from app.version import __version__

_FRAME_MS = 16
_NAV = (("launch", "nav.launch"), ("mic", "nav.sound"), ("image", "nav.images"), ("settings", "nav.settings"))


def app_icon() -> QIcon:
    return QIcon(str(paths.RESOURCES_DIR / "assets" / "icon.ico"))


class UpdateBanner(QFrame):
    def __init__(self, updater: Updater):
        super().__init__()
        self.updater = updater
        self.setObjectName("banner")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 10, 10, 10)
        layout.setSpacing(10)
        self.icon = QLabel()
        self.icon.setPixmap(icons.pixmap("download", theme.ACCENT, 18))
        self.text = QLabel()
        self.text.setFont(theme.font(theme.BASE_POINT_SIZE, QFont.DemiBold))
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setTextVisible(False)
        self.progress.setFixedWidth(160)
        self.notes = QPushButton()
        self.notes.setObjectName("link")
        self.notes.setCursor(Qt.PointingHandCursor)
        self.notes.clicked.connect(self._open_notes)
        self.skip = QPushButton()
        self.skip.setObjectName("flat")
        self.skip.setCursor(Qt.PointingHandCursor)
        self.skip.clicked.connect(updater.skip)
        self.later = QPushButton()
        self.later.setObjectName("flat")
        self.later.setCursor(Qt.PointingHandCursor)
        self.later.clicked.connect(self.hide)
        self.install = QPushButton()
        self.install.setObjectName("primary")
        self.install.setCursor(Qt.PointingHandCursor)
        self.install.clicked.connect(self.start_install)
        layout.addWidget(self.icon)
        layout.addWidget(self.text)
        layout.addWidget(self.progress)
        layout.addSpacing(6)
        layout.addWidget(self.notes)
        layout.addStretch()
        layout.addWidget(self.skip)
        layout.addWidget(self.later)
        layout.addWidget(self.install)
        updater.update_found.connect(self._on_update)
        updater.progress.connect(self._on_progress)
        updater.failed.connect(self._on_failed)
        self.hide()

    def _on_update(self, info) -> None:
        self.setVisible(info is not None)
        self._set_downloading(False)
        self.retranslate()

    def start_install(self) -> None:
        if self.updater.update is None or self.updater.downloading:
            return
        self.show()
        self._set_downloading(True)
        self._on_progress(0)
        self.updater.install()

    def _set_downloading(self, downloading: bool) -> None:
        self.progress.setVisible(downloading)
        for widget in (self.notes, self.skip, self.later, self.install):
            widget.setVisible(not downloading)

    def _on_progress(self, percent: int) -> None:
        self.progress.setValue(percent)
        key = "update.installing" if percent >= 100 else "update.downloading"
        self.text.setText(i18n.t(key, percent=percent))

    def _on_failed(self, error: str) -> None:
        self._set_downloading(False)
        self.text.setText(i18n.t("update.failed", error=error))

    def _open_notes(self) -> None:
        if self.updater.update and self.updater.update.page_url:
            QDesktopServices.openUrl(QUrl(self.updater.update.page_url))

    def retranslate(self) -> None:
        if self.updater.update and not self.updater.downloading:
            self.text.setText(i18n.t("update.available", version=self.updater.update.version))
        self.notes.setText(i18n.t("update.notes"))
        self.skip.setText(i18n.t("update.skip"))
        self.later.setText(i18n.t("update.later"))
        self.install.setText(i18n.t("update.install"))


class MainWindow(QMainWindow):
    close_requested = Signal()

    def __init__(self, state: AppState, updater: Updater):
        super().__init__()
        self.state = state
        self.updater = updater
        self.setWindowTitle("PNG Streamer")
        self.setWindowIcon(app_icon())
        self.setMinimumSize(1000, 680)
        self.resize(1180, 760)
        self.allow_close = False

        root = QWidget()
        root.setObjectName("root")
        layout = QHBoxLayout(root)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self._build_sidebar())

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)
        self.banner = UpdateBanner(updater)
        banner_holder = QHBoxLayout()
        banner_holder.setContentsMargins(32, 18, 32, 0)
        banner_holder.addWidget(self.banner)
        content_layout.addLayout(banner_holder)
        self.pages = QStackedWidget()
        self.screens: List[Screen] = [
            LaunchScreen(state),
            SoundScreen(state),
            ImagesScreen(state),
            SettingsScreen(state, updater),
        ]
        for screen in self.screens:
            self.pages.addWidget(screen)
        content_layout.addWidget(self.pages, 1)
        layout.addWidget(content, 1)
        self.setCentralWidget(root)

        self.toast = Toast(root)
        state.notify.connect(self.toast.show_message)
        state.language_changed.connect(self.retranslate)

        self._frame_timer = QTimer(self)
        self._frame_timer.timeout.connect(self._tick)
        self._frame_timer.start(_FRAME_MS)

        self._restore_geometry()
        self.retranslate()

    def _build_sidebar(self) -> QFrame:
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(208)
        side = QVBoxLayout(sidebar)
        side.setContentsMargins(16, 20, 16, 16)
        side.setSpacing(4)
        brand = QHBoxLayout()
        brand.setSpacing(10)
        logo = QLabel()
        logo_pm = QPixmap(str(paths.RESOURCES_DIR / "assets" / "icon.ico"))
        logo.setPixmap(logo_pm.scaled(28, 28, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        brand.addWidget(logo)
        name = QLabel("PNG Streamer")
        name.setFont(theme.font(10.5, QFont.DemiBold))
        brand.addWidget(name)
        brand.addStretch()
        side.addLayout(brand)
        side.addSpacing(22)

        self.nav_buttons: List[QPushButton] = []
        for index, (icon_name, _) in enumerate(_NAV):
            button = QPushButton()
            button.setObjectName("nav")
            button.setCheckable(True)
            button.setIcon(icons.icon(icon_name, theme.MUTED, theme.ACCENT))
            button.setIconSize(QSize(20, 20))
            button.setCursor(Qt.PointingHandCursor)
            button.clicked.connect(lambda _=False, i=index: self.show_page(i))
            side.addWidget(button)
            self.nav_buttons.append(button)
        self.nav_buttons[0].setChecked(True)
        side.addStretch()
        version = QLabel(f"v{__version__}")
        version.setObjectName("faint")
        side.addWidget(version)
        return sidebar

    def current_screen(self) -> Screen:
        return self.screens[self.pages.currentIndex()]

    def show_page(self, index: int) -> None:
        if index != self.pages.currentIndex() and not self.current_screen().can_leave():
            index = self.pages.currentIndex()
        self.pages.setCurrentIndex(index)
        for i, button in enumerate(self.nav_buttons):
            button.setChecked(i == index)

    def _tick(self) -> None:
        if self.isVisible() and not self.isMinimized():
            self.current_screen().tick(_FRAME_MS / 1000)

    def retranslate(self) -> None:
        for button, (_, key) in zip(self.nav_buttons, _NAV):
            button.setText("  " + i18n.t(key))
        self.banner.retranslate()

    def bring_to_front(self) -> None:
        self.show()
        self.setWindowState((self.windowState() & ~Qt.WindowMinimized) | Qt.WindowActive)
        self.raise_()
        self.activateWindow()

    def confirm_quit(self) -> bool:
        return all(screen.can_leave() for screen in self.screens) if self.isVisible() else True

    def _restore_geometry(self) -> None:
        saved = self.state.settings().get("window-geometry") or ""
        if saved:
            self.restoreGeometry(QByteArray.fromBase64(saved.encode("ascii")))

    def save_geometry(self) -> None:
        self.state.update_settings(window_geometry=bytes(self.saveGeometry().toBase64()).decode("ascii"))

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self.toast.reposition()

    def closeEvent(self, event) -> None:
        self.save_geometry()
        if self.allow_close:
            event.accept()
            return
        event.ignore()
        self.close_requested.emit()
