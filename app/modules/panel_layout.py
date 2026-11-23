"""Layout of the web control panel: pages with widgets placed on a grid.

settings["panel-layout"] is None (automatic: generated from what the active
avatar offers) or {"pages": [page, ...]} where

    page = {"name": str, "cols": 2..8, "items": [item, ...]}
    item = {"id", "type", "x", "y", "w", "h", ...}   position and size in cells

Item types and their own fields:

    button    {"action": "param" | "sequence" | "profile" | "sound-profile", "target", "label", "color"}
    slider    {"target": <number param id>, "label", "color"}
    label     {"text", "align": "left" | "center"}
    chat      Twitch chat
    profiles  image profile switcher
    sounds    sound profile switcher
    meter     microphone level
    avatar    the live avatar, as OBS shows it

Buttons and sliders point at parameter ids, so one layout serves every avatar:
whatever the active avatar does not have leaves its cells empty. resolve()
turns a layout into concrete widgets for the page."""
import copy
import secrets
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

ITEM_TYPES = ("button", "slider", "label", "chat", "profiles", "sounds", "meter", "avatar")
BUTTON_ACTIONS = ("param", "sequence", "profile", "sound-profile")
COLOR_NAMES = {"#C8F65A": "lime", "#FF6B6B": "red", "#FFB547": "orange", "#F5D547": "yellow",
               "#5AC8FA": "blue", "#B58CFF": "purple", "#FF7AC6": "pink"}
COLORS = ("",) + tuple(COLOR_NAMES)
MIN_COLS, MAX_COLS, DEFAULT_COLS = 2, 8, 4
MAX_ROWS = 60
MAX_PAGES = 12
MAX_ITEMS = 120

# Size a widget gets when it is dropped on the grid (w, h); 0 means "all columns".
DEFAULT_SIZES: Dict[str, Tuple[int, int]] = {
    "button": (1, 1), "slider": (0, 1), "label": (0, 1), "chat": (0, 5),
    "profiles": (0, 1), "sounds": (0, 1), "meter": (2, 1), "avatar": (2, 2),
}
_FIELDS: Dict[str, Dict[str, Any]] = {
    "button": {"action": "param", "target": "", "label": "", "color": ""},
    "slider": {"target": "", "label": "", "color": ""},
    "label": {"text": "", "align": "left"},
    "chat": {},
    "profiles": {},
    "sounds": {},
    "meter": {},
    "avatar": {},
}


def new_id() -> str:
    return secrets.token_hex(4)


def _int(value: Any, default: int, low: int, high: int) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        number = default
    return max(low, min(high, number))


def default_size(kind: str, cols: int) -> Tuple[int, int]:
    w, h = DEFAULT_SIZES[kind]
    return (cols if w == 0 else min(w, cols)), h


def make_item(kind: str, cols: int, **fields: Any) -> Dict[str, Any]:
    w, h = default_size(kind, cols)
    item = {"id": new_id(), "type": kind, "x": 0, "y": 0, "w": w, "h": h, **copy.deepcopy(_FIELDS[kind])}
    item.update(fields)
    return item


# --- geometry ----------------------------------------------------------------------------
def cells(item: Dict[str, Any]) -> Set[Tuple[int, int]]:
    return {(x, y) for x in range(item["x"], item["x"] + item["w"]) for y in range(item["y"], item["y"] + item["h"])}


def fits(items: List[Dict[str, Any]], cols: int, x: int, y: int, w: int, h: int, ignore: Optional[str] = None) -> bool:
    if x < 0 or y < 0 or w < 1 or h < 1 or x + w > cols or y + h > MAX_ROWS:
        return False
    wanted = {(cx, cy) for cx in range(x, x + w) for cy in range(y, y + h)}
    return not any(wanted & cells(other) for other in items if other["id"] != ignore)


def free_spot(items: List[Dict[str, Any]], cols: int, w: int, h: int, start: Tuple[int, int] = (0, 0)) -> Optional[Tuple[int, int]]:
    """First place in reading order (from `start`) where a w x h widget fits."""
    w = min(w, cols)
    for y in range(start[1], MAX_ROWS):
        for x in range(start[0] if y == start[1] else 0, cols - w + 1):
            if fits(items, cols, x, y, w, h):
                return x, y
    return None


def rows_used(items: List[Dict[str, Any]]) -> int:
    return max((i["y"] + i["h"] for i in items), default=0)


# --- normalization -----------------------------------------------------------------------
def normalize_item(item: Any, cols: int) -> Optional[Dict[str, Any]]:
    if not isinstance(item, dict) or item.get("type") not in ITEM_TYPES:
        return None
    kind = item["type"]
    w, h = default_size(kind, cols)
    result: Dict[str, Any] = {
        "id": str(item.get("id") or new_id()),
        "type": kind,
        "w": _int(item.get("w"), w, 1, cols),
        "h": _int(item.get("h"), h, 1, MAX_ROWS),
    }
    # Items without a position are placed later, in order.
    result["x"] = _int(item["x"], 0, 0, cols - result["w"]) if "x" in item else None
    result["y"] = _int(item["y"], 0, 0, MAX_ROWS - result["h"]) if "y" in item else None
    for key, default in _FIELDS[kind].items():
        value = item.get(key, default)
        result[key] = value if key == "target" and isinstance(value, int) else str(value or "")
    if kind == "button" and result["action"] not in BUTTON_ACTIONS:
        return None
    if kind in ("button", "slider") and result["target"] in ("", None):
        return None
    if "color" in result and result["color"] not in COLORS:
        result["color"] = ""
    if kind == "label" and result["align"] not in ("left", "center"):
        result["align"] = "left"
    return result


def normalize_page(page: Any) -> Dict[str, Any]:
    page = page if isinstance(page, dict) else {}
    cols = _int(page.get("cols"), DEFAULT_COLS, MIN_COLS, MAX_COLS)
    placed: List[Dict[str, Any]] = []
    pending: List[Dict[str, Any]] = []
    seen_ids = set()
    for raw in (page.get("items") or [])[:MAX_ITEMS]:
        item = normalize_item(raw, cols)
        if item is None:
            continue
        if item["id"] in seen_ids:
            item["id"] = new_id()
        seen_ids.add(item["id"])
        if item["x"] is not None and item["y"] is not None and fits(placed, cols, item["x"], item["y"], item["w"], item["h"]):
            placed.append(item)
        else:
            pending.append(item)
    for item in pending:  # unplaced or overlapping: next free spot
        spot = free_spot(placed, cols, item["w"], item["h"])
        if spot is not None:
            item["x"], item["y"] = spot
            placed.append(item)
    return {"name": str(page.get("name") or ""), "cols": cols, "items": placed}


def normalize(layout: Any) -> Optional[Dict[str, Any]]:
    """None stays None (automatic); anything else becomes a valid layout."""
    if layout is None:
        return None
    pages = layout.get("pages") if isinstance(layout, dict) else None
    pages = [normalize_page(p) for p in (pages or [])[:MAX_PAGES]]
    return {"pages": pages or [normalize_page({})]}


# --- the automatic layout ------------------------------------------------------------------
def generate(context: Dict[str, Any], t: Callable[[str], str], cols: int = DEFAULT_COLS) -> Dict[str, Any]:
    """The layout used until the user makes their own: every manual parameter
    and sequence of the active avatar, the profiles and, if on, the chat."""
    items: List[Dict[str, Any]] = []

    def place(kind: str, **fields: Any) -> None:
        item = make_item(kind, cols, **fields)
        spot = free_spot(items, cols, item["w"], item["h"])
        if spot is not None:
            item["x"], item["y"] = spot
            items.append(item)

    manual = [p for p in context["params"] if p.get("manual")]
    for p in manual:
        if p["type"] == "trigger":
            place("button", action="param", target=p["id"])
    for s in context["sequences"]:
        place("button", action="sequence", target=s["id"])
    for p in manual:
        if p["type"] == "bool":
            place("button", action="param", target=p["id"])
    for p in manual:
        if p["type"] == "number":
            place("slider", target=p["id"])
    if not items:
        # Nothing to press on this avatar: show it live with the microphone level.
        place("avatar")
        place("meter")
    if len(context["profiles"]) > 1:
        place("profiles")
    if len(context["sound_profiles"]) > 1:
        place("sounds")
    pages = [{"name": "", "cols": cols, "items": items}]
    if context.get("chat_enabled"):
        chat = make_item("chat", cols, h=6)
        pages.append({"name": t("panel.chat"), "cols": cols, "items": [chat]})
    return {"pages": pages}


# --- resolving into widgets -----------------------------------------------------------------
def _widget(item: Dict[str, Any], context: Dict[str, Any], lookup: Dict[str, Dict[Any, Dict[str, Any]]],
            t: Callable[[str], str]) -> Optional[Dict[str, Any]]:
    kind = item["type"]
    base = {"id": item["id"], "x": item["x"], "y": item["y"], "w": item["w"], "h": item["h"]}
    if kind == "button":
        action, target = item["action"], item["target"]
        if action == "param":
            param = lookup["params"].get(target)
            if param is None or not param.get("manual") or param["type"] == "number":
                return None
            name = param.get("name") or param["id"]
            sub = param.get("hotkey") or t("panel.toggle" if param["type"] == "bool" else "panel.reaction")
            action = "toggle" if param["type"] == "bool" else "trigger"
        elif action == "sequence":
            sequence = lookup["sequences"].get(target)
            if sequence is None:
                return None
            name, sub = sequence["name"], t("panel.sequence")
        else:
            source = lookup["profiles" if action == "profile" else "sound_profiles"]
            try:
                profile = source.get(int(target))
            except (TypeError, ValueError):
                profile = None
            if profile is None:
                return None
            target = profile["id"]
            name, sub = profile["name"], t("panel.avatar" if action == "profile" else "panel.sound")
            action = "profile" if action == "profile" else "sound"
        return {**base, "kind": "button", "action": action, "target": target, "label": item["label"] or name,
                "sub": sub, "color": item["color"]}
    if kind == "slider":
        param = lookup["params"].get(item["target"])
        if param is None or param["type"] != "number" or not param.get("manual"):
            return None
        return {**base, "kind": "slider", "target": param["id"], "label": item["label"] or param.get("name") or param["id"],
                "min": param.get("min", 0), "max": param.get("max", 1), "color": item["color"]}
    if kind == "label":
        return {**base, "kind": "label", "text": item["text"], "align": item["align"]} if item["text"] else None
    if kind == "chat":
        return {**base, "kind": "chat"} if context.get("chat_enabled") else None
    if kind == "profiles":
        return {**base, "kind": "chips", "action": "profile", "title": t("panel.avatar"), "items": context["profiles"]}
    if kind == "sounds":
        return {**base, "kind": "chips", "action": "sound", "title": t("panel.sound"), "items": context["sound_profiles"]}
    if kind == "avatar":
        return {**base, "kind": "avatar"}
    return {**base, "kind": "meter"}


def resolve(layout: Optional[Dict[str, Any]], context: Dict[str, Any], t: Callable[[str], str]) -> Dict[str, Any]:
    """context: params / sequences / profiles / sound_profiles / chat_enabled of
    the panel state. Returns {"pages": [{"name", "cols", "rows", "widgets"}], "auto"}."""
    auto = layout is None
    layout = generate(context, t) if auto else normalize(layout)
    lookup = {
        "params": {p["id"]: p for p in context["params"]},
        "sequences": {s["id"]: s for s in context["sequences"]},
        "profiles": {p["id"]: p for p in context["profiles"]},
        "sound_profiles": {p["id"]: p for p in context["sound_profiles"]},
    }
    pages = []
    for page in layout["pages"]:
        widgets = [w for w in (_widget(i, context, lookup, t) for i in page["items"]) if w is not None]
        pages.append({"name": page["name"], "cols": page["cols"], "rows": rows_used(page["items"]), "widgets": widgets})
    return {"pages": pages, "auto": auto}


def uses(layout: Dict[str, Any], kind: str) -> bool:
    return any(w["kind"] == kind for page in layout["pages"] for w in page["widgets"])
