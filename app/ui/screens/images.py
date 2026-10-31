import random
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from PySide6.QtCore import QUrl, Qt, Signal
from PySide6.QtGui import QDesktopServices, QFont
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
)

from app import paths
from app.modules import logic_manager as lm, storage_manager as sm
from app.ui import i18n, icons, pixmaps, theme
from app.ui.screens.base import ProfileScreen
from app.ui.state import AppState
from app.ui.widgets.common import Card, LabeledSlider, clear_layout, muted, number_field
from app.ui.widgets.image_picker import ImagePicker
from app.ui.widgets.meter import LevelMeter
from app.ui.widgets.stage import AvatarStage


class _FrameRow(QFrame):
    changed = Signal()
    remove_requested = Signal(object)

    def __init__(self, on_import):
        super().__init__()
        self.setObjectName("subcard")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 12, 10, 12)
        layout.setSpacing(14)
        self.index_label = QLabel()
        self.index_label.setFont(theme.font(14, QFont.DemiBold))
        self.index_label.setObjectName("faint")
        self.index_label.setFixedWidth(22)
        layout.addWidget(self.index_label, 0, Qt.AlignTop)

        self.image_caption = muted("", "faint")
        self.image = ImagePicker(on_import)
        self.blink_caption = muted("", "faint")
        self.blink = ImagePicker(on_import, allow_none=True)
        for caption, picker in ((self.image_caption, self.image), (self.blink_caption, self.blink)):
            column = QVBoxLayout()
            column.setSpacing(6)
            caption.setFont(theme.font(8.5))
            column.addWidget(caption)
            column.addWidget(picker)
            column.addStretch()
            layout.addLayout(column)

        sliders = QVBoxLayout()
        sliders.setSpacing(10)
        self.threshold = LabeledSlider(0, 100)
        self.shake = LabeledSlider(0, 100)
        sliders.addWidget(self.threshold)
        sliders.addWidget(self.shake)
        sliders.addStretch()
        layout.addLayout(sliders, 1)

        self.remove_button = QPushButton()
        self.remove_button.setObjectName("flat")
        self.remove_button.setIcon(icons.icon("trash", theme.MUTED))
        self.remove_button.setCursor(Qt.PointingHandCursor)
        self.remove_button.clicked.connect(lambda: self.remove_requested.emit(self))
        layout.addWidget(self.remove_button, 0, Qt.AlignTop)

        self.image.changed.connect(self.changed)
        self.blink.changed.connect(self.changed)
        self.threshold.valueChanged.connect(self.changed)
        self.shake.valueChanged.connect(self.changed)
        self.retranslate()

    def retranslate(self) -> None:
        self.image_caption.setText(i18n.t("images.image"))
        self.blink_caption.setText(i18n.t("images.blink_image"))
        self.threshold.set_label(i18n.t("images.threshold"))
        self.shake.set_label(i18n.t("images.shake"))
        self.remove_button.setToolTip(i18n.t("images.remove_frame"))
        self.image.retranslate()
        self.blink.retranslate()


class ImagesScreen(ProfileScreen):
    def __init__(self, state: AppState):
        super().__init__(state)
        self._rows: List[_FrameRow] = []
        self._next_blink = 0.0
        self._blink_until = 0.0
        self.setAcceptDrops(True)

        # preview
        self.preview_card = Card()
        preview = QHBoxLayout()
        preview.setSpacing(18)
        self.stage = AvatarStage(minimum=220)
        self.stage.setFixedSize(220, 220)
        preview.addWidget(self.stage)
        right = QVBoxLayout()
        right.setSpacing(10)
        right.addStretch()
        self.meter = LevelMeter(segments=36)
        right.addWidget(self.meter)
        self.frames_hint = muted("", "faint", wrap=True)
        right.addWidget(self.frames_hint)
        right.addStretch()
        preview.addLayout(right, 1)
        self.preview_card.body.addLayout(preview)
        self.editor_layout.addWidget(self.preview_card)

        # frames
        self.frames_card = Card()
        self.import_button = QPushButton()
        self.import_button.setIcon(icons.icon("upload", theme.TEXT))
        self.import_button.setCursor(Qt.PointingHandCursor)
        self.import_button.clicked.connect(self.import_dialog)
        self.folder_button = QPushButton()
        self.folder_button.setObjectName("flat")
        self.folder_button.setIcon(icons.icon("folder", theme.MUTED))
        self.folder_button.setCursor(Qt.PointingHandCursor)
        self.folder_button.clicked.connect(
            lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(str(paths.IMAGES_DIR)))
        )
        self.frames_card.head.addWidget(self.folder_button)
        self.frames_card.head.addWidget(self.import_button)
        self.rows_layout = QVBoxLayout()
        self.rows_layout.setSpacing(8)
        self.frames_card.body.addLayout(self.rows_layout)
        self.empty_label = muted("", "faint")
        self.empty_label.setAlignment(Qt.AlignCenter)
        self.frames_card.body.addWidget(self.empty_label)
        self.add_button = QPushButton()
        self.add_button.setIcon(icons.icon("plus", theme.TEXT))
        self.add_button.setCursor(Qt.PointingHandCursor)
        self.add_button.clicked.connect(self._add_frame)
        self.frames_card.body.addWidget(self.add_button, 0, Qt.AlignLeft)
        self.drop_hint = muted("", "faint")
        self.frames_card.body.addWidget(self.drop_hint)
        self.editor_layout.addWidget(self.frames_card)

        # blink
        self.blink_card = Card()
        self.blink_hint = muted("", "faint", wrap=True)
        self.blink_card.body.addWidget(self.blink_hint)
        blink_grid = QGridLayout()
        blink_grid.setHorizontalSpacing(12)
        blink_grid.setVerticalSpacing(6)
        self.blink_labels = [muted(), muted(), muted()]
        self.blink_min, self.blink_max, self.blink_duration = (self._ms_field() for _ in range(3))
        for column, (label, field) in enumerate(
            zip(self.blink_labels, (self.blink_min, self.blink_max, self.blink_duration))
        ):
            blink_grid.addWidget(label, 0, column)
            blink_grid.addWidget(field, 1, column)
            field.valueChanged.connect(self._changed)
        self.blink_card.body.addLayout(blink_grid)
        self.editor_layout.addWidget(self.blink_card)
        self.editor_layout.addStretch()

        state.volume_changed.connect(self._on_volume)
        state.images_changed.connect(self._refresh_pickers)
        self.retranslate()
        self.reload()

    @staticmethod
    def _ms_field() -> QSpinBox:
        return number_field(0, 60000, 50)

    # --- ProfileScreen hooks -------------------------------------------------
    def list_profiles(self) -> List[Dict[str, Any]]:
        return sm.list_profiles()

    def store_profile(self, profile: Dict[str, Any]) -> None:
        sm.update_profile(profile)

    def remove_profile(self, profile_id: int) -> None:
        sm.delete_profile(profile_id)

    def active_id(self) -> Optional[int]:
        return self.state.active_image_profile_id()

    def set_active(self, profile_id: int) -> None:
        self.state.set_active_image_profile(profile_id)

    def default_profile_data(self) -> Dict[str, Any]:
        images = lm.list_available_images()
        first = images[0] if images else ""
        return {
            "images": [{"id": 0, "path-to-image": first, "volume-level": 0, "shake-level": 0}] if first else [],
            "blink": dict(sm.IMAGE_PROFILE_TEMPLATE["blink"]),
            "blink-images": [],
        }

    def load_editor(self, profile: Dict[str, Any]) -> None:
        for row in self._rows:
            row.deleteLater()
        self._rows = []
        clear_layout(self.rows_layout)
        blink_by_id = {
            item.get("id"): item.get("path-to-image", "")
            for item in profile.get("blink-images", [])
            if isinstance(item, dict)
        }
        for frame in lm.sorted_frames(profile):
            row = self._create_row()
            row.image.set_value(frame.get("path-to-image", ""))
            row.blink.set_value(blink_by_id.get(frame.get("id"), ""))
            row.threshold.setValue(frame.get("volume-level", 0))
            row.shake.setValue(frame.get("shake-level", 0))
        min_ms, max_ms, duration_ms = lm.blink_settings(profile)
        self.blink_min.setValue(min_ms)
        self.blink_max.setValue(max_ms)
        self.blink_duration.setValue(duration_ms)
        self._renumber()

    def editor_data(self) -> Dict[str, Any]:
        images, blink_images = [], []
        for index, row in enumerate(self._rows):
            if not row.image.value():
                continue
            images.append(
                {
                    "id": index,
                    "path-to-image": row.image.value(),
                    "volume-level": row.threshold.value(),
                    "shake-level": row.shake.value(),
                }
            )
            if row.blink.value():
                blink_images.append({"id": index, "path-to-image": row.blink.value()})
        return {
            "images": images,
            "blink-images": blink_images,
            "blink": {
                "interval-min-ms": self.blink_min.value(),
                "interval-max-ms": self.blink_max.value(),
                "duration-ms": self.blink_duration.value(),
            },
        }

    # --- frames --------------------------------------------------------------
    def _create_row(self) -> _FrameRow:
        row = _FrameRow(self.import_dialog)
        row.changed.connect(self._changed)
        row.remove_requested.connect(self._remove_frame)
        self._rows.append(row)
        self.rows_layout.addWidget(row)
        return row

    def _add_frame(self) -> None:
        last = self._rows[-1] if self._rows else None
        row = self._create_row()
        if last is not None:
            row.image.set_value(last.image.value())
            row.blink.set_value(last.blink.value())
            row.threshold.setValue(min(100, last.threshold.value() + 20))
        else:
            images = lm.list_available_images()
            row.image.set_value(images[0] if images else "")
        self._renumber()
        self._changed()

    def _remove_frame(self, row: _FrameRow) -> None:
        self._rows.remove(row)
        row.deleteLater()
        self._renumber()
        self._changed()

    def _renumber(self) -> None:
        for index, row in enumerate(self._rows):
            row.index_label.setText(str(index + 1))
        self.empty_label.setVisible(not self._rows)

    def _changed(self, *args) -> None:
        if self._loading:
            return
        self._refresh_meter()
        self.mark_changed()

    def _refresh_meter(self) -> None:
        self.meter.set_frames(
            [
                (row.threshold.value(), pixmaps.load(lm.resolve_image_path(row.image.value()), 96))
                for row in self._rows
                if row.image.value()
            ]
        )

    def _select(self, profile_id: Optional[int]) -> None:
        super()._select(profile_id)
        self._refresh_meter()

    def _refresh_pickers(self) -> None:
        for row in self._rows:
            row.image.update()
            row.blink.update()
        self._refresh_meter()

    # --- preview -------------------------------------------------------------
    def _on_volume(self, volume: float) -> None:
        if not self.isVisible():
            return
        self.meter.set_level(volume)
        profile = self.editor_data()
        frame = lm.pick_frame(profile, volume)
        if frame is None:
            self.stage.set_frame(None, 0, "", i18n.t("preview.empty"))
            return
        path = lm.resolve_image_path(frame.get("path-to-image", ""))
        if self._blinking(profile):
            path = lm.blink_image_path(profile, frame.get("id")) or path
        index = lm.sorted_frames(profile).index(frame) + 1
        caption = i18n.t("preview.frame", index=index, level=frame.get("volume-level", 0))
        self.stage.set_frame(path, int(frame.get("shake-level", 0)), caption)

    def _blinking(self, profile: Dict[str, Any]) -> bool:
        min_ms, max_ms, duration_ms = lm.blink_settings(profile)
        if not (min_ms and max_ms and duration_ms):
            return False
        now = time.monotonic()
        if now < self._blink_until:
            return True
        if now >= self._next_blink:
            if self._next_blink:
                self._blink_until = now + duration_ms / 1000
            self._next_blink = now + random.uniform(min_ms, max_ms) / 1000
            return now < self._blink_until
        return False

    def tick(self, dt: float) -> None:
        self.stage.tick(dt)

    # --- import --------------------------------------------------------------
    def import_dialog(self) -> List[str]:
        files, _ = QFileDialog.getOpenFileNames(self.window(), i18n.t("images.import"), "", i18n.t("images.import_filter"))
        return self.import_files([Path(f) for f in files])

    def import_files(self, files: List[Path]) -> List[str]:
        imported = lm.import_images(files)
        if imported:
            self.state.notify.emit(i18n.t("images.imported", count=len(imported)), "info")
            self.state.images_changed.emit()
        return imported

    def dragEnterEvent(self, event) -> None:
        urls = event.mimeData().urls() if event.mimeData().hasUrls() else []
        if any(Path(u.toLocalFile()).suffix.lower() in lm.IMAGE_SUFFIXES for u in urls if u.isLocalFile()):
            event.acceptProposedAction()

    def dropEvent(self, event) -> None:
        files = [Path(u.toLocalFile()) for u in event.mimeData().urls() if u.isLocalFile()]
        self.import_files(files)
        event.acceptProposedAction()

    def retranslate(self) -> None:
        self.header.set_text(i18n.t("images.title"), i18n.t("images.subtitle"))
        self.profile_list.set_title(i18n.t("images.profiles"))
        self.preview_card.set_title(i18n.t("images.preview"), i18n.t("images.preview_hint"))
        self.frames_hint.setText(i18n.t("images.frames_hint"))
        self.frames_card.set_title(i18n.t("images.frames"))
        self.import_button.setText(" " + i18n.t("images.import"))
        self.folder_button.setToolTip(i18n.t("images.open_folder"))
        self.add_button.setText(" " + i18n.t("images.add_frame"))
        self.empty_label.setText(i18n.t("images.no_frames"))
        self.drop_hint.setText(i18n.t("images.drop_hint"))
        self.blink_card.set_title(i18n.t("images.blink"))
        self.blink_hint.setText(i18n.t("images.blink_hint"))
        for label, key in zip(self.blink_labels, ("images.blink_min", "images.blink_max", "images.blink_duration")):
            label.setText(i18n.t(key))
        for row in self._rows:
            row.retranslate()
        self.retranslate_base()
