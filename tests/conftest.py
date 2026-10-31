import os

import pytest

from app import paths

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

REAL_DEFAULTS_DIR = paths.DEFAULTS_DIR


@pytest.fixture
def env(tmp_path, monkeypatch):
    """Point all data locations into a temporary app root."""
    root = tmp_path / "root"
    data = root / "data"
    monkeypatch.setattr(paths, "APP_ROOT", root)
    monkeypatch.setattr(paths, "DATA_DIR", data)
    monkeypatch.setattr(paths, "IMAGES_DIR", data / "images")
    monkeypatch.setattr(paths, "LOGS_DIR", data / "logs")
    monkeypatch.setattr(paths, "BACKUPS_DIR", data / "backups")
    monkeypatch.setattr(paths, "LEGACY_STORAGE_DIR", root / "app" / "storage")
    monkeypatch.setattr(paths, "LEGACY_IMAGES_DIR", root / "images")
    monkeypatch.setattr(paths, "DEFAULTS_DIR", REAL_DEFAULTS_DIR)
    return root
