"""Twitch chat, read anonymously over IRC (no login, no API keys).

Messages keep their display name, name color and emote positions; messages
removed by moderators (CLEARMSG / CLEARCHAT) are removed here too, so the
overlay never keeps showing them."""
import collections
import random
import socket
import ssl
import threading
import time
from typing import Any, Callable, Deque, Dict, List, Optional

from app import features
from app.modules import logging_manager as logm
from app.modules.seventv import apply as apply_7tv, seventv

_LOGGER = logm.get_logger(__name__)

HOST = "irc.chat.twitch.tv"
PORT = 6697
HISTORY = 100
EMOTE_URL = "https://static-cdn.jtvnw.net/emoticons/v2/{id}/default/dark/2.0"
_DEFAULT_COLORS = ["#FF6B6B", "#C8F65A", "#5AC8FA", "#FFB547", "#B58CFF", "#FF7AC6", "#4CD9A0", "#F5D547"]


def _unescape(value: str) -> str:
    return (value.replace("\\s", " ").replace("\\:", ";").replace("\\r", "\r").replace("\\n", "\n")
            .replace("\\\\", "\\"))


def parse_line(line: str) -> Dict[str, Any]:
    """IRCv3 line -> {tags, prefix, command, params, trailing}."""
    tags: Dict[str, str] = {}
    rest = line
    if rest.startswith("@"):
        raw, rest = rest[1:].split(" ", 1)
        for pair in raw.split(";"):
            key, _, value = pair.partition("=")
            tags[key] = _unescape(value)
    prefix = ""
    if rest.startswith(":"):
        prefix, rest = rest[1:].split(" ", 1)
    trailing = ""
    if " :" in rest:
        rest, trailing = rest.split(" :", 1)
    parts = rest.split()
    return {"tags": tags, "prefix": prefix, "command": parts[0] if parts else "", "params": parts[1:], "trailing": trailing}


def readable(color: str, minimum: float = 0.45) -> str:
    """Lighten name colors that would vanish on the dark message background."""
    try:
        r, g, b = (int(color.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4))
    except ValueError:
        return color
    luminance = (0.2126 * r + 0.7152 * g + 0.0722 * b) / 255
    if luminance >= minimum:
        return color
    mix = (minimum - luminance) / (1 - luminance) if luminance < 1 else 0
    r, g, b = (round(c + (255 - c) * mix) for c in (r, g, b))
    return f"#{r:02X}{g:02X}{b:02X}"


def _name_color(name: str, color: str) -> str:
    if color:
        return readable(color)
    return _DEFAULT_COLORS[sum(map(ord, name)) % len(_DEFAULT_COLORS)]


def build_fragments(text: str, emotes_tag: str) -> List[Dict[str, str]]:
    """Split text into text and emote fragments using Twitch's character ranges."""
    ranges = []
    for chunk in filter(None, emotes_tag.split("/")):
        emote_id, _, positions = chunk.partition(":")
        for position in positions.split(","):
            start, _, end = position.partition("-")
            if start.isdigit() and end.isdigit():
                ranges.append((int(start), int(end), emote_id))
    ranges.sort()
    fragments: List[Dict[str, str]] = []
    cursor = 0
    for start, end, emote_id in ranges:
        if start < cursor or end >= len(text):
            continue
        if start > cursor:
            fragments.append({"type": "text", "text": text[cursor:start]})
        fragments.append({"type": "emote", "text": text[start:end + 1], "url": EMOTE_URL.format(id=emote_id)})
        cursor = end + 1
    if cursor < len(text):
        fragments.append({"type": "text", "text": text[cursor:]})
    return fragments


def message_from(parsed: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    if parsed["command"] != "PRIVMSG":
        return None
    tags = parsed["tags"]
    login = parsed["prefix"].split("!", 1)[0]
    name = tags.get("display-name") or login
    text = parsed["trailing"]
    action = text.startswith("\x01ACTION ") and text.endswith("\x01")
    if action:
        text = text[8:-1]
    return {
        "id": tags.get("id") or f"{time.time():.6f}",
        "user": login,
        "name": name,
        "color": _name_color(name, tags.get("color", "")),
        "text": text,
        "action": action,
        "fragments": build_fragments(text, tags.get("emotes", "") if not action else ""),
        "time": time.time(),
    }


def hidden_users(text: str) -> set:
    return {name.strip().lstrip("@").lower() for name in (text or "").replace(";", ",").split(",") if name.strip()}


def visible(messages: List[Dict[str, Any]], settings: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Messages the overlay and the panel show: without bots the streamer
    listed and, if asked, without !commands."""
    hidden = hidden_users(settings.get("chat-hidden-users", ""))
    commands = bool(settings.get("chat-hide-commands"))
    kept = [
        m for m in messages
        if m["user"].lower() not in hidden and m["name"].lower() not in hidden
        and not (commands and m["text"].lstrip().startswith("!"))
    ]
    if settings.get("chat-7tv", True):
        emotes = seventv.emotes()
        kept = [apply_7tv(m, emotes) for m in kept]
    return kept


class TwitchChat:
    def __init__(self) -> None:
        self.channel = ""
        self.room_id: Optional[str] = None
        self.status = "off"  # off | connecting | connected | error
        self.error = ""
        self.messages: Deque[Dict[str, Any]] = collections.deque(maxlen=HISTORY)
        self.revision = 0
        self._lock = threading.Lock()
        self._thread: Optional[threading.Thread] = None
        self._stop = threading.Event()
        self._socket: Optional[socket.socket] = None
        self._listeners: List[Callable[[], None]] = []

    def on_change(self, callback: Callable[[], None]) -> None:
        self._listeners.append(callback)

    def _changed(self) -> None:
        self.revision += 1
        for callback in list(self._listeners):
            try:
                callback()
            except Exception:
                _LOGGER.exception("Chat listener failed")

    # --- control -------------------------------------------------------------------
    def start(self, channel: str) -> None:
        channel = channel.strip().lstrip("#").lower()
        if channel == self.channel and self._thread and self._thread.is_alive():
            return
        self.stop()
        if not channel:
            return
        self.channel = channel
        self.room_id = None
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name="twitch-chat", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        sock = self._socket
        if sock is not None:
            try:
                sock.close()
            except OSError:
                pass
        if self._thread is not None:
            self._thread.join(2.0)
        self._thread = None
        self._socket = None
        if self.status != "off":
            self.status = "off"
            self._changed()

    def _dispatch(self, parsed: Dict[str, Any]) -> None:
        if parsed["command"] not in ("PRIVMSG", "USERNOTICE"):
            return
        if not features.STUDIO:  # chat triggers drive Studio inputs
            return
        from app.studio.chat_triggers import event_from, triggers

        event = event_from(parsed)
        if event is not None:
            try:
                triggers.handle(event)
            except Exception:
                _LOGGER.exception("Chat trigger failed")

    def snapshot(self, limit: int = HISTORY) -> List[Dict[str, Any]]:
        with self._lock:
            return list(self.messages)[-limit:]

    # --- connection ------------------------------------------------------------------
    def _run(self) -> None:
        delay = 2.0
        while not self._stop.is_set():
            self.status, self.error = "connecting", ""
            self._changed()
            try:
                self._session()
                delay = 2.0
            except OSError as error:
                if self._stop.is_set():
                    break
                self.status, self.error = "error", str(error)
                _LOGGER.warning("Twitch chat connection failed: %s", error)
                self._changed()
            if self._stop.wait(delay):
                break
            delay = min(delay * 2, 60.0)

    def _session(self) -> None:
        context = ssl.create_default_context()
        try:
            import certifi

            context.load_verify_locations(cafile=certifi.where())
        except Exception:
            pass
        raw = socket.create_connection((HOST, PORT), timeout=15)
        sock = context.wrap_socket(raw, server_hostname=HOST)
        self._socket = sock
        nick = f"justinfan{random.randint(10000, 99999)}"
        for line in ("CAP REQ :twitch.tv/tags twitch.tv/commands", "PASS SCHMOOPIIE", f"NICK {nick}", f"JOIN #{self.channel}"):
            sock.sendall((line + "\r\n").encode("utf-8"))
        sock.settimeout(360)  # Twitch pings every ~5 minutes
        buffer = b""
        while not self._stop.is_set():
            data = sock.recv(65536)
            if not data:
                raise OSError("connection closed")
            buffer += data
            while b"\r\n" in buffer:
                line, buffer = buffer.split(b"\r\n", 1)
                self._handle(sock, line.decode("utf-8", "replace"))

    def _handle(self, sock: socket.socket, line: str) -> None:
        if not line:
            return
        if line.startswith("PING"):
            sock.sendall(("PONG" + line[4:] + "\r\n").encode("utf-8"))
            return
        parsed = parse_line(line)
        command = parsed["command"]
        if command == "ROOMSTATE" and parsed["tags"].get("room-id"):
            self.room_id = parsed["tags"]["room-id"]
            seventv.load(self.room_id)
        if command == "JOIN" or (command == "ROOMSTATE"):
            if self.status != "connected":
                self.status, self.error = "connected", ""
                _LOGGER.info("Twitch chat connected: #%s", self.channel)
                self._changed()
            return
        if command == "RECONNECT":
            raise OSError("server asked to reconnect")
        if command == "NOTICE" and "login" in parsed["trailing"].lower():
            raise OSError(parsed["trailing"])
        self._dispatch(parsed)
        message = message_from(parsed)
        if message is not None:
            if self.room_id:
                seventv.load(self.room_id)  # refreshes now and then, so new channel emotes appear
            with self._lock:
                self.messages.append(message)
            self._changed()
            return
        if command == "CLEARMSG":
            target = parsed["tags"].get("target-msg-id")
            with self._lock:
                self.messages = collections.deque((m for m in self.messages if m["id"] != target), maxlen=HISTORY)
            self._changed()
        elif command == "CLEARCHAT":
            user = parsed["trailing"].lower()
            with self._lock:
                if user:
                    kept = (m for m in self.messages if m["user"].lower() != user)
                else:
                    kept = ()
                self.messages = collections.deque(kept, maxlen=HISTORY)
            self._changed()


chat = TwitchChat()
seventv.on_change(chat._changed)  # sockets resend the chat with the new emotes
