import threading
from typing import Optional, Tuple

from fastapi import FastAPI
from fastapi.responses import FileResponse, HTMLResponse, Response
import uvicorn

from app.modules import logic_manager as lm


_server_lock = threading.Lock()
_server_thread: Optional[threading.Thread] = None
_server: Optional[uvicorn.Server] = None
_current_port: Optional[int] = None


_APP = FastAPI()

_TRANSPARENT_PNG = bytes(
    [
        137,
        80,
        78,
        71,
        13,
        10,
        26,
        10,
        0,
        0,
        0,
        13,
        73,
        72,
        68,
        82,
        0,
        0,
        0,
        1,
        0,
        0,
        0,
        1,
        8,
        6,
        0,
        0,
        0,
        31,
        21,
        196,
        137,
        0,
        0,
        0,
        12,
        73,
        68,
        65,
        84,
        120,
        156,
        99,
        96,
        0,
        0,
        0,
        2,
        0,
        1,
        229,
        39,
        212,
        160,
        0,
        0,
        0,
        0,
        73,
        69,
        78,
        68,
        174,
        66,
        96,
        130,
    ]
)


@_APP.get("/", response_class=HTMLResponse)
def widget_root() -> str:
    return _widget_html()


@_APP.get("/widget", response_class=HTMLResponse)
def widget_page() -> str:
    return _widget_html()


@_APP.get("/image.png")
def widget_image() -> Response:
    path = lm.get_current_image_path()
    if path is None:
        return Response(content=_TRANSPARENT_PNG, media_type="image/png")
    return FileResponse(path)


@_APP.get("/health")
def health() -> dict:
    return {"status": "ok"}


def _widget_html() -> str:
    return """<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>PNG Streamer</title>
    <style>
      html, body { margin: 0; padding: 0; background: transparent; overflow: hidden; }
      img { display: block; width: 100vw; height: 100vh; object-fit: contain; }
    </style>
  </head>
  <body>
    <img id="avatar" src="/image.png" alt="avatar" />
    <script>
      const img = document.getElementById("avatar");
      setInterval(() => {
        img.src = "/image.png?ts=" + Date.now();
      }, 200);
    </script>
  </body>
</html>"""


def start_server(host: str, port: int) -> Tuple[bool, str]:
    global _server_thread, _server, _current_port
    with _server_lock:
        if _server_thread and _server_thread.is_alive():
            return False, "already_running"
        config = uvicorn.Config(_APP, host=host, port=port, log_level="info")
        _server = uvicorn.Server(config=config)
        _current_port = port

        def _run() -> None:
            _server.run()

        _server_thread = threading.Thread(target=_run, daemon=True)
        _server_thread.start()
        return True, "started"


def stop_server() -> bool:
    global _server_thread, _server, _current_port
    with _server_lock:
        if _server is None:
            return False
        _server.should_exit = True
        _server = None
        _server_thread = None
        _current_port = None
        return True


def is_running() -> bool:
    return _server_thread is not None and _server_thread.is_alive()


def current_port() -> Optional[int]:
    return _current_port
