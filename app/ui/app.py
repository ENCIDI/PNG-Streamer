import sys
from typing import List, Optional

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from app import paths
from app.modules import (
    audio_manager as am,
    autostart_manager as autostart,
    logging_manager as logm,
    storage_manager as sm,
    web_manager as wm,
)
from app.ui import i18n, linux_setup, theme
from app.ui.main_window import MainWindow, app_icon
from app.ui.single_instance import SingleInstance
from app.ui.state import HOST, AppState
from app.ui.tray import Tray
from app.ui.updater import Updater
from app.version import __version__

SELF_TEST_ARG = "--self-test"


class Application:
    def __init__(self, qt_app: QApplication, launched_by_autostart: bool, self_test: bool):
        self.qt_app = qt_app
        self.self_test = self_test
        self.instance: Optional[SingleInstance] = None
        self.state = AppState()
        self.state.restart_microphone()
        self.updater = Updater(self.state)
        self.window = MainWindow(self.state, self.updater)
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
        start_hidden = launched_by_autostart and settings.get("start-minimized") and self.tray is not None
        if not start_hidden:
            self.window.show()

    def attach_instance(self, instance: SingleInstance) -> None:
        self.instance = instance
        instance.show_requested.connect(self.show_window)

    def _release_instance(self) -> None:
        if self.instance is not None:
            self.instance.release()

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
        self.window.allow_close = True
        self.window.close()
        self.qt_app.quit()

    def _shutdown(self) -> None:
        wm.stop_server()
        am.stop_monitor()
        if self.tray is not None:
            self.tray.hide()
        self._release_instance()
        logm.get_logger(__name__).info("Application exit")


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
            return response.status == 200
    except OSError:
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

    instance = SingleInstance()
    if not self_test and not instance.acquire():
        return 0

    sm.init_storage()
    am.log_environment()
    i18n.init_language()
    if paths.is_frozen():
        autostart.refresh()

    application = Application(qt_app, launched_by_autostart, self_test)
    if not self_test:
        application.attach_instance(instance)
    else:
        def _finish() -> None:
            for index in range(len(application.window.screens)):
                application.window.show_page(index)
                qt_app.processEvents()
            ok = _self_test_server(application.state)
            logger.info("Self-test %s", "passed" if ok else "FAILED")
            application.quit(confirm=False)
            if not ok:
                qt_app.exit(1)

        QTimer.singleShot(1500, _finish)
    return qt_app.exec()
