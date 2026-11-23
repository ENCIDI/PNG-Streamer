"""7TV emotes for the Twitch chat: the global set and the channel's own set.

The channel's Twitch id comes from the chat itself (the ROOMSTATE room-id tag),
so no login or API key is needed. Emotes are matched by whole words when
messages are sent out, so turning 7TV off or a set that loads late applies to
messages already on screen. Zero-width emotes (RainTime, PETPET…) are drawn on
top of the emote before them."""
import json
import threading
import time
import urllib.request
from typing import Any, Callable, Dict, List, Optional

from app.modules import logging_manager as logm

_LOGGER = logm.get_logger(__name__)

GLOBAL_URL = "https://7tv.io/v3/emote-sets/global"
CHANNEL_URL = "https://7tv.io/v3/users/twitch/{room_id}"
REFRESH_SECONDS = 10 * 60
_ZERO_WIDTH_SET_FLAG = 1        # flag on the emote inside a set
_ZERO_WIDTH_EMOTE_FLAG = 1 << 8  # flag on the emote itself


def _ssl_context():
    from app.modules import update_manager as um

    return um._ssl_context()


def _fetch(url: str) -> Optional[Dict[str, Any]]:
    request = urllib.request.Request(url, headers={"User-Agent": "PNGStreamer"})
    try:
        with urllib.request.urlopen(request, context=_ssl_context(), timeout=15) as response:
            return json.load(response)
    except urllib.error.HTTPError as error:
        if error.code != 404:  # 404: the channel has no 7TV account
            _LOGGER.warning("7TV request failed: %s %s", url, error)
    except Exception as error:  # network, TLS, bad JSON
        _LOGGER.warning("7TV request failed: %s %s", url, error)
    return None


def parse_set(emotes: Any) -> Dict[str, Dict[str, Any]]:
    """7TV emote list -> {name: {"url", "zero_width", "ratio"}}."""
    result: Dict[str, Dict[str, Any]] = {}
    for emote in emotes or []:
        try:
            data = emote.get("data") or {}
            host = data["host"]
            files = [f for f in host.get("files", []) if f.get("format") == "WEBP"]
            chosen = next((f for f in files if f["name"].startswith("2x")), files[0] if files else None)
            if chosen is None:
                continue
            ratio = chosen.get("width", 1) / max(1, chosen.get("height", 1))
            result[emote["name"]] = {
                "url": "https:" + host["url"] + "/" + chosen["name"] if host["url"].startswith("//") else host["url"] + "/" + chosen["name"],
                "zero_width": bool(emote.get("flags", 0) & _ZERO_WIDTH_SET_FLAG or data.get("flags", 0) & _ZERO_WIDTH_EMOTE_FLAG),
                "ratio": round(ratio, 3),
            }
        except (KeyError, TypeError, AttributeError):
            continue
    return result


def apply(message: Dict[str, Any], emotes: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    """Split the text fragments of a chat message into words and 7TV emotes."""
    if not emotes:
        return message
    fragments: List[Dict[str, Any]] = []
    changed = False
    for fragment in message["fragments"]:
        if fragment["type"] != "text":
            fragments.append(fragment)
            continue
        pending = ""
        for index, word in enumerate(fragment["text"].split(" ")):
            separator = " " if index else ""
            emote = emotes.get(word) if word else None
            if emote is None:
                pending += separator + word
                continue
            changed = True
            pending += separator
            if pending:
                fragments.append({"type": "text", "text": pending})
            pending = ""
            fragments.append({"type": "emote", "text": word, "url": emote["url"], "ratio": emote["ratio"],
                              "zero_width": emote["zero_width"], "provider": "7tv"})
        if pending:
            fragments.append({"type": "text", "text": pending})
    if not changed:
        return message
    return {**message, "fragments": fragments}


class SevenTV:
    def __init__(self) -> None:
        self.room_id: Optional[str] = None
        self.global_emotes: Dict[str, Dict[str, Any]] = {}
        self.channel_emotes: Dict[str, Dict[str, Any]] = {}
        self.loaded_at = 0.0
        self.revision = 0
        self._lock = threading.Lock()
        self._loading = False
        self._listeners: List[Callable[[], None]] = []

    def on_change(self, callback: Callable[[], None]) -> None:
        self._listeners.append(callback)

    def emotes(self) -> Dict[str, Dict[str, Any]]:
        """Channel emotes win over global ones with the same name."""
        with self._lock:
            return {**self.global_emotes, **self.channel_emotes}

    def count(self) -> int:
        return len(self.emotes())

    def load(self, room_id: Optional[str], force: bool = False) -> None:
        """Fetch (in the background) for the channel; cheap to call often."""
        fresh = time.monotonic() - self.loaded_at < REFRESH_SECONDS
        if self._loading or (room_id == self.room_id and fresh and not force):
            return
        if room_id != self.room_id:
            with self._lock:
                self.channel_emotes = {}
        self.room_id = room_id
        self._loading = True
        threading.Thread(target=self._load, args=(room_id,), name="7tv", daemon=True).start()

    def _load(self, room_id: Optional[str]) -> None:
        try:
            global_set = _fetch(GLOBAL_URL)
            channel = _fetch(CHANNEL_URL.format(room_id=room_id)) if room_id else None
            with self._lock:
                if global_set is not None:
                    self.global_emotes = parse_set(global_set.get("emotes"))
                if room_id == self.room_id:
                    self.channel_emotes = parse_set(((channel or {}).get("emote_set") or {}).get("emotes"))
            self.loaded_at = time.monotonic()
            _LOGGER.info("7TV emotes: %d global, %d channel", len(self.global_emotes), len(self.channel_emotes))
        finally:
            self._loading = False
        self.revision += 1
        for callback in list(self._listeners):
            try:
                callback()
            except Exception:
                _LOGGER.exception("7TV listener failed")


seventv = SevenTV()
