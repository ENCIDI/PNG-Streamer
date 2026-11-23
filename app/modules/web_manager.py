import asyncio
import base64
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import quote

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse, Response
import uvicorn

from app import features, paths
from app.modules import audio_manager as am, lan, logging_manager as logm, logic_manager as lm, panel_layout, storage_manager as sm
from app.modules.twitch_chat import chat as twitch_chat
from app.modules.output import normalize_output
from app.modules.studio_bridge import service as avatar_service
from app.version import __version__

_LOGGER = logm.get_logger(__name__)


_server_lock = threading.Lock()
_server_thread: Optional[threading.Thread] = None
_server: Optional[uvicorn.Server] = None
_current_port: Optional[int] = None

_SIMPLE_FPS = 30
_AVATAR_FPS = 60

_APP = FastAPI()

_TRANSPARENT_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADElEQVR4nGNgAAAAAgAB5SfUoAAAAABJRU5ErkJggg=="
)


# --- access from the local network -------------------------------------------
_PANEL_ASSETS = paths.RESOURCES_DIR / "assets" / "panel"
_PUBLIC_PANEL_FILES = {"manifest.json", "icon-192.png", "icon-512.png"}


def _request_token(request: Request) -> Optional[str]:
    return request.cookies.get(lan.COOKIE) or request.query_params.get("token")


@_APP.middleware("http")
async def _lan_guard(request: Request, call_next):
    """Requests from this computer pass; other devices need the pairing token
    (the QR link sets it as a cookie)."""
    host = request.client.host if request.client else None
    if lan.is_local(host):
        return await call_next(request)
    if not lan.enabled():
        return Response(status_code=403)
    path = request.url.path
    if path.startswith("/panel/assets/") and path.rsplit("/", 1)[-1] in _PUBLIC_PANEL_FILES or path == "/panel/manifest.json":
        return await call_next(request)
    query_token = request.query_params.get("token")
    if query_token and lan.check_token(query_token) and path == "/panel":
        response = RedirectResponse("/panel", status_code=303)
        response.set_cookie(lan.COOKIE, query_token, max_age=365 * 24 * 3600, httponly=True, samesite="lax")
        return response
    if not lan.check_token(_request_token(request)):
        return HTMLResponse(_panel_denied(), status_code=403)
    return await call_next(request)


def _socket_allowed(websocket: WebSocket) -> bool:
    host = websocket.client.host if websocket.client else None
    if lan.is_local(host):
        return True
    return lan.enabled() and lan.check_token(websocket.cookies.get(lan.COOKIE) or websocket.query_params.get("token"))


def _panel_strings() -> Dict[str, str]:
    from app.ui import i18n

    keys = ("live", "stopped", "reactions", "toggles", "sliders", "avatar", "sound", "chat", "controls", "sequence",
            "reaction", "toggle", "simple_hint", "awake", "tap_awake", "offline", "failed", "denied", "page", "mic", "fullscreen", "exit_fullscreen",
            "avatar_live")
    if features.STUDIO:
        keys += ("no_params",)
    return {key: i18n.t(f"panel.{key}") for key in keys}


def _panel_denied() -> str:
    text = _panel_strings()["denied"]
    return (
        "<!doctype html><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>"
        "<body style='background:#0D0E12;color:#E8EAF0;font:16px system-ui;display:grid;place-items:center;"
        f"height:100vh;margin:0;padding:24px;text-align:center'><p>{text}</p></body>"
    )


class _Feed:
    """An accepted socket the server pushes to. Watches for the client closing
    (reads in the background) and drops clients that stop taking data, e.g. a
    phone that went to sleep without closing the connection."""

    SEND_TIMEOUT = 5.0
    active = 0

    def __init__(self, websocket: WebSocket):
        self.websocket = websocket
        self.last_seen = time.monotonic()
        self._reader = asyncio.ensure_future(self._read())
        _Feed.active += 1

    async def _read(self) -> None:
        try:
            while (await self.websocket.receive())["type"] != "websocket.disconnect":
                self.last_seen = time.monotonic()
        except Exception:
            pass

    @property
    def open(self) -> bool:
        return not self._reader.done()

    def silent_for(self) -> float:
        return time.monotonic() - self.last_seen

    async def send(self, data: Any) -> None:
        await asyncio.wait_for(self.websocket.send_json(data), self.SEND_TIMEOUT)

    async def wait(self, seconds: float) -> None:
        await asyncio.wait({self._reader}, timeout=seconds)

    def close(self) -> None:
        self._reader.cancel()
        _Feed.active -= 1


_FEED_ERRORS = (WebSocketDisconnect, RuntimeError, OSError, asyncio.TimeoutError)
# The panel pings every 10 s; a phone that fell asleep stops pinging without
# closing the connection.
_PANEL_HEARTBEAT_TIMEOUT = 30.0


# --- web control panel ----------------------------------------------------------
@_APP.get("/panel", response_class=HTMLResponse)
def panel_page() -> str:
    import json as _json

    from app.ui import i18n

    html = (_PANEL_ASSETS / "panel.html").read_text(encoding="utf-8")
    return html.replace("__STRINGS__", _json.dumps(_panel_strings(), ensure_ascii=False)).replace("__LANG__", i18n.get_language())


@_APP.get("/panel/manifest.json")
def panel_manifest() -> dict:
    return {
        "name": "PNG Streamer",
        "short_name": "PNG Streamer",
        "start_url": "/panel",
        "display": "standalone",
        "background_color": "#0D0E12",
        "theme_color": "#0D0E12",
        "icons": [
            {"src": "/panel/assets/icon-192.png", "sizes": "192x192", "type": "image/png"},
            {"src": "/panel/assets/icon-512.png", "sizes": "512x512", "type": "image/png"},
        ],
    }


@_APP.get("/panel/assets/{name}")
def panel_asset(name: str) -> Response:
    path = (_PANEL_ASSETS / Path(name).name)
    if not path.is_file() or path.suffix not in (".png", ".webm", ".mp4"):
        return Response(status_code=404)
    return FileResponse(path, headers={"Cache-Control": "max-age=3600"})


def panel_state() -> Dict[str, Any]:
    from app.ui import i18n

    profile = lm.get_active_image_profile() or {}
    settings = sm.load_settings()["settings"]
    doc = avatar_service.doc() if lm.is_advanced(profile) else None
    sound = lm.get_active_sound_profile() or {}
    state = {
        "type": "state",
        "live": is_running(),
        "advanced": lm.is_advanced(profile),
        "profile": profile.get("id"),
        "profile_name": profile.get("name"),
        "sound_profile": sound.get("id"),
        "profiles": [{"id": p["id"], "name": p.get("name") or str(p["id"])} for p in sm.list_profiles()],
        "sound_profiles": [{"id": p["id"], "name": p.get("name") or str(p["id"])} for p in sm.list_sound_profiles()],
        "params": [
            {
                "id": p["id"],
                "name": p.get("name") or p["id"],
                "type": p["type"],
                "min": p.get("min", 0),
                "max": p.get("max", 1),
                "value": p.get("value"),
                "hotkey": p.get("hotkey", ""),
                "manual": p.get("source", "none") in ("none", "chat"),
            }
            for p in avatar_service.params()
        ],
        "sequences": [{"id": s["id"], "name": s.get("name") or s["id"]} for s in (doc or {}).get("sequences", [])],
        "chat_enabled": bool(settings.get("chat-enabled") and settings.get("twitch-channel")),
        "chat_channel": settings.get("twitch-channel", ""),
    }
    layout = panel_layout.resolve(settings.get("panel-layout"), state, i18n.t)
    state["pages"] = layout["pages"]
    state["chat_shown"] = panel_layout.uses(layout, "chat")
    state["meter_shown"] = panel_layout.uses(layout, "meter")
    return state


@_APP.websocket("/panel/ws")
async def panel_socket(websocket: WebSocket) -> None:
    if not _socket_allowed(websocket):
        await websocket.close(code=4403)
        return
    await websocket.accept()
    feed = _Feed(websocket)
    last_state = None
    last_chat = None
    try:
        while feed.open and feed.silent_for() < _PANEL_HEARTBEAT_TIMEOUT:
            state = panel_state()
            if state != last_state:
                await feed.send(state)
                last_state = state
            settings = sm.load_settings()["settings"]
            chat_key = (twitch_chat.revision, settings.get("chat-hide-commands"), settings.get("chat-hidden-users"),
                        settings.get("chat-7tv"))
            if state["chat_shown"] and chat_key != last_chat:
                last_chat = chat_key
                await feed.send({"type": "chat", "messages": _chat_messages(150)})
            if state["meter_shown"]:
                await feed.send({"type": "level", "v": round(am.get_current_volume(), 1)})
            await feed.wait(0.1)
    except _FEED_ERRORS:
        pass
    finally:
        feed.close()


# --- Twitch chat overlay -------------------------------------------------------------
@_APP.get("/chat", response_class=HTMLResponse)
def chat_page() -> str:
    settings = sm.load_settings()["settings"]
    html = (_PANEL_ASSETS / "chat.html").read_text(encoding="utf-8")
    return (
        html.replace("__MAX__", str(max(1, int(settings.get("chat-max", 12) or 12))))
        .replace("__FADE__", str(max(0, int(settings.get("chat-fade-seconds", 45) or 0))))
        .replace("__FONT__", str(max(10, int(settings.get("chat-font-size", 20) or 20))))
        .replace("__BG__", f"{max(0, min(100, int(settings.get('chat-bg-opacity', 72) or 0))) / 100:.2f}")
    )


def _chat_style() -> Dict[str, Any]:
    settings = sm.load_settings()["settings"]
    return {
        "type": "style",
        "max": max(1, int(settings.get("chat-max", 12) or 12)),
        "fade": max(0, int(settings.get("chat-fade-seconds", 45) or 0)),
        "font": max(10, int(settings.get("chat-font-size", 20) or 20)),
        "bg": max(0, min(100, int(settings.get("chat-bg-opacity", 72) or 0))) / 100,
    }


def _chat_messages(limit: int) -> List[Dict[str, Any]]:
    from app.modules.twitch_chat import visible

    return visible(twitch_chat.snapshot(limit * 2), sm.load_settings()["settings"])[-limit:]


@_APP.websocket("/chat/ws")
async def chat_socket(websocket: WebSocket) -> None:
    if not _socket_allowed(websocket):
        await websocket.close(code=4403)
        return
    await websocket.accept()
    feed = _Feed(websocket)
    last = -1
    last_style = None
    last_filter = None
    try:
        while feed.open:
            style = _chat_style()
            if style != last_style:
                await feed.send(style)
                last_style = style
            settings = sm.load_settings()["settings"]
            chat_filter = (settings.get("chat-hide-commands"), settings.get("chat-hidden-users"), settings.get("chat-7tv"))
            if twitch_chat.revision != last or chat_filter != last_filter:
                last, last_filter = twitch_chat.revision, chat_filter
                await feed.send({"type": "chat", "messages": _chat_messages(50)})
            await feed.wait(0.2)
    except _FEED_ERRORS:
        pass
    finally:
        feed.close()


# --- OBS widget --------------------------------------------------------------
@_APP.get("/", response_class=HTMLResponse)
def widget_root() -> str:
    return _WIDGET_HTML


@_APP.get("/widget", response_class=HTMLResponse)
def widget_page() -> str:
    return _WIDGET_HTML


def _output(profile: Dict[str, Any]) -> Dict[str, Any]:
    return normalize_output(profile.get("output"))


def _simple_message(profile: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "type": "simple",
        "output": _output(profile),
        "images": [
            {"name": name, "url": "/images/" + quote(name, safe="")}
            for name in lm.referenced_images(profile)
            if lm.resolve_image_path(name) is not None
        ],
    }


def _scene_revision(avatar_id: Optional[str]) -> int:
    if not avatar_id:
        return 0
    from app.studio import project as pj

    return pj.revision(avatar_id)


def _avatar_message(avatar_id: str) -> Optional[Dict[str, Any]]:
    from app.studio import project as pj

    doc = pj.load(avatar_id)
    if doc is None:
        return None
    return {
        "type": "avatar",
        "canvas": doc["canvas"],
        "assets": [
            {"id": a["id"], "url": f"/avatar/{avatar_id}/assets/{quote(a['file'], safe='')}", "w": a["w"], "h": a["h"]}
            for a in doc["assets"]
        ],
    }


@_APP.websocket("/ws")
async def widget_socket(websocket: WebSocket) -> None:
    """Sends what to preload whenever the avatar changes, then frames: the
    current image for simple profiles (30/s) or the Studio render list (60/s)."""
    if not _socket_allowed(websocket):
        await websocket.close(code=4403)
        return
    await websocket.accept()
    feed = _Feed(websocket)
    last_revision = None
    try:
        while feed.open:
            profile = lm.get_active_image_profile() or {}
            advanced = lm.is_advanced(profile)
            avatar_id = profile.get("avatar") if advanced else None
            revision = (sm.data_revision(), profile.get("id"), _scene_revision(avatar_id))
            if revision != last_revision:
                message = _avatar_message(avatar_id) if advanced else _simple_message(profile)
                if message is not None:
                    message["output"] = _output(profile)
                if message is not None:
                    await feed.send(message)
                last_revision = revision
            if advanced:
                frame = avatar_service.frame()
                if frame is not None:
                    await feed.send({"type": "frame", "t": frame["t"], "items": frame["items"]})
                await feed.wait(1 / _AVATAR_FPS)
            else:
                await feed.send({"type": "state", **lm.compute_state(profile=profile)})
                await feed.wait(1 / _SIMPLE_FPS)
    except _FEED_ERRORS:
        pass
    finally:
        feed.close()


def _allowed_image(name: str) -> Optional[Path]:
    """Only files from the images folder or referenced by a profile are served."""
    path = lm.resolve_image_path(name)
    if path is None:
        return None
    try:
        if path.resolve().is_relative_to(paths.IMAGES_DIR.resolve()):
            return path
    except OSError:
        return None
    if any(name in lm.referenced_images(profile) for profile in sm.list_profiles()):
        return path
    return None


@_APP.get("/images/{name:path}")
def widget_asset(name: str) -> Response:
    path = _allowed_image(name)
    if path is None:
        return Response(status_code=404)
    return FileResponse(path, headers={"Cache-Control": "no-cache"})


@_APP.get("/avatar/{avatar_id}/assets/{name}")
def avatar_asset(avatar_id: str, name: str) -> Response:
    try:
        if not features.STUDIO:
            return Response(status_code=404)
        from app.studio import project as pj

        folder = pj.assets_dir(avatar_id).resolve()
    except ValueError:
        return Response(status_code=404)
    path = (folder / Path(name).name).resolve()
    if not path.is_file() or path.parent != folder:
        return Response(status_code=404)
    return FileResponse(path, headers={"Cache-Control": "no-cache"})


# Pre-3.1 widget endpoints, kept for browser sources that cached the old page.
@_APP.get("/image.png")
def widget_image() -> Response:
    path, _ = lm.get_current_image_state()
    if path is None:
        return Response(content=_TRANSPARENT_PNG, media_type="image/png")
    return FileResponse(path)


@_APP.get("/state")
def widget_state() -> dict:
    _, shake_level = lm.get_current_image_state()
    return {"shake": shake_level}


@_APP.get("/health")
def health() -> dict:
    return {"status": "ok"}


# --- control API (Stream Deck, Touch Portal, Companion, Streamer.bot, hotkeys) --
def _ok(**payload: Any) -> Dict[str, Any]:
    return {"ok": True, **payload}


def _error(text: str, status: int = 404) -> JSONResponse:
    return JSONResponse({"ok": False, "error": text}, status_code=status)


def _brief(item: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    return {"id": item.get("id"), "name": item.get("name")} if item else None


@_APP.get("/api/status")
def api_status() -> dict:
    profile = lm.get_active_image_profile()
    state = lm.compute_state(profile=profile)
    return _ok(
        version=__version__,
        profile={**_brief(profile), "mode": profile.get("mode")} if profile else None,
        sound_profile=_brief(lm.get_active_sound_profile()),
        volume=state["volume"],
        avatar=avatar_service.debug(),
    )


@_APP.get("/api/profiles")
def api_profiles() -> dict:
    return _ok(
        profiles=[{**_brief(p), "mode": p.get("mode")} for p in sm.list_profiles()],
        sound_profiles=[_brief(p) for p in sm.list_sound_profiles()],
        params=[
            {"id": p["id"], "name": p["name"], "type": p["type"], "value": p.get("value")}
            for p in avatar_service.params()
        ],
    )


# GET is accepted too: many Stream Deck / Companion actions can only send GET.
@_APP.api_route("/api/param/{key}", methods=["GET", "POST"])
async def api_param(key: str, request: Request):
    """No value: fire a trigger / toggle a bool. ?value=… sets numbers and bools."""
    value = request.query_params.get("value")
    if value is None and request.method == "POST":
        try:
            body = await request.json()
            value = body.get("value") if isinstance(body, dict) else None
        except Exception:
            value = None
    if lm.get_active_image_profile() is None or not lm.is_advanced(lm.get_active_image_profile()):
        return _error("the active profile is not a Studio avatar", 409)
    done = avatar_service.fire(key) if value is None else avatar_service.set_param(key, value)
    return _ok(param=key) if done else _error("parameter not found")


@_APP.api_route("/api/sequence/{key}", methods=["GET", "POST"])
def api_sequence(key: str):
    if not lm.is_advanced(lm.get_active_image_profile()):
        return _error("the active profile is not a Studio avatar", 409)
    return _ok(sequence=key) if avatar_service.play_sequence(key) else _error("sequence not found")


@_APP.get("/api/state")
def api_state():
    debug = avatar_service.debug()
    return _ok(**debug) if debug is not None else _error("the active profile is not a Studio avatar", 409)


@_APP.api_route("/api/profile/{key}", methods=["GET", "POST"])
def api_set_profile(key: str):
    profile = lm.find_image_profile(key)
    if profile is None or not lm.activate_image_profile(profile["id"]):
        return _error("profile not found")
    return _ok(profile=_brief(profile))


@_APP.api_route("/api/sound-profile/{key}", methods=["GET", "POST"])
def api_set_sound_profile(key: str):
    text = key.strip()
    profiles = sm.list_sound_profiles()
    profile = next((p for p in profiles if str(p.get("id")) == text), None) or next(
        (p for p in profiles if str(p.get("name", "")).casefold() == text.casefold()), None
    )
    if profile is None:
        return _error("sound profile not found")
    lm.activate_sound_profile(profile["id"])
    lm.notify_changed()
    return _ok(sound_profile=_brief(profile))


# --- widget page -------------------------------------------------------------
# Simple profiles: one image at a time with the classic shake. Studio avatars:
# the render list from app/studio/evaluator.py drawn on a canvas; meshes are
# drawn triangle by triangle; frames are interpolated for smooth motion.
_WIDGET_HTML = """<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>PNG Streamer</title>
    <style>
      html, body { margin: 0; padding: 0; background: transparent; overflow: hidden; width: 100vw; height: 100vh; }
      #simple { position: absolute; inset: 0; }
      #simple img { position: absolute; visibility: hidden; transform-origin: center; }
      #simple img.on { visibility: visible; }
      #canvas { position: absolute; inset: 0; width: 100%; height: 100%; display: none; }
    </style>
  </head>
  <body>
    <div id="simple"></div>
    <canvas id="canvas"></canvas>
    <script>
      const simple = document.getElementById("simple");
      const canvas = document.getElementById("canvas");
      const ctx = canvas.getContext("2d");
      const images = new Map();
      let mode = null, current = null, shake = 0, avatar = null;
      let output = { anchor: "bottom", scale: 1, x: 0, y: 0, flip: false };
      const ANCHORS = { center: [0.5, 0.5], bottom: [0.5, 1], "bottom-left": [0, 1], "bottom-right": [1, 1], top: [0.5, 0],
        "top-left": [0, 0], "top-right": [1, 0], left: [0, 0.5], right: [1, 0.5] };
      // Where the avatar goes in the source; same math as app/studio/bindings.py place().
      function place(cw, ch, bw, bh) {
        cw = Math.max(1, cw); ch = Math.max(1, ch);
        const fit = Math.min(bw / cw, bh / ch) * output.scale;
        const w = cw * fit, h = ch * fit, [ax, ay] = ANCHORS[output.anchor] || ANCHORS.bottom;
        return { x: ax * (bw - w) + output.x / 100 * bw, y: ay * (bh - h) + output.y / 100 * bh, w, h };
      }
      function layoutSimple() {
        for (const img of images.values()) {
          if (!img.naturalWidth) { img.onload = layoutSimple; continue; }
          const r = place(img.naturalWidth, img.naturalHeight, window.innerWidth, window.innerHeight);
          Object.assign(img.style, { left: r.x + "px", top: r.y + "px", width: r.w + "px", height: r.h + "px" });
        }
      }
      window.addEventListener("resize", () => { if (mode === "simple") layoutSimple(); });
      let frames = [];  // last two Studio frames for interpolation
      const noise = (t, a, b) => Math.sin(t * a) * 0.65 + Math.sin(t * b + 1.7) * 0.35;

      function loadImages(list, key) {
        const wanted = new Set(list.map((i) => i[key]));
        for (const [name, img] of images) if (!wanted.has(name)) { img.remove(); images.delete(name); }
        for (const item of list) {
          let img = images.get(item[key]);
          if (!img) { img = new Image(); img.decoding = "async"; images.set(item[key], img); }
          img.src = item.url + "?v=" + Date.now();
        }
      }

      function setMode(next) {
        mode = next;
        simple.style.display = mode === "simple" ? "block" : "none";
        canvas.style.display = mode === "avatar" ? "block" : "none";
      }

      // --- simple profiles ---
      function showSimple(name) {
        if (name === current) return;
        const next = images.get(name), prev = images.get(current);
        if (next) next.classList.add("on");
        if (prev && prev !== next) prev.classList.remove("on");
        current = name;
      }

      // --- Studio avatars ---
      function resize() {
        const dpr = window.devicePixelRatio || 1;
        canvas.width = Math.round(canvas.clientWidth * dpr);
        canvas.height = Math.round(canvas.clientHeight * dpr);
      }
      window.addEventListener("resize", resize);

      const tintCache = new Map();
      function tinted(img, tint) {
        const key = img.src + tint.join(",");
        let c = tintCache.get(key);
        if (!c) {
          c = document.createElement("canvas");
          c.width = img.naturalWidth; c.height = img.naturalHeight;
          const g = c.getContext("2d");
          g.drawImage(img, 0, 0);
          g.globalCompositeOperation = "source-atop";
          g.globalAlpha = tint[3];
          g.fillStyle = `rgb(${tint[0]},${tint[1]},${tint[2]})`;
          g.fillRect(0, 0, c.width, c.height);
          if (tintCache.size > 64) tintCache.clear();
          tintCache.set(key, c);
        }
        return c;
      }

      function drawTriangle(img, s0, s1, s2, d0, d1, d2) {
        // affine map from source triangle (image px) to destination (local px)
        const den = (s1[0] - s0[0]) * (s2[1] - s0[1]) - (s2[0] - s0[0]) * (s1[1] - s0[1]);
        if (Math.abs(den) < 1e-9) return;
        const a = ((d1[0] - d0[0]) * (s2[1] - s0[1]) - (d2[0] - d0[0]) * (s1[1] - s0[1])) / den;
        const b = ((d1[1] - d0[1]) * (s2[1] - s0[1]) - (d2[1] - d0[1]) * (s1[1] - s0[1])) / den;
        const c = ((d2[0] - d0[0]) * (s1[0] - s0[0]) - (d1[0] - d0[0]) * (s2[0] - s0[0])) / den;
        const d = ((d2[1] - d0[1]) * (s1[0] - s0[0]) - (d1[1] - d0[1]) * (s2[0] - s0[0])) / den;
        const e = d0[0] - a * s0[0] - c * s0[1];
        const f = d0[1] - b * s0[0] - d * s0[1];
        // grow the clip triangle slightly to hide seams between triangles
        const cx = (d0[0] + d1[0] + d2[0]) / 3, cy = (d0[1] + d1[1] + d2[1]) / 3;
        const grow = (p) => [p[0] + (p[0] - cx) * 0.02, p[1] + (p[1] - cy) * 0.02];
        const [g0, g1, g2] = [grow(d0), grow(d1), grow(d2)];
        ctx.save();
        ctx.beginPath(); ctx.moveTo(g0[0], g0[1]); ctx.lineTo(g1[0], g1[1]); ctx.lineTo(g2[0], g2[1]); ctx.closePath();
        ctx.clip();
        ctx.transform(a, b, c, d, e, f);
        ctx.drawImage(img, 0, 0);
        ctx.restore();
      }

      function drawMesh(img, item) {
        const { cols, rows, pts } = item.mesh;
        const w = item.w, h = item.h, stride = cols + 1;
        const src = (i) => [(i % stride) / cols * w, Math.floor(i / stride) / rows * h];
        const dst = (i) => [pts[i * 2], pts[i * 2 + 1]];
        for (let r = 0; r < rows; r++) for (let c = 0; c < cols; c++) {
          const a = r * stride + c, b = a + 1, d = a + stride, e = d + 1;
          drawTriangle(img, src(a), src(b), src(d), dst(a), dst(b), dst(d));
          drawTriangle(img, src(b), src(e), src(d), dst(b), dst(e), dst(d));
        }
      }

      const BLEND = { normal: "source-over", add: "lighter", multiply: "multiply", screen: "screen" };

      function interpolated(now) {
        if (frames.length < 2) return frames.length ? frames[frames.length - 1].items : [];
        const [a, b] = frames.slice(-2);
        const span = b.t - a.t, k = span > 0 ? Math.min(Math.max((now - b.at) / span, 0), 1) : 1;
        const before = new Map(a.items.map((i) => [i.node + "|" + i.asset, i]));
        return b.items.map((item) => {
          const prev = before.get(item.node + "|" + item.asset);
          if (!prev || k >= 1) return item;
          // render one frame late and blend toward the newest to hide network jitter
          const m = prev.m.map((v, n) => v + (item.m[n] - v) * k);
          return { ...item, m };
        });
      }

      function drawAvatar(now) {
        if (!avatar) return;
        const { w, h } = avatar.canvas;
        const r = place(w, h, canvas.width, canvas.height);
        const scale = r.w / w;
        let ox = r.x, oy = r.y;
        ctx.setTransform(1, 0, 0, 1, 0, 0);
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        const flip = output.flip ? -1 : 1;
        if (output.flip) ox = r.x + r.w;
        for (const item of interpolated(now)) {
          let img = images.get(item.asset);
          if (!img || !img.complete || !img.naturalWidth) continue;
          if (item.tint) img = tinted(img, item.tint);
          const m = item.m;
          ctx.setTransform(flip * scale * m[0], scale * m[1], flip * scale * m[2], scale * m[3], flip * scale * m[4] + ox, scale * m[5] + oy);
          ctx.globalAlpha = item.o;
          ctx.globalCompositeOperation = BLEND[item.blend] || "source-over";
          if (item.mesh) drawMesh(img, item); else ctx.drawImage(img, 0, 0, item.w, item.h);
        }
        ctx.globalAlpha = 1;
        ctx.globalCompositeOperation = "source-over";
      }

      function tick(ms) {
        if (mode === "simple") {
          const img = images.get(current);
          if (img) {
            if (shake > 0) {
              const t = ms / 1000 * 2.2;
              img.style.transform = `translate(${(noise(t, 12, 23) * shake).toFixed(2)}px, ${(noise(t + 3.1, 15, 27) * shake).toFixed(2)}px)` + (output.flip ? " scaleX(-1)" : "");
            } else img.style.transform = output.flip ? "scaleX(-1)" : "none";
          }
        } else if (mode === "avatar") drawAvatar(performance.now());
        requestAnimationFrame(tick);
      }

      function connect() {
        const ws = new WebSocket(`ws://${location.host}/ws`);
        ws.onmessage = (event) => {
          const message = JSON.parse(event.data);
          if (message.output) output = message.output;
          if (message.type === "simple") {
            setMode("simple"); avatar = null; frames = [];
            loadImages(message.images, "name");
            simple.replaceChildren(...[...images.values()]);
            layoutSimple();
            const name = current; current = null; showSimple(name);
          } else if (message.type === "state") {
            shake = message.shake || 0;
            showSimple(message.image);
          } else if (message.type === "avatar") {
            setMode("avatar"); resize();
            avatar = message; frames = [];
            loadImages(message.assets, "id");
          } else if (message.type === "frame") {
            frames.push({ t: message.t, at: performance.now(), items: message.items });
            if (frames.length > 2) frames.shift();
          }
        };
        ws.onclose = () => setTimeout(connect, 1000);
      }

      resize();
      connect();
      requestAnimationFrame(tick);
    </script>
  </body>
</html>"""


# --- server lifecycle --------------------------------------------------------
_START_TIMEOUT_SECONDS = 5.0
_STOP_TIMEOUT_SECONDS = 3.0


def start_server(host: str, port: int) -> Tuple[bool, str]:
    global _server_thread, _server, _current_port
    with _server_lock:
        if _server_thread and _server_thread.is_alive():
            return False, "already_running"
        # log_config=None keeps uvicorn on our logging setup: its default
        # config writes to sys.stderr, which is None in windowed builds.
        config = uvicorn.Config(
            _APP,
            host=host,
            port=port,
            log_level="info",
            log_config=None,
            access_log=False,
            ws="websockets-sansio",
            lifespan="off",
            # Open OBS widget connections must not keep the server from stopping.
            timeout_graceful_shutdown=1,
        )
        server = uvicorn.Server(config=config)
        thread = threading.Thread(target=server.run, daemon=True)
        thread.start()

        deadline = time.monotonic() + _START_TIMEOUT_SECONDS
        while not server.started and thread.is_alive() and time.monotonic() < deadline:
            time.sleep(0.02)
        if not server.started:
            server.should_exit = True
            _LOGGER.error("Server failed to start: host=%s port=%s", host, port)
            return False, "failed"

        _server, _server_thread, _current_port = server, thread, port
        _LOGGER.info("Server started: host=%s port=%s", host, port)
        return True, "started"


def stop_server() -> bool:
    global _server_thread, _server, _current_port
    with _server_lock:
        if _server is None:
            return False
        _server.should_exit = True
        if _server_thread is not None:
            _server_thread.join(_STOP_TIMEOUT_SECONDS)
        _server = None
        _server_thread = None
        _current_port = None
        _LOGGER.info("Server stopped")
        return True


def is_running() -> bool:
    return _server_thread is not None and _server_thread.is_alive()


def current_port() -> Optional[int]:
    return _current_port
