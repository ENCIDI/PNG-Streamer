from pathlib import Path
from typing import Dict, Optional, Tuple

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QPixmap

_cache: Dict[Tuple[str, int, int], QPixmap] = {}


def load(path: Optional[Path], size: int = 0) -> Optional[QPixmap]:
    """Load an image (optionally scaled to fit size x size), cached until the file changes."""
    if path is None:
        return None
    try:
        mtime = path.stat().st_mtime_ns
    except OSError:
        return None
    key = (str(path), mtime, size)
    cached = _cache.get(key)
    if cached is not None:
        return cached
    pm = QPixmap(str(path))
    if pm.isNull():
        return None
    if size:
        pm = pm.scaled(QSize(size, size), Qt.KeepAspectRatio, Qt.SmoothTransformation)
    if len(_cache) > 256:
        _cache.clear()
    _cache[key] = pm
    return pm
