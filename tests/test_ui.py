import socket

import pytest
from PySide6.QtWidgets import QApplication

from app.modules import audio_manager as am, logic_manager as lm, storage_manager as sm, web_manager as wm
from app import features
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
        if not features.STUDIO and ("studio" in file.parts or file.name == "i18n_studio.py"):
            continue
        used |= set(re.findall(r'i18n\.t\(\s*"([a-z_]+\.[a-z_]+)"', file.read_text(encoding="utf-8")))
    missing = used - set(_TRANSLATIONS["ru"])
    assert not missing


def test_locale_files_match_english():
    import json
    import re
    from pathlib import Path

    from app.ui import i18n

    english = i18n._TRANSLATIONS["en"]
    placeholders = lambda text: set(re.findall(r"\{\w*\}", text))
    folders = [Path("app/assets/locales")] + ([Path("app/studio/locales")] if features.STUDIO else [])
    for file in [f for folder in folders for f in folder.glob("*.json")]:
        table = json.loads(file.read_text(encoding="utf-8"))
        assert file.stem in i18n.LANGUAGE_NAMES and file.stem in i18n.LANGUAGES
        assert not set(table) - set(english), file.stem
        for key, text in table.items():
            assert placeholders(text) == placeholders(english[key]), (file.stem, key)


def test_onboarding_with_own_images(application, qt_app, tmp_path, monkeypatch):
    from app.modules import calibration
    from app.ui.onboarding import OnboardingDialog

    files = []
    for name in ("b_talk.png", "a_idle.png"):
        path = tmp_path / name
        path.write_bytes((sm.paths.IMAGES_DIR / "image0.png").read_bytes())
        files.append(path)
    monkeypatch.setattr(application.state, "start_server", lambda port=None: True)
    dialog = OnboardingDialog(application.window, application.state)
    dialog._go(2)
    dialog._add_images(files)
    assert dialog._own_images == ["a_idle.png", "b_talk.png"]
    dialog._on_calibrated(calibration.Calibration(noise_level=5, gate=12, thresholds=[0, 37]))
    dialog._finish()

    active = application.state.active_image_profile()
    frames = active["images"]
    assert [(f["path-to-image"], f["volume-level"]) for f in frames] == [("a_idle.png", 0), ("b_talk.png", 37)]
    assert sm.get_sound_profile_by_id(1)["noise-threshold"] == 12.0
    assert application.state.settings()["onboarding-done"] is True


def test_import_pack_from_screen(application, tmp_path):
    from app.modules import avatar_pack

    pack = avatar_pack.export_pack(sm.get_profile_by_id(1), tmp_path / "sample")
    screen = application.window.screens[2]
    screen.import_pack(pack)

    names = [p["name"] for p in sm.list_profiles()]
    assert names == ["sample", "sample (2)"]
    assert screen._selected_id == sm.list_profiles()[1]["id"]


def test_widget_socket_on_live_server(application):
    import asyncio
    import json

    import websockets

    port = _free_port()
    assert application.state.start_server(port)

    async def receive():
        async with websockets.connect(f"ws://127.0.0.1:{port}/ws") as ws:
            return json.loads(await ws.recv()), json.loads(await ws.recv())

    profile, state = asyncio.run(receive())
    application.state.stop_server()
    assert profile["type"] == "simple" and profile["images"]
    assert state["type"] == "state" and state["image"] in ("image2.png", "image1.png"), "talking frame or its blink"


def test_panel_layout_editor(application, qt_app):
    from app.modules import panel_layout as pl

    screen = application.window.screens[4]
    application.window.show_page(4)
    screen.show_tab(0)
    model = screen.editor.model
    assert model.auto and sm.load_settings()["settings"]["panel-layout"] is None

    first = model.add({"type": "meter"})
    assert not model.auto, "the first change makes the layout the user's own"
    second = model.add({"type": "button", "action": "profile", "target": 1}, at=(3, 3))
    page = model.page()
    assert model.item(second)["x"] == 3 and model.item(second)["y"] == 3
    assert not model.update_item(second, x=model.item(first)["x"], y=model.item(first)["y"]), "no overlapping"
    assert model.update_item(second, x=0, y=5)
    model.update_item(second, merge="text", label="Л")
    model.update_item(second, merge="text", label="Лис")
    assert model.item(second)["label"] == "Лис"
    model.undo()
    assert model.item(second)["label"] == "", "typing is one undo step"
    model.redo()
    model.save()
    stored = sm.load_settings()["settings"]["panel-layout"]
    assert any(i.get("label") == "Лис" for i in stored["pages"][0]["items"])

    model.set_cols(2)
    assert all(i["x"] + i["w"] <= 2 for i in model.page()["items"])
    model.add_page()
    assert model.page_index == 1 and len(model.layout["pages"]) == 2
    model.reset_auto()
    assert model.auto and sm.load_settings()["settings"]["panel-layout"] is None
    del page, pl
    chat_screen = application.window.screens[3]
    application.window.show_page(3)
    qt_app.processEvents()
    assert chat_screen.preview.sample, "sample messages until the chat has some"


def test_grid_canvas_mouse_move_and_resize(application, qt_app):
    from PySide6.QtCore import QPoint, Qt
    from PySide6.QtTest import QTest

    screen = application.window.screens[4]
    application.window.show_page(4)
    screen.show_tab(0)
    application.window.resize(1280, 800)
    application.window.show()
    qt_app.processEvents()
    model, canvas = screen.editor.model, screen.editor.canvas
    for item in list(model.page()["items"]):  # start from an empty grid
        model.delete(item["id"])
    item_id = model.add({"type": "meter"}, at=(0, 0))
    model.update_item(item_id, w=1, h=1)
    qt_app.processEvents()

    def center(x, y):
        return canvas.rect_of(x, y, 1, 1).center().toPoint()

    QTest.mousePress(canvas, Qt.LeftButton, Qt.NoModifier, center(0, 0))
    QTest.mouseMove(canvas, center(1, 0))
    QTest.mouseMove(canvas, center(2, 1))
    QTest.mouseRelease(canvas, Qt.LeftButton, Qt.NoModifier, center(2, 1))
    assert (model.item(item_id)["x"], model.item(item_id)["y"]) == (2, 1)

    handle = canvas._handle(model.item(item_id)).center().toPoint()
    QTest.mousePress(canvas, Qt.LeftButton, Qt.NoModifier, handle)
    QTest.mouseMove(canvas, center(3, 2) + QPoint(0, 0))
    QTest.mouseRelease(canvas, Qt.LeftButton, Qt.NoModifier, center(3, 2))
    assert (model.item(item_id)["w"], model.item(item_id)["h"]) == (2, 2)

    canvas.setFocus()
    QTest.keyClick(canvas, Qt.Key_Delete)
    assert model.item(item_id) is None
    model.undo()
    assert model.item(item_id) is not None


