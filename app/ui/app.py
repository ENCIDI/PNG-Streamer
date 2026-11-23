import json
import sys
from pathlib import Path
from typing import List, Optional

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from app import features, paths
from app.modules import (
    audio_manager as am,
    autostart_manager as autostart,
    avatar_pack,
    logging_manager as logm,
    storage_manager as sm,
    web_manager as wm,
)
from app.modules.studio_bridge import service as avatar_service
from app.ui import i18n, linux_setup, theme
from app.ui.hotkeys import HotkeyManager
from app.ui.main_window import MainWindow, app_icon
from app.ui.onboarding import OnboardingDialog
from app.ui.single_instance import SingleInstance
from app.ui.state import HOST, AppState
from app.ui.tray import Tray
from app.ui.updater import Updater
from app.version import __version__

SELF_TEST_ARG = "--self-test"
_IMAGES_PAGE = 2


def _scene_file(path: str) -> bool:
    if not features.STUDIO:
        return False
    from app.studio.packs import SCENE_EXTENSION

    return path.lower().endswith(SCENE_EXTENSION)


def _opens(path: str) -> bool:
    return path.lower().endswith(avatar_pack.OPEN_EXTENSIONS) or _scene_file(path)


def _pack_argument(argv: List[str]) -> str:
    """Avatar file passed on the command line (a double click)."""
    for arg in argv[1:]:
        if _opens(arg) and Path(arg).is_file():
            return str(Path(arg).resolve())
    return ""


def _close_studio() -> None:
    if features.STUDIO:
        from app.ui.studio.window import close_all

        close_all()


class Application:
    def __init__(self, qt_app: QApplication, launched_by_autostart: bool, self_test: bool):
        self.qt_app = qt_app
        self.self_test = self_test
        self.instance: Optional[SingleInstance] = None
        self.state = AppState()
        self.state.restart_microphone()
        self.updater = Updater(self.state)
        self.hotkeys = HotkeyManager()
        self.hotkeys.triggered.connect(self.state.fire_param)
        self.state.profiles_changed.connect(self.hotkeys.reload)
        avatar_service.start()
        self.window = MainWindow(self.state, self.updater, self.hotkeys)
        self.window.screens[-1].wizard_requested.connect(self.run_onboarding)
        if features.STUDIO:
            self.window.studio_requested.connect(self.open_studio)
        self.tray: Optional[Tray] = None
        if Tray.available() and not self_test:
            self.tray = Tray(self.state, self.updater)
            self.tray.open_requested.connect(self.show_window)
            self.tray.toggle_requested.connect(self.toggle_window)
            self.tray.quit_requested.connect(lambda: self.quit(confirm=False))
            self.tray.install_requested.connect(self.window.banner.start_install)
            self.tray.show()
        self.window.close_requested.connect(self._on_close_requested)
        self.updater.ready_to_quit.connect(lambda: self.quit(confirm=False))
        self.updater.before_install = self._release_instance
        qt_app.aboutToQuit.connect(self._shutdown)

        settings = self.state.settings()
        if settings.get("start-server-on-launch") and not self_test:
            self.state.start_server()
        if not self_test:
            self.state.apply_chat()
        start_hidden = launched_by_autostart and settings.get("start-minimized") and self.tray is not None
        if not start_hidden:
            self.window.show()
        if not settings.get("onboarding-done") and not self_test and not start_hidden:
            QTimer.singleShot(300, self.run_onboarding)

    def run_onboarding(self) -> None:
        self.show_window()
        OnboardingDialog(self.window, self.state).exec()

    def open_file(self, path: str) -> None:
        if not _opens(path):
            return
        if _scene_file(path):
            self._open_scene_file(Path(path))
            return
        self.show_window()
        self.window.show_page(_IMAGES_PAGE)
        if self.window.pages.currentIndex() == _IMAGES_PAGE:
            self.window.screens[_IMAGES_PAGE].import_pack(Path(path))

    def _open_scene_file(self, path: Path) -> None:
        """A scene file goes into the Studio's library and opens there."""
        from app.studio.packs import import_scene
        from app.ui.studio.window import open_studio

        try:
            scene = import_scene(path)
        except avatar_pack.PackError as error:
            self.show_window()
            self.state.notify.emit(i18n.t("packs.import_failed", error=error), "error")
            return
        open_studio(scene, self.state, self.hotkeys)

    def attach_instance(self, instance: SingleInstance) -> None:
        self.instance = instance
        instance.show_requested.connect(self.show_window)
        instance.open_requested.connect(self.open_file)

    def _release_instance(self) -> None:
        if self.instance is not None:
            self.instance.release()

    def open_studio(self) -> None:
        from app.ui.studio.window import open_studio

        open_studio(None, self.state, self.hotkeys)

    def show_window(self) -> None:
        self.window.bring_to_front()

    def toggle_window(self) -> None:
        if self.window.isVisible() and not self.window.isMinimized():
            self.window.hide()
        else:
            self.show_window()

    def _on_close_requested(self) -> None:
        settings = self.state.settings()
        if self.tray is not None and settings.get("minimize-to-tray-on-close", True):
            self.window.hide()
            if not settings.get("tray-hint-shown"):
                self.tray.show_hint()
                self.state.update_settings(tray_hint_shown=True)
            return
        self.quit(confirm=True)

    def quit(self, confirm: bool) -> None:
        if confirm and not self.window.confirm_quit():
            return
        _close_studio()  # the Studio saves and closes with the app
        self.window.allow_close = True
        self.window.close()
        self.qt_app.quit()

    def _shutdown(self) -> None:
        from app.modules.twitch_chat import chat

        _close_studio()
        chat.stop()
        self.hotkeys.stop()
        avatar_service.stop()
        wm.stop_server()
        am.stop_monitor()
        if self.tray is not None:
            self.tray.hide()
        self._release_instance()
        logm.get_logger(__name__).info("Application exit")


def _self_test_tls() -> bool:
    """The update check needs a CA bundle inside the build (see update_manager)."""
    from app.modules import update_manager as um

    try:
        um._ssl_context()
    except Exception:
        logm.get_logger(__name__).exception("Self-test: no usable CA certificates")
        return False
    return True


def _self_test_server(state: AppState) -> bool:
    import socket
    import urllib.request

    with socket.socket() as probe:
        probe.bind((HOST, 0))
        port = probe.getsockname()[1]
    if not state.start_server(port):
        return False
    try:
        with urllib.request.urlopen(f"http://{HOST}:{port}/health", timeout=5) as response:
            if response.status != 200:
                return False
        # The OBS widget needs the WebSocket stack, which is imported dynamically.
        from websockets.sync.client import connect

        with connect(f"ws://{HOST}:{port}/ws", open_timeout=5) as ws:
            return json.loads(ws.recv(timeout=5)).get("type") in ("simple", "avatar")
    except Exception:
        logm.get_logger(__name__).exception("Self-test: server check failed")
        return False
    finally:
        state.stop_server()


def run(argv: Optional[List[str]] = None) -> int:
    argv = list(sys.argv if argv is None else argv)
    self_test = SELF_TEST_ARG in argv
    launched_by_autostart = autostart.AUTOSTART_ARG in argv

    QApplication.setApplicationName("PNGStreamer")
    QApplication.setApplicationDisplayName("PNG Streamer")
    QApplication.setApplicationVersion(__version__)
    QApplication.setDesktopFileName("pngstreamer")
    qt_app = QApplication(argv)
    qt_app.setQuitOnLastWindowClosed(False)
    qt_app.setWindowIcon(app_icon())
    theme.apply(qt_app)

    if not self_test and linux_setup.needed() and linux_setup.run():
        return 0

    logm.init_logging()
    logger = logm.get_logger(__name__)
    logger.info("Application start: version=%s frozen=%s root=%s", __version__, paths.is_frozen(), paths.APP_ROOT)

    pack = _pack_argument(argv)
    instance = SingleInstance()
    if not self_test and not instance.acquire(pack):
        return 0

    sm.init_storage()
    am.log_environment()
    i18n.init_language()
    if paths.is_frozen():
        autostart.refresh()

    application = Application(qt_app, launched_by_autostart, self_test)
    if not self_test:
        application.attach_instance(instance)
        if pack:
            QTimer.singleShot(500, lambda: application.open_file(pack))
    else:
        def _finish() -> None:
            for index in range(len(application.window.screens)):
                application.window.show_page(index)
                qt_app.processEvents()
            ok = _self_test_server(application.state) and _self_test_tls()
            logger.info("Self-test %s", "passed" if ok else "FAILED")
            application.quit(confirm=False)
            if not ok:
                qt_app.exit(1)

        QTimer.singleShot(1500, _finish)
    return qt_app.exec()
