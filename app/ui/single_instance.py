import getpass
import hashlib
import sys

from PySide6.QtCore import QObject, Signal
from PySide6.QtNetwork import QLocalServer, QLocalSocket

from app.modules import logging_manager as logm

_LOGGER = logm.get_logger(__name__)

_SHOW = b"show"
_TIMEOUT_MS = 500
# Also checked by the Windows installer (AppMutex) to ask the user to close the app.
WINDOWS_MUTEX = "PNGStreamerMutex"


def _server_name() -> str:
    try:
        user = getpass.getuser()
    except Exception:
        user = "user"
    return "PNGStreamer-" + hashlib.sha1(user.encode("utf-8")).hexdigest()[:12]


class SingleInstance(QObject):
    """Second launches hand over to the running instance, which shows its window."""

    show_requested = Signal()

    def __init__(self):
        super().__init__()
        self._name = _server_name()
        self._server: QLocalServer | None = None
        self._mutex = None

    def acquire(self) -> bool:
        socket = QLocalSocket()
        socket.connectToServer(self._name)
        if socket.waitForConnected(_TIMEOUT_MS):
            socket.write(_SHOW)
            socket.flush()
            socket.waitForBytesWritten(_TIMEOUT_MS)
            socket.disconnectFromServer()
            _LOGGER.info("Another instance is running, asked it to show its window")
            return False
        # A crashed instance can leave a stale socket file behind on Unix.
        QLocalServer.removeServer(self._name)
        self._server = QLocalServer(self)
        self._server.newConnection.connect(self._on_connection)
        if not self._server.listen(self._name):
            _LOGGER.warning("Single-instance server failed: %s", self._server.errorString())
        if sys.platform == "win32":
            import ctypes

            self._mutex = ctypes.windll.kernel32.CreateMutexW(None, False, WINDOWS_MUTEX)
        return True

    def release(self) -> None:
        if self._server is not None:
            self._server.close()
            self._server = None
        if self._mutex:
            import ctypes

            ctypes.windll.kernel32.CloseHandle(self._mutex)
            self._mutex = None

    def _on_connection(self) -> None:
        while self._server is not None and self._server.hasPendingConnections():
            socket = self._server.nextPendingConnection()
            socket.waitForReadyRead(_TIMEOUT_MS)
            if socket.readAll().data().startswith(_SHOW):
                self.show_requested.emit()
            socket.deleteLater()
