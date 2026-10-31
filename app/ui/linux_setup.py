"""First start of the Linux AppImage: offer to move it into a permanent folder
and register it in the applications menu / on the desktop."""
import os
import shutil
import stat
import subprocess
import sys
from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QPixmap
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
)

from app import paths
from app.ui import i18n, theme

APPIMAGE_NAME = "PNGStreamer.AppImage"
ICON_NAME = "pngstreamer"


def needed() -> bool:
    return (
        sys.platform.startswith("linux")
        and paths.is_frozen()
        and bool(os.environ.get("APPIMAGE"))
        and not paths.DATA_DIR.exists()
    )


def _xdg_dir(env: str, fallback: Path) -> Path:
    return Path(os.environ.get(env) or fallback)


def _desktop_dir() -> Path:
    try:
        out = subprocess.run(["xdg-user-dir", "DESKTOP"], capture_output=True, text=True, timeout=3)
        if out.returncode == 0 and out.stdout.strip():
            return Path(out.stdout.strip())
    except (OSError, subprocess.SubprocessError):
        pass
    return Path.home() / "Desktop"


def _desktop_entry(appimage: Path) -> str:
    return (
        "[Desktop Entry]\n"
        "Type=Application\n"
        "Name=PNG Streamer\n"
        "Comment=PNGTuber avatar for OBS\n"
        f'Exec="{appimage}"\n'
        f"Icon={ICON_NAME}\n"
        "Terminal=false\n"
        "Categories=AudioVideo;Utility;\n"
        "StartupWMClass=PNGStreamer\n"
    )


def install(target_dir: Path, menu_entry: bool, desktop_entry: bool) -> Path:
    source = Path(os.environ["APPIMAGE"]).resolve()
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / APPIMAGE_NAME
    if source != target.resolve():
        shutil.copy2(source, target)
        target.chmod(target.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        source.unlink()

    data_home = _xdg_dir("XDG_DATA_HOME", Path.home() / ".local" / "share")
    icon_dir = data_home / "icons" / "hicolor" / "256x256" / "apps"
    icon_dir.mkdir(parents=True, exist_ok=True)
    QPixmap(str(paths.RESOURCES_DIR / "assets" / "icon.ico")).scaled(
        256, 256, Qt.KeepAspectRatio, Qt.SmoothTransformation
    ).save(str(icon_dir / f"{ICON_NAME}.png"))

    entry = _desktop_entry(target)
    if menu_entry:
        applications = data_home / "applications"
        applications.mkdir(parents=True, exist_ok=True)
        (applications / f"{ICON_NAME}.desktop").write_text(entry, encoding="utf-8")
    if desktop_entry:
        desktop = _desktop_dir()
        desktop.mkdir(parents=True, exist_ok=True)
        shortcut = desktop / f"{ICON_NAME}.desktop"
        shortcut.write_text(entry, encoding="utf-8")
        shortcut.chmod(0o755)
        try:  # GNOME only launches desktop files marked as trusted
            subprocess.run(["gio", "set", str(shortcut), "metadata::trusted", "true"], timeout=3, check=False)
        except (OSError, subprocess.SubprocessError):
            pass
    return target


class SetupDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PNG Streamer")
        self.setMinimumWidth(520)
        self.installed: Optional[Path] = None
        layout = QVBoxLayout(self)
        layout.setContentsMargins(26, 24, 26, 22)
        layout.setSpacing(14)
        title = QLabel(i18n.t("setup.title"))
        title.setFont(theme.font(14, QFont.DemiBold))
        layout.addWidget(title)
        text = QLabel(i18n.t("setup.text"))
        text.setObjectName("muted")
        text.setWordWrap(True)
        layout.addWidget(text)

        label = QLabel(i18n.t("setup.folder"))
        label.setObjectName("muted")
        layout.addWidget(label)
        row = QHBoxLayout()
        self.folder = QLineEdit(str(Path.home() / "Applications" / "PNGStreamer"))
        browse = QPushButton(i18n.t("setup.browse"))
        browse.clicked.connect(self._browse)
        row.addWidget(self.folder, 1)
        row.addWidget(browse)
        layout.addLayout(row)

        self.menu_entry = QCheckBox(i18n.t("setup.menu_entry"))
        self.menu_entry.setChecked(True)
        self.desktop_entry = QCheckBox(i18n.t("setup.desktop_entry"))
        layout.addWidget(self.menu_entry)
        layout.addWidget(self.desktop_entry)
        self.error = QLabel()
        self.error.setObjectName("danger")
        self.error.setWordWrap(True)
        self.error.hide()
        layout.addWidget(self.error)

        buttons = QHBoxLayout()
        buttons.addStretch()
        skip = QPushButton(i18n.t("setup.skip"))
        skip.clicked.connect(self.reject)
        install_button = QPushButton(i18n.t("setup.install"))
        install_button.setObjectName("primary")
        install_button.setDefault(True)
        install_button.clicked.connect(self._install)
        buttons.addWidget(skip)
        buttons.addWidget(install_button)
        layout.addSpacing(6)
        layout.addLayout(buttons)

    def _browse(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, i18n.t("setup.folder"), self.folder.text())
        if folder:
            self.folder.setText(folder)

    def _install(self) -> None:
        try:
            self.installed = install(
                Path(self.folder.text()).expanduser(), self.menu_entry.isChecked(), self.desktop_entry.isChecked()
            )
        except OSError as error:
            self.error.setText(i18n.t("setup.failed", error=error))
            self.error.show()
            return
        self.accept()


def run() -> bool:
    """Show the dialog. Returns True when the app was relaunched from its new place
    and the current process should exit."""
    i18n.use_system_language()
    dialog = SetupDialog()
    if dialog.exec() != QDialog.Accepted or dialog.installed is None:
        return False
    env = {key: value for key, value in os.environ.items() if not key.startswith("APPIMAGE") and key != "APPDIR"}
    subprocess.Popen([str(dialog.installed)], env=env, start_new_session=True, close_fds=True)
    return True
