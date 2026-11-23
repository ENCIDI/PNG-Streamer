"""Where the avatar sits inside the OBS browser source.

    profile["output"] = {anchor, scale, x, y, flip}

x and y are offsets in percent of the source size."""
import copy
from typing import Any, Dict

ANCHORS = ("center", "bottom", "bottom-left", "bottom-right", "top", "top-left", "top-right", "left", "right")
OUTPUT_DEFAULTS: Dict[str, Any] = {"anchor": "bottom", "scale": 1.0, "x": 0.0, "y": 0.0, "flip": False}
ANCHOR_POINTS = {
    "center": (0.5, 0.5), "bottom": (0.5, 1.0), "bottom-left": (0.0, 1.0), "bottom-right": (1.0, 1.0),
    "top": (0.5, 0.0), "top-left": (0.0, 0.0), "top-right": (1.0, 0.0), "left": (0.0, 0.5), "right": (1.0, 0.5),
}


def num(value: Any, default: float, low: float, high: float) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    if number != number:
        return default
    return min(max(number, low), high)


def merge(defaults: Dict[str, Any], stored: Any) -> Dict[str, Any]:
    result = copy.deepcopy(defaults)
    if isinstance(stored, dict):
        for key, value in stored.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = {**result[key], **value}
            elif key in result:
                result[key] = copy.deepcopy(value)
    return result


def normalize_output(stored: Any) -> Dict[str, Any]:
    output = merge(OUTPUT_DEFAULTS, stored)
    if output["anchor"] not in ANCHORS:
        output["anchor"] = "bottom"
    output["scale"] = num(output["scale"], 1.0, 0.1, 4.0)
    output["x"] = num(output["x"], 0.0, -100.0, 100.0)
    output["y"] = num(output["y"], 0.0, -100.0, 100.0)
    output["flip"] = bool(output["flip"])
    return output


def place(output: Dict[str, Any], content_w: float, content_h: float, box_w: float, box_h: float):
    """Where the avatar goes inside the OBS source: (x, y, w, h). The same math
    runs in the browser widget (web_manager) — keep them in sync."""
    output = normalize_output(output)
    content_w, content_h = max(1.0, float(content_w)), max(1.0, float(content_h))
    fit = min(box_w / content_w, box_h / content_h) * output["scale"]
    w, h = content_w * fit, content_h * fit
    ax, ay = ANCHOR_POINTS[output["anchor"]]
    x = ax * (box_w - w) + output["x"] / 100.0 * box_w
    y = ay * (box_h - h) + output["y"] / 100.0 * box_h
    return x, y, w, h
