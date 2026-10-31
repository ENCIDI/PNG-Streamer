import PySide6
from PySide6.QtCore import QUrl, Qt, qVersion
from PySide6.QtGui import QDesktopServices, QFont, QPixmap
from PySide6.QtWidgets import QButtonGroup, QFrame, QGridLayout, QHBoxLayout, QLabel, QPushButton, QSystemTrayIcon, QVBoxLayout

from app import paths
from app.modules import autostart_manager as autostart, update_manager as um
from app.ui import i18n, icons, theme
from app.ui.screens.base import Screen
from app.ui.state import AppState
from app.ui.updater import Updater
from app.ui.widgets.common import Card, SwitchRow, muted
from app.version import __version__

_LANGUAGE_NAMES = {"ru": "Русский", "en": "English"}


def open_path(path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))


class SettingsScreen(Screen):
    def __init__(self, state: AppState, updater: Updater):
        super().__init__(state)
        self.updater = updater
        grid = QGridLayout()
        grid.setHorizontalSpacing(16)
        grid.setVerticalSpacing(16)

        # general
        self.general_card = Card()
        language_row = QHBoxLayout()
        self.language_label = QLabel()
        language_row.addWidget(self.language_label, 1)
        segmented = QFrame()
        segmented.setObjectName("segmented")
        segment_layout = QHBoxLayout(segmented)
        segment_layout.setContentsMargins(3, 3, 3, 3)
        segment_layout.setSpacing(2)
        self.language_group = QButtonGroup(self)
        for lang in i18n.LANGUAGES:
            button = QPushButton(_LANGUAGE_NAMES[lang])
            button.setObjectName("segment")
            button.setCheckable(True)
            button.setCursor(Qt.PointingHandCursor)
            button.setChecked(lang == i18n.get_language())
            button.clicked.connect(lambda _=False, code=lang: state.set_language(code))
            self.language_group.addButton(button)
            segment_layout.addWidget(button)
        language_row.addWidget(segmented)
        self.general_card.body.addLayout(language_row)

        self.tray_available = QSystemTrayIcon.isSystemTrayAvailable()
        self.tray_row = SwitchRow()
        self.tray_row.setEnabled(self.tray_available)
        self.tray_row.toggled.connect(lambda v: state.update_settings(minimize_to_tray_on_close=v))
        self.autostart_row = SwitchRow()
        self.autostart_row.setEnabled(autostart.is_supported())
        self.autostart_row.toggled.connect(self._on_autostart)
        self.minimized_row = SwitchRow()
        self.minimized_row.setEnabled(self.tray_available)
        self.minimized_row.toggled.connect(lambda v: state.update_settings(start_minimized=v))
        self.server_row = SwitchRow()
        self.server_row.toggled.connect(lambda v: state.update_settings(start_server_on_launch=v))
        for row in (self.tray_row, self.autostart_row, self.minimized_row, self.server_row):
            self.general_card.body.addWidget(row)
        self.general_card.body.addStretch()

        # updates
        self.updates_card = Card()
        self.updates_row = SwitchRow()
        self.updates_row.toggled.connect(lambda v: state.update_settings(check_updates=v))
        self.updates_card.body.addWidget(self.updates_row)
        status_row = QHBoxLayout()
        self.update_status = muted("", wrap=True)
        status_row.addWidget(self.update_status, 1)
        self.check_button = QPushButton()
        self.check_button.setCursor(Qt.PointingHandCursor)
        self.check_button.clicked.connect(lambda: updater.check(manual=True))
        status_row.addWidget(self.check_button)
        self.updates_card.body.addLayout(status_row)
        self.updates_card.body.addStretch()

        # data
        self.data_card = Card()
        self.data_hint = muted("", "faint", wrap=True)
        self.data_card.body.addWidget(self.data_hint)
        self.data_path = muted(str(paths.DATA_DIR), wrap=True)
        self.data_path.setFont(theme.mono_font(8.5))
        self.data_path.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.data_card.body.addWidget(self.data_path)
        data_buttons = QHBoxLayout()
        self.open_data = QPushButton()
        self.open_data.setIcon(icons.icon("folder", theme.TEXT))
        self.open_data.setCursor(Qt.PointingHandCursor)
        self.open_data.clicked.connect(lambda: open_path(paths.DATA_DIR))
        self.open_logs = QPushButton()
        self.open_logs.setCursor(Qt.PointingHandCursor)
        self.open_logs.clicked.connect(lambda: open_path(paths.LOGS_DIR))
        data_buttons.addWidget(self.open_data)
        data_buttons.addWidget(self.open_logs)
        data_buttons.addStretch()
        self.data_card.body.addLayout(data_buttons)
        self.data_card.body.addStretch()

        # about
        self.about_card = Card()
        brand = QHBoxLayout()
        brand.setSpacing(12)
        logo = QLabel()
        logo.setPixmap(QPixmap(str(paths.RESOURCES_DIR / "assets" / "icon.ico")).scaled(
            40, 40, Qt.KeepAspectRatio, Qt.SmoothTransformation
        ))
        brand.addWidget(logo)
        names = QVBoxLayout()
        names.setSpacing(0)
        title = QLabel("PNG Streamer")
        title.setFont(theme.font(12, QFont.DemiBold))
        self.version_label = muted()
        names.addWidget(title)
        names.addWidget(self.version_label)
        brand.addLayout(names, 1)
        self.about_card.body.addLayout(brand)
        self.licenses_label = muted("", "faint", wrap=True)
        self.about_card.body.addWidget(self.licenses_label)
        about_buttons = QHBoxLayout()
        github = QPushButton("GitHub")
        github.setCursor(Qt.PointingHandCursor)
        github.clicked.connect(
            lambda: QDesktopServices.openUrl(QUrl(f"https://github.com/{um.REPOSITORY}"))
        )
        self.licenses_button = QPushButton()
        self.licenses_button.setCursor(Qt.PointingHandCursor)
        self.licenses_button.clicked.connect(lambda: open_path(paths.RESOURCES_DIR.parent / "licenses"))
        about_buttons.addWidget(github)
        about_buttons.addWidget(self.licenses_button)
        about_buttons.addStretch()
        self.about_card.body.addLayout(about_buttons)
        self.about_card.body.addStretch()

        grid.addWidget(self.general_card, 0, 0)
        grid.addWidget(self.updates_card, 0, 1)
        grid.addWidget(self.data_card, 1, 0)
        grid.addWidget(self.about_card, 1, 1)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)
        self.root.addLayout(grid)
        self.root.addStretch()

        updater.status_changed.connect(self._refresh_updates)
        self.retranslate()

    def showEvent(self, event) -> None:
        self._load_values()
        super().showEvent(event)

    def _load_values(self) -> None:
        settings = self.state.settings()
        self.tray_row.setChecked(self.tray_available and bool(settings.get("minimize-to-tray-on-close", True)))
        self.autostart_row.setChecked(autostart.is_enabled())
        self.minimized_row.setChecked(bool(settings.get("start-minimized", False)))
        self.server_row.setChecked(bool(settings.get("start-server-on-launch", False)))
        self.updates_row.setChecked(bool(settings.get("check-updates", True)))
        for button, lang in zip(self.language_group.buttons(), i18n.LANGUAGES):
            button.setChecked(lang == i18n.get_language())

    def _on_autostart(self, enabled: bool) -> None:
        if not autostart.set_enabled(enabled):
            self.autostart_row.setChecked(autostart.is_enabled())

    def _refresh_updates(self) -> None:
        eligible = self.updater.eligible
        self.updates_row.setEnabled(eligible)
        self.check_button.setEnabled(eligible and not self.updater.checking)
        result = self.updater.last_result
        if not eligible:
            text = i18n.t("settings.update_source")
        elif self.updater.checking:
            text = i18n.t("settings.update_checking")
        elif result is None:
            text = ""
        elif result.error:
            text = i18n.t("settings.update_error")
        elif not result.is_release:
            text = i18n.t("settings.update_not_release", version=__version__)
        elif result.update:
            text = i18n.t("update.available", version=result.update.version)
        else:
            text = i18n.t("settings.update_none")
        self.update_status.setText(text)

    def retranslate(self) -> None:
        self.header.set_text(i18n.t("settings.title"), i18n.t("settings.subtitle"))
        self.general_card.set_title(i18n.t("settings.general"))
        self.language_label.setText(i18n.t("settings.language"))
        self.tray_row.set_text(
            i18n.t("settings.tray_close"), "" if self.tray_available else i18n.t("settings.tray_unavailable")
        )
        self.autostart_row.set_text(i18n.t("settings.autostart"))
        self.minimized_row.set_text(i18n.t("settings.start_minimized"))
        self.server_row.set_text(i18n.t("settings.start_server"))
        self.updates_card.set_title(i18n.t("settings.updates"))
        self.updates_row.set_text(i18n.t("settings.check_updates"))
        self.check_button.setText(i18n.t("settings.check_now"))
        self.data_card.set_title(i18n.t("settings.data"))
        self.data_hint.setText(i18n.t("settings.data_hint"))
        self.open_data.setText(" " + i18n.t("settings.open_data"))
        self.open_logs.setText(i18n.t("settings.open_logs"))
        self.about_card.set_title(i18n.t("settings.about"))
        self.version_label.setText(
            i18n.t("settings.version", version=__version__) + f"  ·  Qt {qVersion()} · PySide6 {PySide6.__version__}"
        )
        self.licenses_label.setText(i18n.t("settings.licenses", qt=qVersion()))
        self.licenses_button.setText(i18n.t("settings.open_licenses"))
        self._refresh_updates()
