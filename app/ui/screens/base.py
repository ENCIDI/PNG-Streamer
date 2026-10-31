import copy
from typing import Any, Dict, List, Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QScrollArea, QVBoxLayout, QWidget

from app.ui import i18n, icons, theme
from app.ui.state import AppState
from app.ui.widgets import dialogs
from app.ui.widgets.common import Card, PageHeader
from app.ui.widgets.profile_list import ProfileList


class Screen(QWidget):
    def __init__(self, state: AppState):
        super().__init__()
        self.state = state
        self.root = QVBoxLayout(self)
        self.root.setContentsMargins(32, 28, 32, 28)
        self.root.setSpacing(22)
        self.header = PageHeader()
        self.root.addWidget(self.header)
        state.language_changed.connect(self.retranslate)

    def retranslate(self) -> None:
        pass

    def can_leave(self) -> bool:
        return True

    def tick(self, dt: float) -> None:
        pass


class ProfileScreen(Screen):
    """Profile list on the left, an editor on the right, explicit save with
    unsaved-changes tracking. Subclasses implement the storage and editor hooks."""

    def __init__(self, state: AppState):
        super().__init__(state)
        self._selected_id: Optional[int] = None
        self._baseline: Optional[Dict[str, Any]] = None
        self._loading = False
        self._shown_dirty = False

        self.dirty_label = QLabel()
        self.dirty_label.setStyleSheet(f"color: {theme.WARNING};")
        self.revert_button = QPushButton()
        self.revert_button.setCursor(Qt.PointingHandCursor)
        self.revert_button.clicked.connect(self.revert)
        self.save_button = QPushButton()
        self.save_button.setObjectName("primary")
        self.save_button.setIcon(icons.icon("check", theme.ACCENT_INK))
        self.save_button.setCursor(Qt.PointingHandCursor)
        self.save_button.clicked.connect(self.save)
        self.header.actions.addWidget(self.dirty_label)
        self.header.actions.addWidget(self.revert_button)
        self.header.actions.addWidget(self.save_button)

        body = QHBoxLayout()
        body.setSpacing(16)
        list_card = Card(margins=16)
        self.profile_list = ProfileList()
        list_card.body.addWidget(self.profile_list, 1)
        body.addWidget(list_card)

        self.editor_scroll = QScrollArea()
        self.editor_scroll.setWidgetResizable(True)
        self.editor_scroll.setFrameShape(QFrame.NoFrame)
        self.editor = QWidget()
        self.editor_layout = QVBoxLayout(self.editor)
        self.editor_layout.setContentsMargins(0, 0, 6, 0)
        self.editor_layout.setSpacing(16)
        self.editor_scroll.setWidget(self.editor)
        body.addWidget(self.editor_scroll, 1)
        self.root.addLayout(body, 1)

        self.profile_list.selected.connect(self._on_select)
        self.profile_list.create_requested.connect(self._on_create)
        self.profile_list.activate_requested.connect(self._on_activate)
        self.profile_list.rename_requested.connect(self._on_rename)
        self.profile_list.duplicate_requested.connect(self._on_duplicate)
        self.profile_list.delete_requested.connect(self._on_delete)
        state.profiles_changed.connect(self._refresh_list)

    # --- hooks ---------------------------------------------------------------
    def list_profiles(self) -> List[Dict[str, Any]]:
        raise NotImplementedError

    def store_profile(self, profile: Dict[str, Any]) -> None:
        raise NotImplementedError

    def remove_profile(self, profile_id: int) -> None:
        raise NotImplementedError

    def active_id(self) -> Optional[int]:
        raise NotImplementedError

    def set_active(self, profile_id: int) -> None:
        raise NotImplementedError

    def default_profile_data(self) -> Dict[str, Any]:
        raise NotImplementedError

    def load_editor(self, profile: Dict[str, Any]) -> None:
        raise NotImplementedError

    def editor_data(self) -> Dict[str, Any]:
        """Profile fields (without id/name) as currently shown in the editor."""
        raise NotImplementedError

    def on_saved(self, profile: Dict[str, Any]) -> None:
        pass

    # --- helpers -------------------------------------------------------------
    def profile_by_id(self, profile_id: Optional[int]) -> Optional[Dict[str, Any]]:
        return next((p for p in self.list_profiles() if p.get("id") == profile_id), None)

    def selected_profile(self) -> Optional[Dict[str, Any]]:
        return self.profile_by_id(self._selected_id)

    def is_dirty(self) -> bool:
        return self._baseline is not None and self.editor_data() != self._baseline

    def mark_changed(self) -> None:
        if self._loading:
            return
        self._update_save_bar()

    def _update_save_bar(self) -> None:
        dirty = self.is_dirty()
        self.dirty_label.setVisible(dirty)
        self.revert_button.setVisible(dirty)
        self.save_button.setEnabled(dirty)
        if dirty != self._shown_dirty:
            self._shown_dirty = dirty
            self._refresh_list()

    def _refresh_list(self) -> None:
        profiles = self.list_profiles()
        ids = [p.get("id") for p in profiles]
        if self._selected_id not in ids and ids:
            fallback = self.active_id() if self.active_id() in ids else (ids[0] if ids else None)
            self._select(fallback)
            return
        self.profile_list.set_profiles(
            profiles, self.active_id(), self._selected_id, self._selected_id if self.is_dirty() else None
        )

    def _select(self, profile_id: Optional[int]) -> None:
        self._selected_id = profile_id
        profile = self.selected_profile()
        self._loading = True
        if profile is not None:
            self.load_editor(copy.deepcopy(profile))
        self._loading = False
        self.editor.setEnabled(profile is not None)
        self._baseline = self.editor_data() if profile is not None else None
        self._update_save_bar()
        self._refresh_list()

    def reload(self) -> None:
        if self._selected_id is None:
            active = self.active_id()
            self._selected_id = active if self.profile_by_id(active) else None
        self._select(self._selected_id)

    def can_leave(self) -> bool:
        if not self.is_dirty():
            return True
        profile = self.selected_profile() or {}
        choice = dialogs.ask_save(self.window(), profile.get("name", ""))
        if choice == "save":
            self.save()
            return True
        if choice == "discard":
            self.revert()
            return True
        return False

    # --- actions -------------------------------------------------------------
    def save(self) -> None:
        profile = self.selected_profile()
        if profile is None:
            return
        profile.update(self.editor_data())
        self.store_profile(profile)
        self._baseline = self.editor_data()
        self.on_saved(profile)
        self._update_save_bar()
        self.state.profiles_changed.emit()
        self.state.notify.emit(i18n.t("notify.saved", name=profile.get("name")), "info")

    def revert(self) -> None:
        self._select(self._selected_id)

    def _next_id(self) -> int:
        return max((int(p.get("id", 0)) for p in self.list_profiles()), default=0) + 1

    def _on_select(self, profile_id: int) -> None:
        if profile_id == self._selected_id or not self.can_leave():
            return
        self._select(profile_id)

    def _on_create(self) -> None:
        if not self.can_leave():
            return
        profile = {"id": self._next_id(), "name": i18n.t("profiles.new_name"), **self.default_profile_data()}
        self.store_profile(profile)
        self.state.notify.emit(i18n.t("notify.created", name=profile["name"]), "info")
        self._select(profile["id"])
        self.state.profiles_changed.emit()

    def _on_activate(self, profile_id: int) -> None:
        self.set_active(profile_id)
        profile = self.profile_by_id(profile_id) or {}
        self.state.notify.emit(i18n.t("notify.activated", name=profile.get("name")), "info")

    def _on_rename(self, profile_id: int) -> None:
        profile = self.profile_by_id(profile_id)
        if profile is None:
            return
        name = dialogs.prompt_text(self.window(), i18n.t("profiles.rename_title"), profile.get("name", ""))
        if not name or name == profile.get("name"):
            return
        profile["name"] = name
        self.store_profile(profile)
        self.state.profiles_changed.emit()

    def _on_duplicate(self, profile_id: int) -> None:
        if not self.can_leave():
            return
        source = self.profile_by_id(profile_id)
        if source is None:
            return
        copy_profile = copy.deepcopy(source)
        copy_profile["id"] = self._next_id()
        copy_profile["name"] = i18n.t("profiles.copy_name", name=source.get("name", ""))
        self.store_profile(copy_profile)
        self.state.notify.emit(i18n.t("notify.created", name=copy_profile["name"]), "info")
        self._select(copy_profile["id"])
        self.state.profiles_changed.emit()

    def _on_delete(self, profile_id: int) -> None:
        profiles = self.list_profiles()
        profile = self.profile_by_id(profile_id)
        if profile is None or len(profiles) <= 1:
            return
        if not dialogs.confirm(
            self.window(),
            i18n.t("profiles.delete_title"),
            i18n.t("profiles.delete_text", name=profile.get("name", "")),
            i18n.t("common.delete"),
            danger=True,
        ):
            return
        was_active = self.active_id() == profile_id
        self.remove_profile(profile_id)
        remaining = self.list_profiles()
        if was_active and remaining:
            self.set_active(remaining[0].get("id"))
        if self._selected_id == profile_id:
            self._baseline = None
            self._selected_id = None
        self.state.notify.emit(i18n.t("notify.deleted", name=profile.get("name")), "info")
        self.reload()
        self.state.profiles_changed.emit()

    def retranslate_base(self) -> None:
        self.dirty_label.setText("● " + i18n.t("common.unsaved"))
        self.revert_button.setText(i18n.t("common.revert"))
        self.save_button.setText(" " + i18n.t("common.save"))
        self._refresh_list()
