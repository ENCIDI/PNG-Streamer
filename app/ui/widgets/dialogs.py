from typing import List, Optional, Tuple

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QDialog, QHBoxLayout, QLabel, QLineEdit, QPushButton, QVBoxLayout, QWidget

from app.ui import i18n, theme


class _Dialog(QDialog):
    def __init__(self, parent: Optional[QWidget], title: str, text: str = ""):
        super().__init__(parent)
        self.setWindowTitle("PNG Streamer")
        self.setModal(True)
        self.setMinimumWidth(400)
        self.result_key: Optional[str] = None
        self.layout_ = QVBoxLayout(self)
        self.layout_.setContentsMargins(24, 22, 24, 20)
        self.layout_.setSpacing(12)
        heading = QLabel(title)
        heading.setFont(theme.font(12.5, QFont.DemiBold))
        heading.setWordWrap(True)
        self.layout_.addWidget(heading)
        if text:
            body = QLabel(text)
            body.setObjectName("muted")
            body.setWordWrap(True)
            self.layout_.addWidget(body)
        self.buttons = QHBoxLayout()
        self.buttons.setSpacing(8)
        self.buttons.addStretch()

    def add_buttons(self, buttons: List[Tuple[str, str, str]]) -> None:
        """buttons: (key, text, object_name); the last one is the default."""
        self.layout_.addSpacing(8)
        for key, text, object_name in buttons:
            button = QPushButton(text)
            button.setObjectName(object_name)
            button.setCursor(Qt.PointingHandCursor)
            button.clicked.connect(lambda _=False, k=key: self._finish(k))
            self.buttons.addWidget(button)
            button.setDefault(True)
        self.layout_.addLayout(self.buttons)

    def _finish(self, key: str) -> None:
        self.result_key = key
        self.accept() if key != "cancel" else self.reject()


def confirm(parent: Optional[QWidget], title: str, text: str, action: str, danger: bool = False) -> bool:
    dialog = _Dialog(parent, title, text)
    dialog.add_buttons([("cancel", i18n.t("common.cancel"), ""), ("ok", action, "danger" if danger else "primary")])
    dialog.exec()
    return dialog.result_key == "ok"


def ask_save(parent: Optional[QWidget], name: str) -> str:
    """Returns "save", "discard" or "cancel"."""
    dialog = _Dialog(parent, i18n.t("common.discard_title"), i18n.t("common.discard_text", name=name))
    dialog.add_buttons(
        [
            ("discard", i18n.t("common.discard"), "danger"),
            ("cancel", i18n.t("common.cancel"), ""),
            ("save", i18n.t("common.save"), "primary"),
        ]
    )
    dialog.exec()
    return dialog.result_key or "cancel"


def prompt_text(parent: Optional[QWidget], title: str, value: str) -> Optional[str]:
    dialog = _Dialog(parent, title)
    field = QLineEdit(value)
    field.selectAll()
    field.returnPressed.connect(lambda: dialog._finish("ok"))
    dialog.layout_.addWidget(field)
    dialog.add_buttons([("cancel", i18n.t("common.cancel"), ""), ("ok", i18n.t("common.save"), "primary")])
    field.setFocus()
    dialog.exec()
    if dialog.result_key != "ok":
        return None
    text = field.text().strip()
    return text or None
