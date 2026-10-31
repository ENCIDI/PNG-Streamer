import socket

import pytest
from PySide6.QtWidgets import QApplication

from app.modules import audio_manager as am, logic_manager as lm, storage_manager as sm, web_manager as wm
from app.ui import i18n, theme
from app.ui.widgets import dialogs


@pytest.fixture(scope="session")
def qt_app():
    app = QApplication.instance() or QApplication([])
    theme.apply(app)
    return app


@pytest.fixture
def application(qt_app, env, monkeypatch):
    monkeypatch.setattr(am, "start_monitor", lambda device_id=None: None)
    monkeypatch.setattr(am, "get_current_volume", lambda: 50.0)
    sm.init_storage()
    i18n.set_language("ru")
    from app.ui.app import Application

    app = Application(qt_app, launched_by_autostart=False, self_test=True)
    yield app
    wm.stop_server()
    app.window.allow_close = True
    app.window.close()
    app.window.deleteLater()
    qt_app.processEvents()


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def test_all_screens_build_and_switch(application, qt_app):
    window = application.window
    for index in range(len(window.screens)):
        window.show_page(index)
        qt_app.processEvents()
        assert window.pages.currentIndex() == index


def test_image_profile_edit_save_and_revert(application, qt_app):
    screen = application.window.screens[2]
    application.window.show_page(2)
    assert not screen.is_dirty()

    screen._rows[1].threshold.slider.setValue(35)
    assert screen.is_dirty()
    assert screen.save_button.isEnabled()

    screen.save()
    assert not screen.is_dirty()
    levels = [img["volume-level"] for img in sm.get_profile_by_id(1)["images"]]
    assert levels == [0, 35, 80]

    screen._rows[0].shake.slider.setValue(40)
    screen.revert()
    assert not screen.is_dirty()
    assert screen._rows[0].shake.value() == 0


def test_image_frames_add_remove(application):
    screen = application.window.screens[2]
    screen._add_frame()
    assert len(screen._rows) == 4
    assert screen._rows[3].threshold.value() == 100
    screen._remove_frame(screen._rows[0])
    screen.save()
    images = sm.get_profile_by_id(1)["images"]
    assert [img["id"] for img in images] == [0, 1, 2]
    assert [img["volume-level"] for img in images] == [30, 80, 100]


def test_leaving_with_unsaved_changes_asks(application, monkeypatch):
    window = application.window
    window.show_page(2)
    window.screens[2]._rows[0].shake.slider.setValue(10)

    monkeypatch.setattr(dialogs, "ask_save", lambda *a: "cancel")
    window.show_page(0)
    assert window.pages.currentIndex() == 2

    monkeypatch.setattr(dialogs, "ask_save", lambda *a: "discard")
    window.show_page(0)
    assert window.pages.currentIndex() == 0
    assert sm.get_profile_by_id(1)["images"][0]["shake-level"] == 0


def test_profile_create_duplicate_delete(application, monkeypatch):
    screen = application.window.screens[1]
    screen._on_create()
    profiles = sm.list_sound_profiles()
    assert len(profiles) == 2
    new_id = profiles[-1]["id"]
    assert screen._selected_id == new_id

    screen._on_duplicate(new_id)
    assert len(sm.list_sound_profiles()) == 3

    monkeypatch.setattr(dialogs, "confirm", lambda *a, **k: True)
    screen._on_activate(new_id)
    screen._on_delete(new_id)
    remaining = sm.list_sound_profiles()
    assert new_id not in [p["id"] for p in remaining]
    assert application.state.active_sound_profile_id() == remaining[0]["id"]


def test_sound_profile_save(application):
    screen = application.window.screens[1]
    screen.noise_switch.switch.setChecked(True)
    screen.noise_switch.switch.toggled.emit(True)
    assert screen.is_dirty()
    screen.save()
    assert sm.get_sound_profile_by_id(1)["unnoised"] is True


def test_server_start_stop_from_state(application):
    state = application.state
    port = _free_port()
    assert state.start_server(port)
    assert state.server_running()
    assert state.widget_url() == f"http://127.0.0.1:{port}/widget"
    launch = application.window.screens[0]
    assert launch.url.text() == state.widget_url()
    assert not launch.port.isEnabled()
    state.stop_server()
    assert not state.server_running()
    assert launch.port.isEnabled()


def test_language_switch(application):
    application.state.set_language("en")
    assert application.window.nav_buttons[0].text().strip() == "Launch"
    application.state.set_language("ru")
    assert application.window.nav_buttons[0].text().strip() == "Запуск"


def test_import_images(env, tmp_path):
    sm.init_storage()
    source = tmp_path / "new.png"
    source.write_bytes(b"png")
    (tmp_path / "notes.txt").write_text("x")
    assert lm.import_images([source, tmp_path / "notes.txt"]) == ["new.png"]
    assert lm.import_images([source]) == ["new-2.png"]


def test_all_translation_keys_exist():
    import re
    from pathlib import Path

    from app.ui.i18n import _TRANSLATIONS

    assert set(_TRANSLATIONS["ru"]) == set(_TRANSLATIONS["en"])
    used = set()
    for file in Path("app").rglob("*.py"):
        used |= set(re.findall(r'i18n\.t\(\s*"([a-z_]+\.[a-z_]+)"', file.read_text(encoding="utf-8")))
    missing = used - set(_TRANSLATIONS["ru"])
    assert not missing
