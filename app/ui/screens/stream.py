"""Two sections for the stream: the Twitch chat overlay with a live preview,
and the web panel (connecting a phone or tablet, the grid layout editor)."""
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QButtonGroup, QFrame, QHBoxLayout, QPushButton, QScrollArea, QStackedWidget, QVBoxLayout, QWidget

from app import features
from app.modules.seventv import seventv
from app.modules.twitch_chat import chat as twitch_chat
from app.ui import i18n
from app.ui.screens.base import Screen
from app.ui.screens.layout_editor import LayoutEditor
from app.ui.screens.remote_cards import ChatCard, PanelCard
from app.ui.state import AppState
from app.ui.widgets.chat_preview import ChatPreview
from app.ui.widgets.common import Card, muted


class ChatScreen(Screen):
    """Settings on the left, the overlay preview on the right."""

    def __init__(self, state: AppState):
        super().__init__(state)
        body = QHBoxLayout()
        body.setSpacing(16)
        self.chat_card = ChatCard(state)
        settings_scroll = QScrollArea()
        settings_scroll.setWidgetResizable(True)
        settings_scroll.setFrameShape(QFrame.NoFrame)
        settings_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        holder = QWidget()
        holder_layout = QVBoxLayout(holder)
        holder_layout.setContentsMargins(0, 0, 6, 0)
        holder_layout.addWidget(self.chat_card)
        self.trigger_card = None
        if features.STUDIO:  # chat triggers drive Studio inputs
            from app.ui.studio.trigger_card import TriggerCard

            self.trigger_card = TriggerCard(state)
            holder_layout.addWidget(self.trigger_card)
        holder_layout.addStretch()
        settings_scroll.setWidget(holder)
        self.settings_scroll = settings_scroll
        body.addWidget(settings_scroll)
        self.preview_card = Card()
        self.preview = ChatPreview()
        self.preview_note = muted("", "faint", wrap=True)
        self.preview_card.body.addWidget(self.preview, 1)
        self.preview_card.body.addWidget(self.preview_note)
        body.addWidget(self.preview_card, 1)
        self.root.addLayout(body, 1)

        self._preview_timer = QTimer(self)
        self._preview_timer.setInterval(500)  # fade-outs in the preview
        self._preview_timer.timeout.connect(self._update_preview)
        state.chat_changed.connect(self._update_preview)
        self.retranslate()

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self._preview_timer.start()
        self._update_preview()

    def hideEvent(self, event) -> None:
        super().hideEvent(event)
        self._preview_timer.stop()

    def _update_preview(self) -> None:
        if not self.isVisible():
            return
        settings = self.state.settings()
        if settings.get("chat-7tv", True):
            seventv.load(twitch_chat.room_id)  # global emotes for the preview even before the chat connects
        self.preview.set_state(settings, twitch_chat.snapshot(60))
        self.chat_card.show_7tv()
        self.preview_note.setText(i18n.t("stream.preview_sample") if self.preview.sample else i18n.t("stream.preview_live"))

    def retranslate(self) -> None:
        self.header.set_text(i18n.t("stream.chat_title"), i18n.t("stream.chat_subtitle"))
        self.preview_card.set_title(i18n.t("stream.preview"))
        self.chat_card.retranslate()
        if self.trigger_card is not None:
            self.trigger_card.retranslate()
        self._fit_settings()

    def _fit_settings(self) -> None:
        # Horizontal scrolling is off, so the column must be at least as wide as
        # its cards — otherwise their right edge is cut off (longer languages too).
        scroll = self.settings_scroll
        needed = scroll.widget().minimumSizeHint().width() + scroll.verticalScrollBar().sizeHint().width()
        scroll.setFixedWidth(max(420, needed))


_PANEL_TABS = ("stream.tab_layout", "stream.tab_connect")


class PanelScreen(Screen):
    """The grid editor and connecting devices, switched in the header."""

    def __init__(self, state: AppState):
        super().__init__(state)
        segmented = QFrame()
        segmented.setObjectName("segmented")
        segment_layout = QHBoxLayout(segmented)
        segment_layout.setContentsMargins(3, 3, 3, 3)
        segment_layout.setSpacing(2)
        self.tab_group = QButtonGroup(self)
        self.tab_buttons = []
        for index in range(len(_PANEL_TABS)):
            button = QPushButton()
            button.setObjectName("segment")
            button.setCheckable(True)
            button.setCursor(Qt.PointingHandCursor)
            button.clicked.connect(lambda _=False, i=index: self.show_tab(i))
            self.tab_group.addButton(button, index)
            segment_layout.addWidget(button)
            self.tab_buttons.append(button)
        self.header.actions.addWidget(segmented)

        self.stack = QStackedWidget()
        self.root.addWidget(self.stack, 1)
        self.editor = LayoutEditor(state)
        self.stack.addWidget(self.editor)

        connect_page = QScrollArea()
        connect_page.setWidgetResizable(True)
        connect_page.setFrameShape(QFrame.NoFrame)
        connect_holder = QWidget()
        connect_layout = QVBoxLayout(connect_holder)
        connect_layout.setContentsMargins(0, 0, 6, 0)
        connect_layout.setSpacing(16)
        self.panel_card = PanelCard(state)
        connect_layout.addWidget(self.panel_card)
        self.steps_card = Card()
        self.steps = muted("", "muted", wrap=True)
        self.steps_card.body.addWidget(self.steps)
        connect_layout.addWidget(self.steps_card)
        connect_layout.addStretch()
        connect_page.setWidget(connect_holder)
        self.stack.addWidget(connect_page)

        # Nothing to arrange before a device can connect: start there until access is on.
        self.show_tab(0 if state.settings().get("lan-access") else 1)
        self.retranslate()

    def show_tab(self, index: int) -> None:
        self.stack.setCurrentIndex(index)
        self.tab_buttons[index].setChecked(True)

    def retranslate(self) -> None:
        self.header.set_text(i18n.t("stream.panel_title"), i18n.t("stream.panel_subtitle"))
        for button, key in zip(self.tab_buttons, _PANEL_TABS):
            button.setText(i18n.t(key))
        self.steps_card.set_title(i18n.t("stream.steps_title"))
        self.steps.setText(i18n.t("stream.steps"))
        self.panel_card.retranslate()
        self.editor.retranslate()
