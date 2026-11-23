"""Where the avatar sits in OBS: the output card of the image profile editor."""
from typing import Any, Dict, Optional, Tuple

from PySide6.QtCore import QPointF, QRectF, QSize, Qt, Signal
from PySide6.QtGui import QPainter, QPen, QPixmap
from PySide6.QtWidgets import QButtonGroup, QGridLayout, QHBoxLayout, QPushButton, QSizePolicy, QVBoxLayout, QWidget

from app.modules import output as bd
from app.ui import i18n, theme
from app.ui.widgets.common import Card, LabeledSlider, SwitchRow, muted


# --- output in OBS --------------------------------------------------------------------------
class OutputPreview(QWidget):
    """The OBS browser source with the avatar in it; drag to move, wheel to scale."""

    moved = Signal(float, float)   # x, y in % of the source
    scaled = Signal(float)

    SOURCE = (600, 600)

    def __init__(self):
        super().__init__()
        self.setMinimumSize(240, 240)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.setFixedSize(240, 240)
        self.setCursor(Qt.OpenHandCursor)
        self.output = bd.normalize_output(None)
        self.pixmap: Optional[QPixmap] = None
        self.content = (1.0, 1.0)
        self._drag: Optional[Tuple[QPointF, float, float]] = None

    def set_content(self, pixmap: Optional[QPixmap], size: Optional[Tuple[float, float]] = None) -> None:
        self.pixmap = pixmap if pixmap is not None and not pixmap.isNull() else None
        if size is not None:
            self.content = size
        elif self.pixmap is not None:
            self.content = (float(self.pixmap.width()), float(self.pixmap.height()))
        self.update()

    def set_output(self, output: Dict[str, Any]) -> None:
        self.output = bd.normalize_output(output)
        self.update()

    def _box(self) -> QRectF:
        sw, sh = self.SOURCE
        side = min(self.width(), self.height()) - 16
        scale = side / max(sw, sh)
        box = QRectF(0, 0, sw * scale, sh * scale)
        box.moveCenter(QRectF(self.rect()).center())
        return box

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.SmoothPixmapTransform)
        box = self._box()
        p.setPen(Qt.NoPen)
        tile = 10
        p.save()
        p.setClipRect(box)
        for row in range(int(box.height() // tile) + 1):
            for col in range(int(box.width() // tile) + 1):
                p.setBrush(theme.color("#1B1E26" if (row + col) % 2 else "#15171D"))
                p.drawRect(QRectF(box.left() + col * tile, box.top() + row * tile, tile, tile))
        x, y, w, h = bd.place(self.output, self.content[0], self.content[1], box.width(), box.height())
        target = QRectF(box.left() + x, box.top() + y, w, h)
        if self.pixmap is not None:
            if self.output["flip"]:
                p.translate(target.center())
                p.scale(-1, 1)
                p.translate(-target.center())
            p.drawPixmap(target, self.pixmap, QRectF(self.pixmap.rect()))
        else:
            p.setPen(QPen(theme.color(theme.FAINT), 1, Qt.DashLine))
            p.setBrush(Qt.NoBrush)
            p.drawRect(target)
        p.restore()
        p.setPen(QPen(theme.color(theme.ACCENT), 1.5))
        p.setBrush(Qt.NoBrush)
        p.drawRect(box)
        p.setPen(theme.color(theme.FAINT))
        p.setFont(theme.font(7.5))
        p.drawText(QRectF(box.left() + 6, box.top() + 4, box.width(), 14), Qt.AlignLeft, "OBS")

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.LeftButton:
            self._drag = (event.position(), self.output["x"], self.output["y"])
            self.setCursor(Qt.ClosedHandCursor)

    def mouseMoveEvent(self, event) -> None:
        if self._drag is None:
            return
        start, x0, y0 = self._drag
        box = self._box()
        delta = event.position() - start
        x = round(x0 + delta.x() / box.width() * 100, 1)
        y = round(y0 + delta.y() / box.height() * 100, 1)
        self.moved.emit(max(-100.0, min(100.0, x)), max(-100.0, min(100.0, y)))

    def mouseReleaseEvent(self, event) -> None:
        self._drag = None
        self.setCursor(Qt.OpenHandCursor)

    def mouseDoubleClickEvent(self, event) -> None:
        self.moved.emit(0.0, 0.0)

    def wheelEvent(self, event) -> None:
        factor = 1.05 if event.angleDelta().y() > 0 else 1 / 1.05
        self.scaled.emit(max(0.1, min(4.0, round(self.output["scale"] * factor, 3))))


class OutputCard(Card):
    changed = Signal()

    def __init__(self):
        super().__init__()
        self.output = bd.normalize_output(None)
        self._loading = False
        row = QHBoxLayout()
        row.setSpacing(18)
        self.preview = OutputPreview()
        self.preview.moved.connect(lambda x, y: self._update(x=x, y=y))
        self.preview.scaled.connect(lambda s: self._update(scale=s))
        row.addWidget(self.preview, 0, Qt.AlignTop)
        right = QVBoxLayout()
        right.setSpacing(10)
        self.hint = muted("", "faint", wrap=True)
        right.addWidget(self.hint)
        anchor_row = QHBoxLayout()
        anchor_row.setSpacing(12)
        self.anchor_label = muted()
        anchor_row.addWidget(self.anchor_label, 0, Qt.AlignTop)
        grid = QGridLayout()
        grid.setSpacing(3)
        self.anchor_group = QButtonGroup(self)
        self.anchor_buttons: Dict[str, QPushButton] = {}
        layout_map = {"top-left": (0, 0), "top": (0, 1), "top-right": (0, 2), "left": (1, 0), "center": (1, 1),
                      "right": (1, 2), "bottom-left": (2, 0), "bottom": (2, 1), "bottom-right": (2, 2)}
        for anchor, (r, c) in layout_map.items():
            button = QPushButton()
            button.setObjectName("anchor")
            button.setCheckable(True)
            button.setFixedSize(QSize(26, 26))
            button.setCursor(Qt.PointingHandCursor)
            button.clicked.connect(lambda _=False, a=anchor: self._update(anchor=a, x=0.0, y=0.0))
            self.anchor_group.addButton(button)
            self.anchor_buttons[anchor] = button
            grid.addWidget(button, r, c)
        anchor_row.addLayout(grid)
        anchor_row.addStretch()
        right.addLayout(anchor_row)
        self.scale = LabeledSlider(10, 400, lambda v: f"{v}%")
        self.scale.valueChanged.connect(lambda v: self._update(scale=v / 100))
        right.addWidget(self.scale)
        self.offset_x = LabeledSlider(-100, 100, lambda v: f"{v}%")
        self.offset_x.valueChanged.connect(lambda v: self._update(x=float(v)))
        self.offset_y = LabeledSlider(-100, 100, lambda v: f"{v}%")
        self.offset_y.valueChanged.connect(lambda v: self._update(y=float(v)))
        offsets = QHBoxLayout()
        offsets.setSpacing(12)
        offsets.addWidget(self.offset_x)
        offsets.addWidget(self.offset_y)
        right.addLayout(offsets)
        bottom = QHBoxLayout()
        self.flip = SwitchRow()
        self.flip.toggled.connect(lambda on: self._update(flip=on))
        bottom.addWidget(self.flip, 1)
        self.reset = QPushButton()
        self.reset.setCursor(Qt.PointingHandCursor)
        self.reset.clicked.connect(lambda: self._update(**bd.OUTPUT_DEFAULTS))
        bottom.addWidget(self.reset)
        right.addLayout(bottom)
        right.addStretch()
        row.addLayout(right, 1)
        self.body.addLayout(row)
        self.retranslate()

    def set_value(self, output: Dict[str, Any]) -> None:
        self.output = bd.normalize_output(output)
        self._show()

    def value(self) -> Dict[str, Any]:
        return dict(self.output)

    def _update(self, **fields: Any) -> None:
        if self._loading:
            return
        self.output = bd.normalize_output({**self.output, **fields})
        self._show()
        self.changed.emit()

    def _show(self) -> None:
        self._loading = True
        self.anchor_buttons[self.output["anchor"]].setChecked(True)
        self.scale.setValue(round(self.output["scale"] * 100))
        self.offset_x.setValue(round(self.output["x"]))
        self.offset_y.setValue(round(self.output["y"]))
        self.flip.setChecked(self.output["flip"])
        self.preview.set_output(self.output)
        self._loading = False

    def retranslate(self) -> None:
        self.set_title(i18n.t("output.title"))
        self.hint.setText(i18n.t("output.hint"))
        self.anchor_label.setText(i18n.t("output.anchor"))
        self.scale.set_label(i18n.t("output.scale"))
        self.offset_x.set_label(i18n.t("output.x"))
        self.offset_y.set_label(i18n.t("output.y"))
        self.flip.set_text(i18n.t("output.flip"))
        self.reset.setText(i18n.t("output.reset"))
        for anchor, button in self.anchor_buttons.items():
            button.setToolTip(i18n.t(f"output.anchor_{anchor.replace('-', '_')}"))
