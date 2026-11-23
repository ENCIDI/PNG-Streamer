"""Settings cards: web control panel (LAN access, link + QR code) and Twitch chat."""
from typing import Optional

from PySide6.QtCore import QRectF, QSize, Qt
from PySide6.QtGui import QGuiApplication, QPainter
from PySide6.QtWidgets import QHBoxLayout, QLabel, QLineEdit, QPushButton, QVBoxLayout, QWidget

from app.modules import lan
from app.modules.twitch_chat import chat as twitch_chat
from app.ui import i18n, icons, theme
from app.ui.state import AppState
from app.ui.widgets import dialogs
from app.ui.widgets.common import Card, Combo, LabeledSlider, SwitchRow, muted, number_field


class QrCode(QWidget):
    def __init__(self, size: int = 168):
        super().__init__()
        self.setFixedSize(QSize(size, size))
        self._matrix = []

    def set_text(self, text: str) -> None:
        self._matrix = lan.qr_matrix(text) if text else []
        self.update()

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.fillRect(self.rect(), Qt.white)
        if not self._matrix:
            return
        count = len(self._matrix) + 8  # quiet zone of 4 modules on each side
        cell = self.width() / count
        p.setPen(Qt.NoPen)
        p.setBrush(Qt.black)
        for y, row in enumerate(self._matrix):
            for x, dark in enumerate(row):
                if dark:
                    p.drawRect(QRectF((x + 4) * cell, (y + 4) * cell, cell + 0.4, cell + 0.4))


class PanelCard(Card):
    def __init__(self, state: AppState):
        super().__init__()
        self.state = state
        self.hint = muted("", "faint", wrap=True)
        self.body.addWidget(self.hint)
        self.switch = SwitchRow()
        self.switch.toggled.connect(self._toggle)
        self.body.addWidget(self.switch)
        self.details = QWidget()
        details = QHBoxLayout(self.details)
        details.setContentsMargins(0, 4, 0, 0)
        details.setSpacing(16)
        self.qr = QrCode()
        details.addWidget(self.qr, 0, Qt.AlignTop)
        right = QVBoxLayout()
        right.setSpacing(8)
        self.scan = QLabel()
        self.scan.setWordWrap(True)
        right.addWidget(self.scan)
        self.address = Combo()
        self.address.currentIndexChanged.connect(lambda _: self._show_url())
        right.addWidget(self.address)
        self.url = QLineEdit()
        self.url.setReadOnly(True)
        self.url.setObjectName("url")
        self.url.setFont(theme.mono_font(8.5))
        right.addWidget(self.url)
        buttons = QHBoxLayout()
        self.copy = QPushButton()
        self.copy.setIcon(icons.icon("copy", theme.TEXT))
        self.copy.clicked.connect(lambda: (QGuiApplication.clipboard().setText(self.url.text()),
                                           state.notify.emit(i18n.t("panel_ui.copied"), "info")))
        self.reset = QPushButton()
        self.reset.setObjectName("danger")
        self.reset.clicked.connect(self._reset)
        buttons.addWidget(self.copy)
        buttons.addWidget(self.reset)
        buttons.addStretch()
        right.addLayout(buttons)
        self.server_note = muted("", "danger", wrap=True)
        right.addWidget(self.server_note)

        right.addStretch()
        details.addLayout(right, 1)
        self.body.addWidget(self.details)
        state.server_changed.connect(self.refresh)
        self.retranslate()

    def _toggle(self, enabled: bool) -> None:
        self.state.set_lan_access(enabled)
        self.refresh()

    def _reset(self) -> None:
        if dialogs.confirm(self.window(), i18n.t("panel_ui.reset_title"), i18n.t("panel_ui.reset_text"),
                           i18n.t("panel_ui.reset"), danger=True):
            lan.reset_token()
            self._show_url()

    def _show_url(self) -> None:
        address = self.address.currentData()
        url = lan.panel_url(address, self.state.port()) if address else ""
        self.url.setText(url)
        self.qr.set_text(url)

    def refresh(self) -> None:
        enabled = lan.enabled()
        self.switch.setChecked(enabled)
        self.details.setVisible(enabled)
        if not enabled:
            return
        addresses = lan.addresses()
        current = self.address.currentData()
        self.address.set_items([(a, a) for a in addresses], current if current in addresses else (addresses[0] if addresses else None))
        self.address.setVisible(len(addresses) > 1)
        if not addresses:
            self.url.setText("")
            self.qr.set_text("")
            self.scan.setText(i18n.t("panel_ui.no_network"))
        else:
            self.scan.setText(i18n.t("panel_ui.scan"))
            self._show_url()
        self.server_note.setText("" if self.state.server_running() else i18n.t("panel_ui.server_off"))
        self.server_note.setVisible(not self.state.server_running())

    def retranslate(self) -> None:
        self.set_title(i18n.t("panel_ui.title"))
        self.hint.setText(i18n.t("panel_ui.hint"))
        self.switch.set_text(i18n.t("panel_ui.enable"), i18n.t("panel_ui.enable_hint"))
        self.copy.setText(" " + i18n.t("panel_ui.copy"))
        self.reset.setText(i18n.t("panel_ui.reset"))

        self.refresh()


class ChatCard(Card):
    def __init__(self, state: AppState):
        super().__init__()
        self.state = state
        self.hint = muted("", "faint", wrap=True)
        self.body.addWidget(self.hint)
        row = QHBoxLayout()
        self.channel = QLineEdit()
        self.channel.setPlaceholderText("twitch.tv/…")
        self.channel.editingFinished.connect(self._save_channel)
        row.addWidget(self.channel, 1)
        self.status = QLabel()
        row.addWidget(self.status)
        self.body.addLayout(row)
        self.switch = SwitchRow()
        self.switch.toggled.connect(self._toggle)
        self.body.addWidget(self.switch)
        options = QHBoxLayout()
        options.setSpacing(10)
        self.max_label, self.fade_label, self.font_label = muted(), muted(), muted()
        self.max_field = number_field(1, 50)
        self.fade_field = number_field(0, 3600)
        self.font_field = number_field(10, 72)
        for label, field, key in ((self.max_label, self.max_field, "chat_max"), (self.fade_label, self.fade_field, "chat_fade_seconds"),
                                  (self.font_label, self.font_field, "chat_font_size")):
            column = QVBoxLayout()
            column.setSpacing(4)
            column.addWidget(label)
            column.addWidget(field)
            field.valueChanged.connect(lambda _v, f=field, k=key: state.update_settings(**{k: f.value()}) or self._changed())
            options.addLayout(column)
        self.body.addLayout(options)
        self.opacity = LabeledSlider(0, 100, lambda v: f"{v}%")
        self.opacity.valueChanged.connect(lambda v: state.update_settings(chat_bg_opacity=v) or self._changed())
        self.body.addWidget(self.opacity)
        self.seventv = SwitchRow()
        self.seventv.toggled.connect(lambda on: state.update_settings(chat_7tv=on) or self._changed())
        self.body.addWidget(self.seventv)
        self.commands = SwitchRow()
        self.commands.toggled.connect(lambda on: state.update_settings(chat_hide_commands=on) or self._changed())
        self.body.addWidget(self.commands)
        self.hidden_label = muted()
        self.body.addWidget(self.hidden_label)
        self.hidden = QLineEdit()
        self.hidden.editingFinished.connect(
            lambda: state.update_settings(chat_hidden_users=self.hidden.text().strip()) or self._changed())
        self.body.addWidget(self.hidden)
        url_row = QHBoxLayout()
        self.url = QLineEdit()
        self.url.setReadOnly(True)
        self.url.setObjectName("url")
        self.url.setFont(theme.mono_font(8.5))
        url_row.addWidget(self.url, 1)
        self.copy = QPushButton()
        self.copy.setIcon(icons.icon("copy", theme.TEXT))
        self.copy.clicked.connect(lambda: (QGuiApplication.clipboard().setText(self.url.text()),
                                           state.notify.emit(i18n.t("panel_ui.copied"), "info")))
        url_row.addWidget(self.copy)
        self.body.addLayout(url_row)
        self.obs_hint = muted("", "faint", wrap=True)
        self.body.addWidget(self.obs_hint)
        state.chat_changed.connect(self.refresh)
        state.server_changed.connect(self.refresh)
        self.retranslate()

    def show_7tv(self) -> None:
        from app.modules.seventv import seventv

        count = seventv.count()
        hint = i18n.t("chat_ui.7tv_count", count=count) if count else i18n.t("chat_ui.7tv_hint")
        if self.seventv.hint.text() != hint or self.seventv.label.text() != i18n.t("chat_ui.7tv"):
            self.seventv.set_text(i18n.t("chat_ui.7tv"), hint)

    def _changed(self) -> None:
        """The overlay reads its style when it loads; tell open overlays and the preview."""
        self.state.chat_changed.emit()

    def _save_channel(self) -> None:
        name = self.channel.text().strip().rstrip("/").split("/")[-1].lstrip("#@").lower()
        self.channel.setText(name)
        if name != self.state.settings().get("twitch-channel"):
            self.state.update_settings(twitch_channel=name)
            self.state.apply_chat()

    def _toggle(self, enabled: bool) -> None:
        self._save_channel()
        self.state.update_settings(chat_enabled=enabled)
        self.state.apply_chat()

    def refresh(self) -> None:
        settings = self.state.settings()
        if not self.channel.hasFocus():
            self.channel.setText(settings.get("twitch-channel", ""))
        self.switch.setChecked(bool(settings.get("chat-enabled")))
        for field, key, default in ((self.max_field, "chat-max", 12), (self.fade_field, "chat-fade-seconds", 45),
                                    (self.font_field, "chat-font-size", 20)):
            if not field.hasFocus():
                field.blockSignals(True)
                field.setValue(int(settings.get(key, default) or 0))
                field.blockSignals(False)
        self.opacity.setValue(int(settings.get("chat-bg-opacity", 72)))
        self.commands.setChecked(bool(settings.get("chat-hide-commands")))
        self.seventv.setChecked(bool(settings.get("chat-7tv", True)))
        self.show_7tv()
        if not self.hidden.hasFocus():
            self.hidden.setText(settings.get("chat-hidden-users", ""))
            self.hidden.setCursorPosition(0)  # show the start of the list, not its end
        self.url.setText(f"http://127.0.0.1:{self.state.port()}/chat")
        status = twitch_chat.status if settings.get("chat-enabled") else "off"
        color = {"connected": theme.ACCENT, "error": theme.DANGER, "connecting": theme.WARNING}.get(status, theme.FAINT)
        self.status.setText("● " + i18n.t(f"chat_ui.status_{status}"))
        self.status.setStyleSheet(f"color: {color};")
        self.status.setToolTip(twitch_chat.error)

    def retranslate(self) -> None:
        self.set_title(i18n.t("chat_ui.title"))
        self.hint.setText(i18n.t("chat_ui.hint"))
        self.switch.set_text(i18n.t("chat_ui.enable"))
        self.max_label.setText(i18n.t("chat_ui.max"))
        self.fade_label.setText(i18n.t("chat_ui.fade"))
        self.font_label.setText(i18n.t("chat_ui.font"))
        self.opacity.set_label(i18n.t("chat_ui.opacity"))
        self.commands.set_text(i18n.t("chat_ui.hide_commands"), i18n.t("chat_ui.hide_commands_hint"))
        self.show_7tv()
        self.hidden_label.setText(i18n.t("chat_ui.hidden_users"))
        self.hidden.setPlaceholderText("nightbot, streamelements")
        self.copy.setText(" " + i18n.t("panel_ui.copy"))
        self.obs_hint.setText(i18n.t("chat_ui.obs_hint"))
        self.refresh()
