# Third-party software

PNG Streamer itself is distributed under the MIT License (see `LICENSE`).
Binary builds bundle the following components.

| Component | License | Source |
|---|---|---|
| Qt 6 (QtCore, QtGui, QtWidgets, QtNetwork, QtDBus, QtSvg and platform plugins) | LGPL-3.0 (`LGPL-3.0.txt`, `GPL-3.0.txt`) | https://download.qt.io/official_releases/qt/ |
| PySide6 / Shiboken6 | LGPL-3.0 | https://code.qt.io/cgit/pyside/pyside-setup.git/ |
| Inter font | SIL Open Font License 1.1 (`app/assets/fonts/OFL.txt`) | https://github.com/rsms/inter |
| Python | PSF License | https://www.python.org/ |
| NumPy | BSD-3-Clause | https://github.com/numpy/numpy |
| python-sounddevice | MIT | https://github.com/spatialaudio/python-sounddevice |
| PortAudio | MIT | https://github.com/PortAudio/portaudio |
| FastAPI | MIT | https://github.com/fastapi/fastapi |
| Starlette | BSD-3-Clause | https://github.com/encode/starlette |
| Pydantic | MIT | https://github.com/pydantic/pydantic |
| Uvicorn | BSD-3-Clause | https://github.com/encode/uvicorn |
| AnyIO | MIT | https://github.com/agronholm/anyio |
| h11 | MIT | https://github.com/python-hyper/h11 |
| CFFI | MIT-0 | https://github.com/python-cffi/cffi |

## Qt under the LGPL

Qt and PySide6 are used unmodified and are linked dynamically: the Qt libraries
are shipped as separate files next to the program (`Qt6*.dll` on Windows,
`libQt6*.so*` inside the AppImage, which can be unpacked with
`--appimage-extract`). You may replace them with your own compatible build of
the same Qt/PySide6 version. The exact versions are shown in
Settings → About. The corresponding source code is available from the links
above; on request we will also provide it ourselves.
