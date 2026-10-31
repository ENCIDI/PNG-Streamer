# PyInstaller spec: one-folder build (Qt stays in separate, replaceable
# libraries as required by the LGPL). Run from the repository root:
#   pyinstaller --noconfirm packaging/pngstreamer.spec
import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_submodules

ROOT = Path(SPECPATH).parent

datas = [
    (str(ROOT / "app" / "assets"), "app/assets"),
    (str(ROOT / "app" / "defaults"), "app/defaults"),
    (str(ROOT / "licenses"), "licenses"),
    (str(ROOT / "LICENSE"), "licenses"),
]

binaries = []
if sys.platform.startswith("linux"):
    # sounddevice wheels do not ship PortAudio on Linux; bundle the build host's copy.
    for candidate in ("/usr/lib/x86_64-linux-gnu/libportaudio.so.2", "/usr/lib64/libportaudio.so.2"):
        if Path(candidate).exists():
            binaries.append((candidate, "."))
            break
    else:
        raise SystemExit("libportaudio.so.2 not found, install libportaudio2")

# Qt modules the app never imports. Some of them are GPL-only, and all of
# them only add size.
excludes = [
    "tkinter",
    "PySide6.QtQml",
    "PySide6.QtQuick",
    "PySide6.QtQuickWidgets",
    "PySide6.QtQuickControls2",
    "PySide6.QtQuickTest",
    "PySide6.QtOpenGL",
    "PySide6.QtOpenGLWidgets",
    "PySide6.QtPdf",
    "PySide6.QtSql",
    "PySide6.QtTest",
    "PySide6.QtXml",
    "PySide6.QtDesigner",
    "PySide6.QtHelp",
    "PySide6.QtUiTools",
    "PySide6.QtConcurrent",
    "PySide6.QtPrintSupport",
    "PySide6.QtSvgWidgets",
    "PySide6.QtLabsStyleKit",
]

a = Analysis(
    [str(ROOT / "main.py")],
    pathex=[str(ROOT)],
    binaries=binaries,
    datas=datas,
    hiddenimports=collect_submodules("uvicorn"),
    excludes=excludes,
    noarchive=False,
)
# Software OpenGL fallback and Qt's own translations are not used by a widgets app.
a.binaries = [entry for entry in a.binaries if "opengl32sw" not in entry[0]]
a.datas = [entry for entry in a.datas if "PySide6/translations" not in entry[0].replace("\\", "/")]

pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="PNGStreamer",
    console=False,
    icon=str(ROOT / "app" / "assets" / "icon.ico"),
    upx=False,
)
coll = COLLECT(exe, a.binaries, a.datas, name="PNGStreamer", upx=False)
