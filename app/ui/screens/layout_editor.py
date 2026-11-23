"""Grid editor for the web panel layout.

Widgets are dragged from the list onto the grid, moved by dragging and resized
by their corner; everything snaps to cells and nothing may overlap. Changes
are saved at once (connected devices update live) and can be undone. Until
the first change the editor shows the automatic layout."""
import copy
import json
import time
from typing import Any, Callable, Dict, List, Optional, Tuple

from PySide6.QtCore import QMimeData, QPointF, QRectF, QSize, Qt, QTimer, QUrl, Signal, QObject
from PySide6.QtGui import QBrush, QColor, QDesktopServices, QDrag, QFont, QFontMetricsF, QIcon, QKeySequence, QPainter, \
    QPainterPath, QPen, QPixmap, QShortcut
from PySide6.QtWidgets import (
    QAbstractItemView, QFrame, QHBoxLayout, QLabel, QLineEdit, QMenu, QPushButton, QScrollArea, QSizePolicy, QTabBar,
    QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget,
)

from app import features
from app.modules import logic_manager as lm, panel_layout as pl, storage_manager as sm
from app.modules.studio_bridge import bound_params
from app.ui import i18n, icons, theme
from app.ui.state import AppState
from app.ui.widgets import dialogs
from app.ui.widgets.common import Combo, muted, number_field

MIME = "application/x-pngstreamer-panel-widget"
_ROLE = Qt.UserRole
_MERGE_SECONDS = 1.2


# --- what can be placed --------------------------------------------------------------------
def build_catalog() -> Dict[str, Any]:
    """Every avatar's manual parameters and sequences, the profiles, and what
    the active avatar has (the rest is shown as missing)."""
    from app.modules import web_manager as wm

    avatars: List[Tuple[str, List[Dict[str, Any]], List[Dict[str, Any]]]] = []
    seen = set()
    for profile in sm.list_profiles():
        avatar_id = profile.get("avatar") if lm.is_advanced(profile) else None
        if not avatar_id or avatar_id in seen:
            continue
        seen.add(avatar_id)
        from app.studio import project as pj  # advanced profiles exist only with the Studio

        doc = pj.load(avatar_id)
        if doc is not None:
            params = [p for p in bound_params(profile) if p.get("source", "none") in ("none", "chat")]
            avatars.append((profile.get("name") or doc.get("name") or avatar_id, params, doc.get("sequences", [])))
    context = wm.panel_state()
    return {
        "avatars": avatars,
        "context": context,
        "active_params": {p["id"]: p for p in context["params"] if p.get("manual")},
        "active_sequences": {s["id"] for s in context["sequences"]},
        "profiles": {p["id"]: p["name"] for p in context["profiles"]},
        "sound_profiles": {p["id"]: p["name"] for p in context["sound_profiles"]},
    }


def _param_info(catalog: Dict[str, Any], param_id: str) -> Optional[Dict[str, Any]]:
    if param_id in catalog["active_params"]:
        return catalog["active_params"][param_id]
    for _, params, _ in catalog["avatars"]:
        for p in params:
            if p["id"] == param_id:
                return p
    return None


def describe(catalog: Dict[str, Any], item: Dict[str, Any]) -> Dict[str, Any]:
    """What the editor draws for an item: {title, sub, missing}."""
    kind = item["type"]
    if kind == "button":
        action, target = item["action"], item["target"]
        if action == "param":
            p = _param_info(catalog, target)
            name = (p.get("name") or p["id"]) if p else str(target)
            sub = i18n.t("panel.toggle" if p and p["type"] == "bool" else "panel.reaction")
            missing = target not in catalog["active_params"]
        elif action == "sequence":
            name = next((s.get("name") or s["id"] for _, _, seqs in catalog["avatars"] for s in seqs if s["id"] == target), str(target))
            sub, missing = i18n.t("panel.sequence"), target not in catalog["active_sequences"]
        else:
            source = catalog["profiles" if action == "profile" else "sound_profiles"]
            name = source.get(target, str(target))
            sub = i18n.t("panel.avatar" if action == "profile" else "panel.sound")
            missing = target not in source
        return {"title": item["label"] or name, "sub": sub, "missing": missing}
    if kind == "slider":
        p = _param_info(catalog, item["target"])
        name = (p.get("name") or p["id"]) if p else str(item["target"])
        return {"title": item["label"] or name, "sub": "", "missing": item["target"] not in catalog["active_params"]}
    if kind == "label":
        return {"title": item["text"] or i18n.t("grid.label_empty"), "sub": "", "missing": False}
    if kind == "chat":
        return {"title": i18n.t("panel.chat"), "sub": "", "missing": not catalog["context"].get("chat_enabled")}
    titles = {"profiles": "panel.avatar", "sounds": "panel.sound", "meter": "panel.mic", "avatar": "grid.kind_avatar"}
    return {"title": i18n.t(titles[kind]), "sub": "", "missing": False}


# --- model ---------------------------------------------------------------------------------
class LayoutModel(QObject):
    changed = Signal()
    selection_changed = Signal()

    def __init__(self, state: AppState):
        super().__init__()
        self.state = state
        self.catalog = build_catalog()
        self.layout: Dict[str, Any] = {"pages": []}
        self.auto = True
        self.page_index = 0
        self.selected: Optional[str] = None
        self._undo: List[Tuple[Dict[str, Any], bool]] = []
        self._redo: List[Tuple[Dict[str, Any], bool]] = []
        self._merge: Tuple[str, float] = ("", 0.0)
        self._save_timer = QTimer(self)
        self._save_timer.setSingleShot(True)
        self._save_timer.setInterval(350)
        self._save_timer.timeout.connect(self.save)
        self.reload()

    # loading / saving
    def reload(self) -> None:
        self.catalog = build_catalog()
        stored = self.state.settings().get("panel-layout")
        self.auto = stored is None
        self.layout = pl.generate(self.catalog["context"], i18n.t) if self.auto else pl.normalize(stored)
        self.page_index = min(self.page_index, len(self.layout["pages"]) - 1)
        self.changed.emit()

    def refresh_catalog(self) -> None:
        """Avatar or profiles changed: new names; the automatic layout follows."""
        self.catalog = build_catalog()
        if self.auto:
            self.layout = pl.generate(self.catalog["context"], i18n.t)
            self.page_index = min(self.page_index, len(self.layout["pages"]) - 1)
        self.changed.emit()

    def save(self) -> None:
        self._save_timer.stop()
        self.state.update_settings(panel_layout=None if self.auto else copy.deepcopy(self.layout))

    # editing
    def edit(self, change: Callable[[Dict[str, Any]], Any], merge: str = "") -> Any:
        now = time.monotonic()
        if not (merge and self._merge[0] == merge and now - self._merge[1] < _MERGE_SECONDS):
            self._undo.append((copy.deepcopy(self.layout), self.auto))
            del self._undo[:-100]
        self._merge = (merge, now)
        self._redo.clear()
        self.auto = False
        result = change(self.layout)
        self._save_timer.start()
        self.changed.emit()
        return result

    def _restore(self, source: List, target: List) -> None:
        if not source:
            return
        target.append((copy.deepcopy(self.layout), self.auto))
        self.layout, self.auto = source.pop()
        self._merge = ("", 0.0)
        self.page_index = min(self.page_index, len(self.layout["pages"]) - 1)
        if self.selected and self.item(self.selected) is None:
            self.select(None)
        self.save()
        self.changed.emit()

    def undo(self) -> None:
        self._restore(self._undo, self._redo)

    def redo(self) -> None:
        self._restore(self._redo, self._undo)

    def can_undo(self) -> bool:
        return bool(self._undo)

    def can_redo(self) -> bool:
        return bool(self._redo)

    def reset_auto(self) -> None:
        self._undo.append((copy.deepcopy(self.layout), self.auto))
        self._redo.clear()
        self.auto = True
        self.layout = pl.generate(self.catalog["context"], i18n.t)
        self.page_index = 0
        self.select(None)
        self.save()
        self.changed.emit()

    # pages
    def page(self) -> Dict[str, Any]:
        return self.layout["pages"][self.page_index]

    def set_page(self, index: int) -> None:
        self.page_index = max(0, min(index, len(self.layout["pages"]) - 1))
        self.select(None)
        self.changed.emit()

    def add_page(self) -> None:
        if len(self.layout["pages"]) >= pl.MAX_PAGES:
            return
        cols = self.page()["cols"]
        self.edit(lambda layout: layout["pages"].append({"name": "", "cols": cols, "items": []}))
        self.set_page(len(self.layout["pages"]) - 1)

    def delete_page(self, index: int) -> None:
        if len(self.layout["pages"]) > 1:
            self.edit(lambda layout: layout["pages"].pop(index))
            self.set_page(min(index, len(self.layout["pages"]) - 1))

    def move_page(self, index: int, step: int) -> None:
        target = index + step
        pages = self.layout["pages"]
        if 0 <= target < len(pages):
            self.edit(lambda layout: layout["pages"].insert(target, layout["pages"].pop(index)))
            self.set_page(target)

    def rename_page(self, index: int, name: str) -> None:
        self.edit(lambda layout: layout["pages"][index].__setitem__("name", name))

    def set_cols(self, cols: int) -> None:
        def change(layout: Dict[str, Any]) -> None:
            page = layout["pages"][self.page_index]
            page["cols"] = cols
            layout["pages"][self.page_index] = pl.normalize_page(page)  # narrower: things move down
        self.edit(change, merge="cols")

    # items
    def item(self, item_id: Optional[str]) -> Optional[Dict[str, Any]]:
        return next((i for i in self.page()["items"] if i["id"] == item_id), None) if item_id else None

    def select(self, item_id: Optional[str]) -> None:
        if item_id != self.selected:
            self.selected = item_id
            self.selection_changed.emit()

    def add(self, spec: Dict[str, Any], at: Optional[Tuple[int, int]] = None) -> Optional[str]:
        page = self.page()
        cols = page["cols"]
        item = pl.make_item(spec["type"], cols, **{k: v for k, v in spec.items() if k != "type"})
        if at is not None and pl.fits(page["items"], cols, at[0], at[1], item["w"], item["h"]):
            item["x"], item["y"] = at
        else:
            spot = None
            # Wide widgets that do not fit anywhere get narrower before giving up.
            for width in range(item["w"], 0, -1):
                spot = pl.free_spot(page["items"], cols, width, item["h"])
                if spot is not None:
                    item["w"] = width
                    break
            if spot is None:
                return None
            item["x"], item["y"] = spot
        self.edit(lambda layout: layout["pages"][self.page_index]["items"].append(item))
        self.select(item["id"])
        return item["id"]

    def update_item(self, item_id: str, merge: str = "", **fields: Any) -> bool:
        item = self.item(item_id)
        if item is None:
            return False
        if {"x", "y", "w", "h"} & set(fields):
            geometry = {k: fields.get(k, item[k]) for k in ("x", "y", "w", "h")}
            if not pl.fits(self.page()["items"], self.page()["cols"], ignore=item_id, **geometry):
                return False
        if all(item.get(k) == v for k, v in fields.items()):
            return True

        def change(layout: Dict[str, Any]) -> None:
            target = next(i for i in layout["pages"][self.page_index]["items"] if i["id"] == item_id)
            target.update(fields)
        self.edit(change, merge=f"{item_id}:{merge}" if merge else "")
        return True

    def delete(self, item_id: str) -> None:
        self.edit(lambda layout: layout["pages"][self.page_index].__setitem__(
            "items", [i for i in layout["pages"][self.page_index]["items"] if i["id"] != item_id]))
        self.select(None)

    def duplicate(self, item_id: str) -> None:
        item = self.item(item_id)
        if item is not None:
            spec = {k: v for k, v in item.items() if k not in ("id", "x", "y")}
            self.add(spec)


# --- the grid -------------------------------------------------------------------------------
class GridCanvas(QWidget):
    edit_requested = Signal()

    GAP = 8.0
    MARGIN = 18.0

    def __init__(self, model: LayoutModel):
        super().__init__()
        self.model = model
        self.setAcceptDrops(True)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setMouseTracking(True)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self._drag: Optional[Dict[str, Any]] = None
        self._ghost: Optional[Tuple[int, int, int, int, bool]] = None
        model.changed.connect(self._on_changed)
        model.selection_changed.connect(self.update)
        for keys, handler in ((QKeySequence.Delete, self._delete), ("Backspace", self._delete), ("Ctrl+D", self._duplicate)):
            shortcut = QShortcut(QKeySequence(keys), self)
            shortcut.setContext(Qt.WidgetShortcut)
            shortcut.activated.connect(handler)

    # geometry
    def _cols(self) -> int:
        return self.model.page()["cols"]

    def _rows(self) -> int:
        return max(pl.rows_used(self.model.page()["items"]) + 3, 6)

    def _cell(self) -> float:
        cols = self._cols()
        return max(48.0, min(104.0, (self.width() - 2 * self.MARGIN - self.GAP * (cols - 1)) / cols))

    def _origin(self) -> QPointF:
        cols, cell = self._cols(), self._cell()
        width = cell * cols + self.GAP * (cols - 1)
        return QPointF((self.width() - width) / 2, self.MARGIN)

    def _row_h(self) -> float:
        return round(self._cell() * 0.8)

    def rect_of(self, x: int, y: int, w: int, h: int) -> QRectF:
        o, cell, row = self._origin(), self._cell(), self._row_h()
        return QRectF(o.x() + x * (cell + self.GAP), o.y() + y * (row + self.GAP),
                      w * cell + (w - 1) * self.GAP, h * row + (h - 1) * self.GAP)

    def cell_at(self, point: QPointF) -> Tuple[int, int]:
        o = self._origin()
        return (int((point.x() - o.x()) // (self._cell() + self.GAP)), int((point.y() - o.y()) // (self._row_h() + self.GAP)))

    def _item_at(self, point: QPointF) -> Optional[Dict[str, Any]]:
        for item in self.model.page()["items"]:
            if self.rect_of(item["x"], item["y"], item["w"], item["h"]).contains(point):
                return item
        return None

    def _handle(self, item: Dict[str, Any]) -> QRectF:
        r = self.rect_of(item["x"], item["y"], item["w"], item["h"])
        return QRectF(r.right() - 16, r.bottom() - 16, 22, 22)

    def sizeHint(self) -> QSize:  # noqa: N802 - Qt API
        return QSize(420, int(self.MARGIN * 2 + self._rows() * (self._row_h() + self.GAP)))

    def _on_changed(self) -> None:
        self.setFixedHeight(self.sizeHint().height())
        self.update()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self.setFixedHeight(self.sizeHint().height())

    # painting
    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        page = self.model.page()
        cols, rows = page["cols"], self._rows()
        frame = self.rect_of(0, 0, cols, rows).adjusted(-10, -10, 10, 10)
        p.setPen(QPen(theme.color(theme.BORDER), 1))
        p.setBrush(theme.color(theme.BG))
        p.drawRoundedRect(frame, 18, 18)
        occupied = set()
        for item in page["items"]:
            occupied |= pl.cells(item)
        p.setBrush(Qt.NoBrush)
        p.setPen(QPen(theme.color(theme.BORDER_STRONG), 1, Qt.DashLine))
        for y in range(rows):
            for x in range(cols):
                if (x, y) not in occupied:
                    p.drawRoundedRect(self.rect_of(x, y, 1, 1).adjusted(2, 2, -2, -2), 12, 12)
        for item in page["items"]:
            dragging = self._drag and self._drag.get("id") == item["id"]
            p.setOpacity(0.35 if dragging else 1.0)
            self._paint_item(p, item)
        p.setOpacity(1.0)
        selected = self.model.item(self.model.selected)
        if selected is not None and not self._drag:
            r = self.rect_of(selected["x"], selected["y"], selected["w"], selected["h"]).adjusted(-2, -2, 2, 2)
            p.setPen(QPen(theme.color(theme.ACCENT), 2))
            p.setBrush(Qt.NoBrush)
            p.drawRoundedRect(r, 18, 18)
            handle = self._handle(selected)
            p.setBrush(theme.color(theme.ACCENT))
            p.setPen(Qt.NoPen)
            p.drawEllipse(handle.center(), 7, 7)
            p.setPen(QPen(theme.color(theme.ACCENT_INK), 1.6))
            c = handle.center()
            p.drawLine(QPointF(c.x() - 3, c.y() + 3), QPointF(c.x() + 3, c.y() - 3))
        if self._ghost is not None:
            x, y, w, h, ok = self._ghost
            color = theme.ACCENT if ok else theme.DANGER
            p.setPen(QPen(theme.color(color), 2, Qt.DashLine))
            p.setBrush(theme.color(color, 0.12))
            p.drawRoundedRect(self.rect_of(x, y, w, h), 16, 16)

    def _paint_item(self, p: QPainter, item: Dict[str, Any]) -> None:
        r = self.rect_of(item["x"], item["y"], item["w"], item["h"])
        info = describe(self.model.catalog, item)
        kind = item["type"]
        color = item.get("color") or ""
        p.save()
        if info["missing"]:
            p.setOpacity(p.opacity() * 0.45)
        title_font = theme.font(9.5, QFont.DemiBold)
        small = theme.font(8)
        if kind == "label":
            p.setPen(theme.color(theme.MUTED))
            p.setFont(theme.font(8, QFont.DemiBold))
            align = (Qt.AlignHCenter if item.get("align") == "center" else Qt.AlignLeft) | Qt.AlignBottom
            p.drawText(r.adjusted(6, 4, -6, -6), align, info["title"].upper())
            p.restore()
            return
        p.setPen(QPen(theme.color(theme.BORDER), 1))
        p.setBrush(theme.color("#181A21" if kind == "button" else theme.SURFACE))
        p.drawRoundedRect(r, 14, 14)
        if color and kind == "button":
            path = QPainterPath()
            path.addRoundedRect(r, 14, 14)
            p.setClipPath(path)
            p.fillRect(QRectF(r.left(), r.top(), 4, r.height()), theme.color(color))
            p.setClipping(False)
        inner = r.adjusted(12, 10, -12, -10)
        p.setPen(theme.color(theme.TEXT))
        p.setFont(title_font)
        if kind == "button":
            p.drawText(inner, Qt.AlignLeft | Qt.AlignTop | Qt.TextWordWrap, info["title"])
            p.setPen(theme.color(theme.FAINT))
            p.setFont(small)
            p.drawText(inner, Qt.AlignLeft | Qt.AlignBottom, info["sub"])
        elif kind == "slider":
            vertical = item["h"] > item["w"]
            p.drawText(inner, Qt.AlignLeft | Qt.AlignTop, info["title"])
            accent = theme.color(color or theme.ACCENT)
            if vertical:
                cx = inner.center().x()
                top, bottom = inner.top() + 26, inner.bottom() - 4
                p.setPen(QPen(theme.color(theme.SURFACE_3), 5, Qt.SolidLine, Qt.RoundCap))
                p.drawLine(QPointF(cx, top), QPointF(cx, bottom))
                mid = (top + bottom) / 2
                p.setPen(QPen(accent, 5, Qt.SolidLine, Qt.RoundCap))
                p.drawLine(QPointF(cx, mid), QPointF(cx, bottom))
                p.setPen(Qt.NoPen)
                p.setBrush(accent)
                p.drawEllipse(QPointF(cx, mid), 7, 7)
            else:
                y = inner.bottom() - 8
                p.setPen(QPen(theme.color(theme.SURFACE_3), 5, Qt.SolidLine, Qt.RoundCap))
                p.drawLine(QPointF(inner.left(), y), QPointF(inner.right(), y))
                mid = inner.left() + inner.width() * 0.45
                p.setPen(QPen(accent, 5, Qt.SolidLine, Qt.RoundCap))
                p.drawLine(QPointF(inner.left(), y), QPointF(mid, y))
                p.setPen(Qt.NoPen)
                p.setBrush(accent)
                p.drawEllipse(QPointF(mid, y), 7, 7)
        elif kind in ("profiles", "sounds"):
            p.setPen(theme.color(theme.MUTED))
            p.setFont(small)
            p.drawText(inner, Qt.AlignLeft | Qt.AlignTop, info["title"])
            names = list((self.model.catalog["profiles"] if kind == "profiles" else self.model.catalog["sound_profiles"]).values())
            x, y = inner.left(), inner.top() + 20
            p.setFont(theme.font(8.5))
            metrics = QFontMetricsF(p.font())
            for index, name in enumerate(names):
                w = metrics.horizontalAdvance(name) + 20
                if x + w > inner.right() and x > inner.left():
                    x, y = inner.left(), y + 30
                if y + 26 > r.bottom():
                    break
                chip = QRectF(x, y, min(w, inner.width()), 26)
                p.setPen(QPen(theme.color(theme.ACCENT if index == 0 else theme.BORDER), 1))
                p.setBrush(theme.color(theme.SURFACE_2))
                p.drawRoundedRect(chip, 9, 9)
                p.setPen(theme.color(theme.ACCENT if index == 0 else theme.TEXT))
                p.drawText(chip, Qt.AlignCenter, metrics.elidedText(name, Qt.ElideRight, chip.width() - 12))
                x += w + 6
        elif kind == "avatar":
            preview = self._avatar_preview()
            p.fillRect(inner.adjusted(-6, -4, 6, 4), theme.color("#14161B"))
            if preview is not None:
                scaled = preview.scaled(inner.size().toSize(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
                x = inner.center().x() - scaled.width() / 2
                y = inner.bottom() - scaled.height()
                p.drawPixmap(QPointF(x, y), scaled)
            p.setPen(theme.color(theme.MUTED))
            p.setFont(small)
            p.drawText(inner, Qt.AlignLeft | Qt.AlignTop, info["title"])
        elif kind == "meter":
            p.setPen(theme.color(theme.MUTED))
            p.setFont(small)
            p.drawText(inner, Qt.AlignLeft | Qt.AlignTop, info["title"])
            bar = QRectF(inner.left(), inner.center().y() + 2, inner.width(), 10)
            p.setPen(Qt.NoPen)
            p.setBrush(theme.color(theme.SURFACE_3))
            p.drawRoundedRect(bar, 5, 5)
            p.setBrush(theme.color(theme.ACCENT))
            p.drawRoundedRect(QRectF(bar.left(), bar.top(), bar.width() * 0.6, bar.height()), 5, 5)
        elif kind == "chat":
            p.setPen(theme.color(theme.MUTED))
            p.setFont(small)
            p.drawText(inner, Qt.AlignLeft | Qt.AlignTop, info["title"])
            y = inner.top() + 22
            widths = (0.8, 0.55, 0.9, 0.4, 0.7, 0.6)
            colors = ("#FF7AC6", "#5AC8FA", "#C8F65A", "#B58CFF", "#FFB547", "#FF6B6B")
            for index in range(20):
                if y + 22 > inner.bottom():
                    break
                line = QRectF(inner.left(), y, inner.width() * widths[index % 6], 22)
                p.setPen(Qt.NoPen)
                p.setBrush(theme.color(theme.SURFACE_2))
                p.drawRoundedRect(line, 8, 8)
                p.setBrush(theme.color(colors[index % 6]))
                p.drawRoundedRect(QRectF(line.left() + 8, line.top() + 8, min(40, line.width() * 0.3), 6), 3, 3)
                y += 28
        if info["missing"]:
            p.setOpacity(1.0)
            p.setPen(theme.color(theme.WARNING))
            p.setFont(theme.font(7.5))
            text = i18n.t("grid.chat_off") if kind == "chat" else i18n.t("grid.missing")
            p.drawText(r.adjusted(8, 6, -8, -6), Qt.AlignRight | Qt.AlignTop | Qt.TextWordWrap, text)
        p.restore()

    def _avatar_preview(self):
        """The active avatar for the avatar widget's picture (cached briefly)."""
        import time as _time

        from app.modules import logic_manager as lm
        from app.ui import pixmaps

        cached = getattr(self, "_avatar_cache", None)
        if cached and _time.monotonic() - cached[0] < 5:
            return cached[1]
        profile = lm.get_active_image_profile() or {}
        if lm.is_advanced(profile):
            from app.ui.studio.render import scene_pixmap

            pm = scene_pixmap(profile.get("avatar"), 300)
        else:
            frames = lm.sorted_frames(profile)
            pm = pixmaps.load(lm.resolve_image_path(frames[0]["path-to-image"]), 300) if frames else None
        self._avatar_cache = (_time.monotonic(), pm)
        return pm

    # mouse
    def mousePressEvent(self, event) -> None:
        if event.button() != Qt.LeftButton:
            return super().mousePressEvent(event)
        self.setFocus()
        point = event.position()
        selected = self.model.item(self.model.selected)
        if selected is not None and self._handle(selected).contains(point):
            self._drag = {"mode": "resize", "id": selected["id"]}
            return
        item = self._item_at(point)
        self.model.select(item["id"] if item else None)
        if item is not None:
            cx, cy = self.cell_at(point)
            self._drag = {"mode": "move", "id": item["id"], "dx": cx - item["x"], "dy": cy - item["y"], "start": point,
                          "moved": False}

    def mouseMoveEvent(self, event) -> None:
        point = event.position()
        if self._drag is None:
            selected = self.model.item(self.model.selected)
            if selected is not None and self._handle(selected).contains(point):
                self.setCursor(Qt.SizeFDiagCursor)
            elif self._item_at(point) is not None:
                self.setCursor(Qt.OpenHandCursor)
            else:
                self.unsetCursor()
            return
        item = self.model.item(self._drag["id"])
        if item is None:
            return
        cols, (cx, cy) = self._cols(), self.cell_at(point)
        if self._drag["mode"] == "move":
            if not self._drag["moved"] and (point - self._drag["start"]).manhattanLength() < 6:
                return
            self._drag["moved"] = True
            self.setCursor(Qt.ClosedHandCursor)
            x = max(0, min(cols - item["w"], cx - self._drag["dx"]))
            y = max(0, cy - self._drag["dy"])
            w, h = item["w"], item["h"]
        else:
            x, y = item["x"], item["y"]
            w = max(1, min(cols - x, cx - x + 1))
            h = max(1, min(pl.MAX_ROWS - y, cy - y + 1))
        ok = pl.fits(self.model.page()["items"], cols, x, y, w, h, ignore=item["id"])
        self._ghost = (x, y, w, h, ok)
        self.update()

    def mouseReleaseEvent(self, event) -> None:
        drag, ghost = self._drag, self._ghost
        self._drag, self._ghost = None, None
        self.unsetCursor()
        if drag and ghost and ghost[4]:
            x, y, w, h, _ = ghost
            self.model.update_item(drag["id"], x=x, y=y, w=w, h=h)
        self.update()

    def mouseDoubleClickEvent(self, event) -> None:
        if self._item_at(event.position()) is not None:
            self.edit_requested.emit()

    def contextMenuEvent(self, event) -> None:
        item = self._item_at(QPointF(event.pos()))
        if item is None:
            return
        self.model.select(item["id"])
        menu = QMenu(self)
        menu.addAction(i18n.t("grid.duplicate") + "\tCtrl+D", self._duplicate)
        menu.addAction(i18n.t("grid.delete") + "\tDel", self._delete)
        menu.exec(event.globalPos())

    def keyPressEvent(self, event) -> None:
        item = self.model.item(self.model.selected)
        steps = {Qt.Key_Left: (-1, 0), Qt.Key_Right: (1, 0), Qt.Key_Up: (0, -1), Qt.Key_Down: (0, 1)}
        if item is not None and event.key() in steps:
            dx, dy = steps[event.key()]
            if event.modifiers() & Qt.ShiftModifier:  # Shift+arrows resize
                self.model.update_item(item["id"], merge="size", w=max(1, item["w"] + dx), h=max(1, item["h"] + dy))
            else:
                self.model.update_item(item["id"], merge="move", x=item["x"] + dx, y=item["y"] + dy)
            return
        super().keyPressEvent(event)

    def _delete(self) -> None:
        if self.model.selected:
            self.model.delete(self.model.selected)

    def _duplicate(self) -> None:
        if self.model.selected:
            self.model.duplicate(self.model.selected)

    # dropping from the widget list
    def _spec(self, mime: QMimeData) -> Optional[Dict[str, Any]]:
        if not mime.hasFormat(MIME):
            return None
        try:
            return json.loads(bytes(mime.data(MIME)).decode("utf-8"))
        except ValueError:
            return None

    def dragEnterEvent(self, event) -> None:
        if self._spec(event.mimeData()) is not None:
            event.acceptProposedAction()

    def dragMoveEvent(self, event) -> None:
        spec = self._spec(event.mimeData())
        if spec is None:
            return
        cols = self._cols()
        w, h = pl.default_size(spec["type"], cols)
        cx, cy = self.cell_at(event.position())
        x, y = max(0, min(cols - w, cx)), max(0, cy)
        self._ghost = (x, y, w, h, pl.fits(self.model.page()["items"], cols, x, y, w, h))
        self.update()
        event.acceptProposedAction()

    def dragLeaveEvent(self, event) -> None:
        self._ghost = None
        self.update()

    def dropEvent(self, event) -> None:
        spec, ghost = self._spec(event.mimeData()), self._ghost
        self._ghost = None
        if spec is not None:
            self.model.add(spec, at=(ghost[0], ghost[1]) if ghost and ghost[4] else None)
            event.acceptProposedAction()
        self.update()


# --- the list of widgets -----------------------------------------------------------------------
class Palette(QTreeWidget):
    add_requested = Signal(dict)

    def __init__(self):
        super().__init__()
        self.setHeaderHidden(True)
        self.setDragEnabled(True)
        self.setDragDropMode(QAbstractItemView.DragOnly)
        self.itemDoubleClicked.connect(lambda node, _: self._request(node))

    def _request(self, node: Optional[QTreeWidgetItem]) -> None:
        if node is not None and node.data(0, _ROLE):
            self.add_requested.emit(node.data(0, _ROLE))

    def add_current(self) -> None:
        self._request(self.currentItem())

    def startDrag(self, actions) -> None:  # noqa: N802 - Qt API
        node = self.currentItem()
        spec = node.data(0, _ROLE) if node else None
        if not spec:
            return
        mime = QMimeData()
        mime.setData(MIME, json.dumps(spec).encode("utf-8"))
        drag = QDrag(self)
        drag.setMimeData(mime)
        label = QPixmap(180, 34)
        label.fill(Qt.transparent)
        p = QPainter(label)
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(QPen(theme.color(theme.ACCENT), 1.5))
        p.setBrush(theme.color(theme.SURFACE_2))
        p.drawRoundedRect(QRectF(1, 1, 178, 32), 10, 10)
        p.setPen(theme.color(theme.TEXT))
        p.setFont(theme.font(9))
        p.drawText(QRectF(10, 0, 162, 34), Qt.AlignVCenter, QFontMetricsF(p.font()).elidedText(node.text(0), Qt.ElideRight, 160))
        p.end()
        drag.setPixmap(label)
        drag.setHotSpot(label.rect().center())
        drag.exec(Qt.CopyAction)

    def fill(self, catalog: Dict[str, Any]) -> None:
        self.clear()

        def branch(text: str) -> QTreeWidgetItem:
            node = QTreeWidgetItem([text])
            node.setFlags(Qt.ItemIsEnabled)
            node.setForeground(0, QBrush(QColor(theme.MUTED)))
            self.addTopLevelItem(node)
            return node

        def leaf(parent: QTreeWidgetItem, text: str, spec: Dict[str, Any], tip: str = "") -> None:
            node = QTreeWidgetItem([text])
            node.setData(0, _ROLE, spec)
            node.setToolTip(0, tip or text)
            node.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsDragEnabled)
            parent.addChild(node)

        basics = branch(i18n.t("grid.basics"))
        leaf(basics, i18n.t("grid.kind_label"), {"type": "label", "text": i18n.t("grid.label_default")})
        leaf(basics, i18n.t("grid.kind_chat"), {"type": "chat"}, i18n.t("grid.chat_hint"))
        leaf(basics, i18n.t("grid.kind_meter"), {"type": "meter"})
        leaf(basics, i18n.t("grid.kind_avatar"), {"type": "avatar"}, i18n.t("grid.avatar_hint"))
        leaf(basics, i18n.t("grid.kind_profiles"), {"type": "profiles"})
        leaf(basics, i18n.t("grid.kind_sounds"), {"type": "sounds"})
        if not catalog["avatars"] and features.STUDIO:
            from app.ui.studio.profile_page import no_scenes_note

            note = branch(no_scenes_note())
            note.setToolTip(0, no_scenes_note())
        for name, params, sequences in catalog["avatars"]:
            avatar = branch(name)
            for p in params:
                kind = "slider" if p["type"] == "number" else "button"
                spec = {"type": "slider", "target": p["id"]} if kind == "slider" else {"type": "button", "action": "param", "target": p["id"]}
                leaf(avatar, f"{i18n.t('grid.kind_' + p['type'])}: {p.get('name') or p['id']}", spec)
            for s in sequences:
                leaf(avatar, f"{i18n.t('grid.kind_sequence')}: {s.get('name') or s['id']}",
                     {"type": "button", "action": "sequence", "target": s["id"]})
        images = branch(i18n.t("grid.image_buttons"))
        for profile_id, name in catalog["profiles"].items():
            leaf(images, name, {"type": "button", "action": "profile", "target": profile_id})
        sounds = branch(i18n.t("grid.sound_buttons"))
        for profile_id, name in catalog["sound_profiles"].items():
            leaf(sounds, name, {"type": "button", "action": "sound-profile", "target": profile_id})
        self.expandAll()


# --- properties of the selected widget -------------------------------------------------------------
class Inspector(QFrame):
    def __init__(self, model: LayoutModel):
        super().__init__()
        self.setObjectName("subcard")
        self.model = model
        self._loading = False
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(8)
        self.heading = QLabel()
        self.heading.setFont(theme.font(10, QFont.DemiBold))
        layout.addWidget(self.heading)
        self.hint = muted(i18n.t("grid.hint"), "faint", wrap=True)
        layout.addWidget(self.hint)

        self.fields = QWidget()
        fields = QVBoxLayout(self.fields)
        fields.setContentsMargins(0, 0, 0, 0)
        fields.setSpacing(6)
        self.target_label = muted(i18n.t("grid.target"))
        self.target = Combo()
        self.target.currentIndexChanged.connect(self._on_target)
        self.text_label = muted()
        self.text = QLineEdit()
        self.text.textEdited.connect(self._on_text)
        self.color_label = muted(i18n.t("layout.color"))
        self.color = Combo()
        self.color.set_items([(i18n.t(f"layout.color_{pl.COLOR_NAMES[c]}") if c else i18n.t("layout.color_none"), c)
                              for c in pl.COLORS])
        for index, value in enumerate(pl.COLORS):
            if value:
                swatch = QPixmap(14, 14)
                swatch.fill(QColor(value))
                self.color.setItemIcon(index, QIcon(swatch))
        self.color.currentIndexChanged.connect(lambda _: self._set(color=self.color.currentData()))
        self.align_label = muted(i18n.t("grid.align"))
        self.align = Combo()
        self.align.set_items([(i18n.t("grid.align_left"), "left"), (i18n.t("grid.align_center"), "center")])
        self.align.currentIndexChanged.connect(lambda _: self._set(align=self.align.currentData()))
        size_row = QHBoxLayout()
        size_row.setSpacing(6)
        self.size_label = muted(i18n.t("grid.size"))
        self.width_field = number_field(1, pl.MAX_COLS)
        self.height_field = number_field(1, pl.MAX_ROWS)
        self.width_field.valueChanged.connect(lambda v: self._resize(w=v))
        self.height_field.valueChanged.connect(lambda v: self._resize(h=v))
        size_row.addWidget(self.size_label, 1)
        size_row.addWidget(self.width_field)
        size_row.addWidget(QLabel("×"))
        size_row.addWidget(self.height_field)
        for widget in (self.target_label, self.target, self.text_label, self.text, self.color_label, self.color,
                       self.align_label, self.align):
            fields.addWidget(widget)
        fields.addLayout(size_row)
        buttons = QHBoxLayout()
        duplicate = QPushButton(" " + i18n.t("grid.duplicate"))
        duplicate.setIcon(icons.icon("duplicate", theme.TEXT))
        duplicate.clicked.connect(lambda: self.model.selected and self.model.duplicate(self.model.selected))
        delete = QPushButton(" " + i18n.t("grid.delete"))
        delete.setObjectName("danger")
        delete.setIcon(icons.icon("trash", theme.DANGER))
        delete.clicked.connect(lambda: self.model.selected and self.model.delete(self.model.selected))
        buttons.addWidget(duplicate)
        buttons.addWidget(delete)
        buttons.addStretch()
        fields.addLayout(buttons)
        layout.addWidget(self.fields)
        model.selection_changed.connect(self.refresh)
        model.changed.connect(self.refresh)
        self.refresh()

    def focus_text(self) -> None:
        if self.text.isVisible():
            self.text.setFocus()
            self.text.selectAll()

    def _targets(self, item: Dict[str, Any]) -> List[Tuple[str, Any]]:
        catalog = self.model.catalog
        choices: List[Tuple[str, Any]] = []
        seen = set()
        for avatar, params, sequences in catalog["avatars"]:
            for p in params:
                wanted = p["type"] == "number" if item["type"] == "slider" else p["type"] != "number"
                if wanted and ("param", p["id"]) not in seen:
                    seen.add(("param", p["id"]))
                    choices.append((f"{p.get('name') or p['id']} · {avatar}", ("param", p["id"])))
            if item["type"] == "button":
                for s in sequences:
                    if ("sequence", s["id"]) not in seen:
                        seen.add(("sequence", s["id"]))
                        choices.append((f"{i18n.t('grid.kind_sequence')}: {s.get('name') or s['id']} · {avatar}", ("sequence", s["id"])))
        if item["type"] == "button":
            choices += [(f"{i18n.t('panel.avatar')}: {n}", ("profile", i)) for i, n in catalog["profiles"].items()]
            choices += [(f"{i18n.t('panel.sound')}: {n}", ("sound-profile", i)) for i, n in catalog["sound_profiles"].items()]
        current = ("param", item["target"]) if item["type"] == "slider" else (item["action"], item["target"])
        if current not in [c[1] for c in choices]:
            choices.insert(0, (f"{item['target']} · {i18n.t('grid.missing')}", current))
        return choices

    def refresh(self) -> None:
        item = self.model.item(self.model.selected)
        self.hint.setVisible(item is None)
        self.fields.setVisible(item is not None)
        if item is None:
            self.heading.setText(i18n.t("grid.nothing_selected"))
            return
        self._loading = True
        kind = item["type"]
        self.heading.setText(i18n.t(f"grid.kind_{kind}") if kind not in ("button",) else i18n.t("grid.kind_button"))
        has_target = kind in ("button", "slider")
        self.target_label.setVisible(has_target)
        self.target.setVisible(has_target)
        if has_target:
            choices = self._targets(item)
            current = ("param", item["target"]) if kind == "slider" else (item["action"], item["target"])
            self.target.set_items(choices, current)
        has_text = kind in ("button", "slider", "label")
        self.text_label.setVisible(has_text)
        self.text.setVisible(has_text)
        if has_text:
            self.text_label.setText(i18n.t("grid.text") if kind == "label" else i18n.t("layout.label"))
            value = item["text"] if kind == "label" else item["label"]
            if self.text.text() != value:
                self.text.setText(value)
            info = describe(self.model.catalog, {**item, "label": ""}) if kind != "label" else {"title": ""}
            self.text.setPlaceholderText(info["title"])
        has_color = kind in ("button", "slider")
        self.color_label.setVisible(has_color)
        self.color.setVisible(has_color)
        if has_color:
            self.color.setCurrentIndex(max(self.color.findData(item["color"]), 0))
        self.align_label.setVisible(kind == "label")
        self.align.setVisible(kind == "label")
        if kind == "label":
            self.align.setCurrentIndex(max(self.align.findData(item["align"]), 0))
        self.width_field.setMaximum(self.model.page()["cols"])
        self.width_field.setValue(item["w"])
        self.height_field.setValue(item["h"])
        self._loading = False

    def _set(self, merge: str = "", **fields: Any) -> None:
        if not self._loading and self.model.selected:
            self.model.update_item(self.model.selected, merge=merge, **fields)

    def _on_text(self, text: str) -> None:
        item = self.model.item(self.model.selected)
        if item is not None:
            self._set(merge="text", **({"text": text} if item["type"] == "label" else {"label": text}))

    def _on_target(self, _index: int) -> None:
        data = self.target.currentData()
        item = self.model.item(self.model.selected)
        if self._loading or item is None or data is None:
            return
        action, target = data
        self._set(target=target) if item["type"] == "slider" else self._set(action=action, target=target)

    def _resize(self, **size: int) -> None:
        if self._loading or not self.model.selected:
            return
        if not self.model.update_item(self.model.selected, merge="size", **size):
            self.refresh()  # does not fit: show the real size again


# --- the whole editor --------------------------------------------------------------------------
class LayoutEditor(QWidget):
    def __init__(self, state: AppState):
        super().__init__()
        self.state = state
        self.model = LayoutModel(state)
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(10)

        # toolbar: pages, columns, undo, automatic layout, open in browser
        bar = QHBoxLayout()
        bar.setSpacing(8)
        self.tabs = QTabBar()
        self.tabs.setExpanding(False)
        self.tabs.setDrawBase(False)
        self.tabs.setMovable(True)
        self.tabs.currentChanged.connect(self._on_tab)
        self.tabs.tabMoved.connect(self._on_tab_moved)
        self.tabs.tabBarDoubleClicked.connect(self._rename_page)
        self.tabs.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tabs.customContextMenuRequested.connect(self._page_menu)
        bar.addWidget(self.tabs, 1)
        add_page = QPushButton()
        add_page.setIcon(icons.icon("plus", theme.TEXT))
        add_page.setToolTip(i18n.t("grid.add_page"))
        add_page.setFixedWidth(36)
        add_page.clicked.connect(self.model.add_page)
        bar.addWidget(add_page)
        bar.addSpacing(8)
        bar.addWidget(muted(i18n.t("grid.columns")))
        self.cols = number_field(pl.MIN_COLS, pl.MAX_COLS)
        self.cols.setFixedWidth(52)
        self.cols.valueChanged.connect(self._on_cols)
        bar.addWidget(self.cols)
        bar.addSpacing(8)
        self.undo_button = QPushButton()
        self.undo_button.setIcon(icons.icon("undo", theme.TEXT))
        self.undo_button.setToolTip(i18n.t("grid.undo"))
        self.undo_button.setFixedWidth(36)
        self.undo_button.clicked.connect(self.model.undo)
        self.redo_button = QPushButton()
        self.redo_button.setIcon(icons.icon("redo", theme.TEXT))
        self.redo_button.setToolTip(i18n.t("grid.redo"))
        self.redo_button.setFixedWidth(36)
        self.redo_button.clicked.connect(self.model.redo)
        bar.addWidget(self.undo_button)
        bar.addWidget(self.redo_button)
        open_button = QPushButton(" " + i18n.t("grid.open_browser"))
        open_button.setIcon(icons.icon("launch", theme.TEXT))
        open_button.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(f"http://127.0.0.1:{self.state.port()}/panel")))
        bar.addWidget(open_button)
        root.addLayout(bar)

        self.auto_note = QFrame()
        self.auto_note.setObjectName("subcard")
        note = QHBoxLayout(self.auto_note)
        note.setContentsMargins(14, 8, 8, 8)
        self.auto_text = muted("", "muted", wrap=True)
        note.addWidget(self.auto_text, 1)
        self.reset_button = QPushButton(i18n.t("grid.reset"))
        self.reset_button.clicked.connect(self._reset)
        note.addWidget(self.reset_button)
        root.addWidget(self.auto_note)

        body = QHBoxLayout()
        body.setSpacing(14)
        side = QVBoxLayout()
        side.setSpacing(8)
        side.addWidget(muted(i18n.t("grid.widgets")))
        self.palette = Palette()
        self.palette.setFixedWidth(250)
        self.palette.add_requested.connect(lambda spec: self.model.add(spec))
        side.addWidget(self.palette, 1)
        palette_hint = muted(i18n.t("grid.palette_hint"), "faint", wrap=True)
        palette_hint.setFixedWidth(250)
        side.addWidget(palette_hint)
        body.addLayout(side)
        self.canvas = GridCanvas(self.model)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setAlignment(Qt.AlignTop)
        scroll.setWidget(self.canvas)
        body.addWidget(scroll, 1)
        inspector_column = QVBoxLayout()
        self.inspector = Inspector(self.model)
        self.inspector.setFixedWidth(300)
        inspector_column.addWidget(self.inspector)
        inspector_column.addStretch()
        body.addLayout(inspector_column)
        root.addLayout(body, 1)

        self.canvas.edit_requested.connect(self.inspector.focus_text)
        for keys, handler in (("Ctrl+Z", self.model.undo), ("Ctrl+Y", self.model.redo), ("Ctrl+Shift+Z", self.model.redo)):
            shortcut = QShortcut(QKeySequence(keys), self)
            shortcut.setContext(Qt.WidgetWithChildrenShortcut)
            shortcut.activated.connect(handler)
        self.model.changed.connect(self._refresh)
        state.profiles_changed.connect(self.model.refresh_catalog)
        state.avatar_changed.connect(self.model.refresh_catalog)
        state.chat_changed.connect(self.model.refresh_catalog)
        self.palette.fill(self.model.catalog)
        self._refresh()

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self.model.refresh_catalog()
        self.palette.fill(self.model.catalog)

    def _refresh(self) -> None:
        pages = self.model.layout["pages"]
        self.tabs.blockSignals(True)
        while self.tabs.count() > len(pages):
            self.tabs.removeTab(self.tabs.count() - 1)
        for index, page in enumerate(pages):
            title = page["name"] or i18n.t("layout.page_default", index=index + 1)
            if index < self.tabs.count():
                self.tabs.setTabText(index, title)
            else:
                self.tabs.addTab(title)
        self.tabs.setCurrentIndex(self.model.page_index)
        self.tabs.blockSignals(False)
        self.cols.blockSignals(True)
        self.cols.setValue(self.model.page()["cols"])
        self.cols.blockSignals(False)
        self.undo_button.setEnabled(self.model.can_undo())
        self.redo_button.setEnabled(self.model.can_redo())
        self.auto_text.setText(i18n.t("grid.auto_note") if self.model.auto else i18n.t("grid.custom_note"))
        self.reset_button.setVisible(not self.model.auto)
        self.canvas.update()

    def _on_tab(self, index: int) -> None:
        if index >= 0:
            self.model.set_page(index)

    def _on_tab_moved(self, source: int, target: int) -> None:
        self.model.move_page(source, target - source)

    def _on_cols(self, cols: int) -> None:
        if cols != self.model.page()["cols"]:
            self.model.set_cols(cols)

    def _rename_page(self, index: int) -> None:
        if index < 0:
            return
        name = dialogs.prompt_text(self, i18n.t("layout.page_name"), self.model.layout["pages"][index]["name"])
        if name is not None:
            self.model.rename_page(index, name)

    def _page_menu(self, position) -> None:
        index = self.tabs.tabAt(position)
        if index < 0:
            return
        menu = QMenu(self)
        menu.addAction(i18n.t("grid.rename_page"), lambda: self._rename_page(index))
        delete = menu.addAction(i18n.t("grid.delete_page"), lambda: self.model.delete_page(index))
        delete.setEnabled(len(self.model.layout["pages"]) > 1)
        menu.exec(self.tabs.mapToGlobal(position))

    def _reset(self) -> None:
        if dialogs.confirm(self, i18n.t("grid.reset_title"), i18n.t("grid.reset_text"), i18n.t("grid.reset"), danger=True):
            self.model.reset_auto()

    def retranslate(self) -> None:
        self.palette.fill(self.model.catalog)
        self.inspector.refresh()
        self._refresh()
