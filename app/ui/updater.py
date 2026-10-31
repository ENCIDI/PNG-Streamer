import threading
from typing import Callable, Optional

from PySide6.QtCore import QObject, QTimer, Signal

from app.modules import logging_manager as logm, update_manager as um
from app.ui.state import AppState

_LOGGER = logm.get_logger(__name__)

_FIRST_CHECK_DELAY_MS = 5000
_RECHECK_MS = 60 * 60 * 1000


class Updater(QObject):
    """Runs update checks/downloads off the UI thread and reports back via signals."""

    status_changed = Signal()  # check state for the settings screen
    update_found = Signal(object)  # UpdateInfo or None
    progress = Signal(int)
    failed = Signal(str)
    ready_to_quit = Signal()

    _checked = Signal(object)
    _downloaded = Signal(object)
    _download_failed = Signal(str)

    def __init__(self, state: AppState):
        super().__init__()
        self.state = state
        self.checking = False
        self.downloading = False
        self.last_result: Optional[um.CheckResult] = None
        self.update: Optional[um.UpdateInfo] = None
        self._manual = False
        # Called right before the new version is launched, e.g. to release the
        # single-instance lock so the new process does not hand over to us.
        self.before_install: Optional[Callable[[], None]] = None
        self._checked.connect(self._on_checked)
        self._downloaded.connect(self._on_downloaded)
        self._download_failed.connect(self._on_download_failed)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._auto_check)
        self._timer.start(_RECHECK_MS)
        QTimer.singleShot(_FIRST_CHECK_DELAY_MS, self._auto_check)

    @property
    def eligible(self) -> bool:
        return um.is_eligible()

    def _auto_check(self) -> None:
        if um.is_eligible() and um.check_due():
            self.check(manual=False)

    def check(self, manual: bool = True) -> None:
        if self.checking or not um.is_eligible():
            return
        self.checking = True
        self._manual = manual
        self.status_changed.emit()
        um.check_async(self._checked.emit)

    def _on_checked(self, result: um.CheckResult) -> None:
        self.checking = False
        self.last_result = result
        update = result.update
        skipped = self.state.settings().get("skipped-version", "")
        if update and update.version == skipped and not self._manual:
            update = None
        self.update = update
        self.status_changed.emit()
        self.update_found.emit(update)

    def skip(self) -> None:
        if self.update:
            self.state.update_settings(skipped_version=self.update.version)
        self.update = None
        self.update_found.emit(None)

    def install(self) -> None:
        if self.update is None or self.downloading:
            return
        self.downloading = True
        info = self.update

        def _run() -> None:
            try:
                path = um.download(info, self.progress.emit)
                self._downloaded.emit(path)
            except Exception as error:
                _LOGGER.exception("Update download failed")
                self._download_failed.emit(str(error))

        threading.Thread(target=_run, daemon=True).start()

    def _on_downloaded(self, path) -> None:
        try:
            if self.before_install is not None:
                self.before_install()
            um.install(self.update, path)
        except Exception as error:
            _LOGGER.exception("Update install failed")
            self._on_download_failed(str(error))
            return
        self.ready_to_quit.emit()

    def _on_download_failed(self, error: str) -> None:
        self.downloading = False
        self.failed.emit(error)
