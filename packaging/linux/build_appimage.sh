#!/usr/bin/env bash
# Wrap the PyInstaller build (dist/PNGStreamer) into an AppImage.
# Usage: packaging/linux/build_appimage.sh <version>
set -euo pipefail

VERSION="$1"
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
DIST="$ROOT/dist"
APPDIR="$DIST/AppDir"
TOOL="$DIST/appimagetool-x86_64.AppImage"

rm -rf "$APPDIR"
mkdir -p "$APPDIR/usr/lib"
cp -a "$DIST/PNGStreamer" "$APPDIR/usr/lib/pngstreamer"
install -m 755 "$ROOT/packaging/linux/AppRun" "$APPDIR/AppRun"
cp "$ROOT/packaging/linux/pngstreamer.desktop" "$APPDIR/pngstreamer.desktop"

QT_QPA_PLATFORM=offscreen python - "$ROOT/app/assets/icon.ico" "$APPDIR/pngstreamer.png" <<'PY'
import sys
from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication, QImage
app = QGuiApplication([])
image = QImage(sys.argv[1])
assert not image.isNull(), "icon not readable"
image.scaled(256, 256, Qt.KeepAspectRatio, Qt.SmoothTransformation).save(sys.argv[2])
PY
cp "$APPDIR/pngstreamer.png" "$APPDIR/.DirIcon"

if [ ! -x "$TOOL" ]; then
  curl -fsSL -o "$TOOL" https://github.com/AppImage/appimagetool/releases/download/continuous/appimagetool-x86_64.AppImage
  chmod +x "$TOOL"
fi
ARCH=x86_64 "$TOOL" --appimage-extract-and-run --no-appstream "$APPDIR" "$DIST/PNGStreamer-$VERSION-x86_64.AppImage"
