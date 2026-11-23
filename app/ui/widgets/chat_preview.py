"""Preview of the Twitch chat overlay: drawn the way chat.html shows it in OBS
(bottom-anchored bubbles, name colors, emotes), with the overlay settings
applied live. Shows sample messages until the real chat has some."""
import time
from typing import Any, Dict, List, Optional, Tuple

from PySide6.QtCore import QRectF, QSize, Qt, QUrl
from PySide6.QtGui import QColor, QFont, QFontMetricsF, QLinearGradient, QPainter, QPen, QPixmap
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkReply, QNetworkRequest
from PySide6.QtWidgets import QSizePolicy, QWidget

from app.modules import twitch_chat as tc
from app.ui import i18n, theme

SOURCE_W, SOURCE_H = 400, 600  # the browser source size the README suggests

# Text parts are translation keys ("t:…"), so the sample speaks the app's language.
_SAMPLE = [
    ("Lis_Ryzhiy", "#FF7AC6", [("text", "t:chat_sample.hello"), ("text", " "), ("emote", "25")]),
    ("nightbot", "#5AC8FA", [("text", "t:chat_sample.follow")]),
    ("pixel_owl", "#C8F65A", [("text", "!discord")]),
    ("MoonCat", "#B58CFF", [("text", "t:chat_sample.avatar")]),
    ("dark_knight", "#1E1E7A", [("text", "GG "), ("emote", "354"), ("text", " "), ("emote", "354")]),
    ("streamfan", "#FFB547", [("text", "t:chat_sample.next")]),
    ("pepe_fan", "#4CD9A0", [("text", "EZ RainTime Clap PETPET")]),
]


def sample_messages() -> List[Dict[str, Any]]:
    now = time.time()
    messages = []
    for index, (name, color, parts) in enumerate(_SAMPLE):
        fragments = [
            {"type": "emote", "text": "Kappa" if value == "25" else "4Head", "url": tc.EMOTE_URL.format(id=value)}
            if kind == "emote" else {"type": "text", "text": i18n.t(value[2:]) if value.startswith("t:") else value}
            for kind, value in parts
        ]
        messages.append({
            "id": f"sample-{index}", "user": name.lower(), "name": name, "color": tc.readable(color),
            "text": "".join(f["text"] for f in fragments), "action": False, "fragments": fragments, "time": now,
        })
    return messages


class _Emotes:
    """Downloads emote images once and keeps them for the session."""

    def __init__(self) -> None:
        self._network: Optional[QNetworkAccessManager] = None
        self.images: Dict[str, QPixmap] = {}
        self._pending: set = set()
        self._listeners: List[Any] = []

    def get(self, url: str, listener: QWidget) -> Optional[QPixmap]:
        if url in self.images:
            return self.images[url]
        if listener not in self._listeners:
            self._listeners.append(listener)
            listener.destroyed.connect(lambda *_: self._listeners.remove(listener) if listener in self._listeners else None)
        if url not in self._pending:
            if self._network is None:
                self._network = QNetworkAccessManager()
            self._pending.add(url)
            reply = self._network.get(QNetworkRequest(QUrl(url)))
            reply.finished.connect(lambda r=reply, u=url: self._done(r, u))
        return None

    def _done(self, reply: QNetworkReply, url: str) -> None:
        pixmap = QPixmap()
        if reply.error() == QNetworkReply.NoError and pixmap.loadFromData(reply.readAll()):
            self.images[url] = pixmap
        reply.deleteLater()
        for listener in list(self._listeners):
            listener.update()


_EMOTES = _Emotes()


class ChatPreview(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setMinimumSize(260, 320)
        self.settings: Dict[str, Any] = {}
        self.messages: List[Dict[str, Any]] = []
        self.sample = True

    def sizeHint(self) -> QSize:  # noqa: N802 - Qt API
        return QSize(420, 600)

    def set_state(self, settings: Dict[str, Any], messages: List[Dict[str, Any]]) -> None:
        self.settings = settings
        fade = int(settings.get("chat-fade-seconds", 45) or 0)
        live = tc.visible(messages, settings)
        if fade > 0:
            live = [m for m in live if time.time() - m["time"] < fade]
        self.sample = not live
        self.messages = tc.visible(sample_messages(), settings) if self.sample else live
        self.update()

    # --- layout of one message ---------------------------------------------------------
    def _layout(self, message: Dict[str, Any], width: float, fonts: Tuple[QFont, QFont]) -> Tuple[List[Tuple], float]:
        """Returns ([(kind, x, y, payload, color, w)], height) for a bubble whose text
        area is `width` wide. kind is "name", "text" or "emote" (payload: url)."""
        name_font, text_font = fonts
        metrics = QFontMetricsF(text_font)
        name_metrics = QFontMetricsF(name_font)
        line_h = metrics.height() * 1.05
        emote_h = metrics.height() * 1.25
        runs: List[Tuple] = []
        x, y = 0.0, 0.0
        tokens: List[Tuple[str, str, Optional[Dict[str, Any]]]] = []
        name_text = message["name"] + (" " if message.get("action") else ": ")
        tokens.append(("name", name_text, None))
        for fragment in message["fragments"]:
            if fragment["type"] == "emote":
                tokens.append(("emote", fragment["text"], fragment))
            else:
                for word in fragment["text"].split(" "):
                    tokens.append(("text", word, None))
                    tokens.append(("text", " ", None))
                tokens.pop()
        last_emote: Optional[Tuple] = None
        for kind, text, fragment in tokens:
            if kind == "emote":
                emote_w = emote_h * float(fragment.get("ratio") or 1)
                if fragment.get("zero_width") and last_emote is not None:
                    # On top of the emote before it, centered, taking no room.
                    _, ex, ey, _, _, ew = last_emote
                    runs.append(("emote", ex + (ew - emote_w) / 2, ey, fragment["url"], None, emote_w))
                    continue
                advance = emote_w + 2
            else:
                advance = (name_metrics if kind == "name" else metrics).horizontalAdvance(text)
            if x + advance > width and x > 0 and text != " ":
                x, y = 0.0, y + line_h
            if text == " " and x == 0:
                continue
            if kind != "emote" and text.strip():
                last_emote = None
            if kind == "text" and advance > width:  # one very long word: break it
                chunk = ""
                for char in text:
                    if x + metrics.horizontalAdvance(chunk + char) > width and chunk:
                        runs.append(("text", x, y, chunk, None, metrics.horizontalAdvance(chunk)))
                        x, y, chunk = 0.0, y + line_h, ""
                    chunk += char
                runs.append(("text", x, y, chunk, None, metrics.horizontalAdvance(chunk)))
                x += metrics.horizontalAdvance(chunk)
                continue
            if kind == "emote":
                last_emote = ("emote", x, y, fragment["url"], None, advance - 2)
                runs.append(last_emote)
            else:
                runs.append((kind, x, y, text, message["color"] if kind == "name" else None, advance))
            x += advance
        return runs, y + line_h

    # --- painting ------------------------------------------------------------------------
    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.SmoothPixmapTransform)
        area = QRectF(self.rect()).adjusted(0, 0, 0, -22)
        scale = min(area.width() / SOURCE_W, area.height() / SOURCE_H)
        source = QRectF(0, 0, SOURCE_W * scale, SOURCE_H * scale)
        source.moveCenter(area.center())
        # What the stream looks like behind the transparent overlay.
        p.setPen(QPen(theme.color(theme.BORDER_STRONG), 1))
        gradient = QLinearGradient(source.topLeft(), source.bottomRight())
        gradient.setColorAt(0, theme.color("#2A3040"))
        gradient.setColorAt(1, theme.color("#1C2029"))
        p.setBrush(gradient)
        p.drawRoundedRect(source, 10, 10)
        p.setPen(Qt.NoPen)
        p.setBrush(theme.color(theme.TEXT, 0.05))
        step = 16
        x = source.left() + step / 2
        while x < source.right():
            y = source.top() + step / 2
            while y < source.bottom():
                p.drawEllipse(QRectF(x - 0.9, y - 0.9, 1.8, 1.8))
                y += step
            x += step
        p.setPen(theme.color(theme.FAINT))
        p.setFont(theme.font(8))
        caption = f"{SOURCE_W} × {SOURCE_H}"
        p.drawText(QRectF(source.left(), source.bottom() + 4, source.width(), 18), Qt.AlignCenter, caption)

        font_px = max(10, int(self.settings.get("chat-font-size", 20) or 20)) * scale
        name_font = theme.font(9, QFont.ExtraBold)
        name_font.setPixelSize(max(6, round(font_px)))
        text_font = theme.font(9, QFont.DemiBold)
        text_font.setPixelSize(max(6, round(font_px)))
        alpha = max(0, min(100, int(self.settings.get("chat-bg-opacity", 72)))) / 100
        limit = max(1, int(self.settings.get("chat-max", 12) or 12))

        p.save()
        p.setClipRect(source.adjusted(1, 1, -1, -1))
        pad_x, pad_y, gap, edge = 12 * scale, 8 * scale, 8 * scale, 12 * scale
        inner = source.width() - 2 * edge - 2 * pad_x
        bottom = source.bottom() - edge
        for message in reversed(self.messages[-limit:]):
            runs, text_h = self._layout(message, inner, (name_font, text_font))
            used = max((r[1] + r[5] for r in runs), default=0)
            bubble = QRectF(source.left() + edge, bottom - text_h - 2 * pad_y, min(inner, used) + 2 * pad_x, text_h + 2 * pad_y)
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(13, 14, 18, round(alpha * 255)))
            p.drawRoundedRect(bubble, 12 * scale, 12 * scale)
            metrics = QFontMetricsF(text_font)
            for kind, rx, ry, payload, color, run_w in runs:
                left, top = bubble.left() + pad_x + rx, bubble.top() + pad_y + ry
                if kind == "emote":
                    size = metrics.height() * 1.25
                    pixmap = _EMOTES.get(payload, self)
                    target = QRectF(left, top + (metrics.height() * 1.05 - size) / 2, run_w, size)
                    if pixmap is not None:
                        p.drawPixmap(target, pixmap, QRectF(pixmap.rect()))
                    continue
                font = name_font if kind == "name" else text_font
                p.setFont(font)
                p.setPen(QColor(0, 0, 0, 150))
                p.drawText(QRectF(left, top + 1, 2000, metrics.height() * 1.05), Qt.AlignLeft | Qt.AlignTop, payload)
                p.setPen(QColor(color) if color else QColor("#FFFFFF"))
                p.drawText(QRectF(left, top, 2000, metrics.height() * 1.05), Qt.AlignLeft | Qt.AlignTop, payload)
            bottom = bubble.top() - gap
            if bottom < source.top():
                break
        p.restore()
