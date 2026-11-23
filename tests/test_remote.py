import pytest
from fastapi.testclient import TestClient

from app.modules import lan, storage_manager as sm, twitch_chat as tc, web_manager as wm

LOCAL = ("127.0.0.1", 5000)
PHONE = ("192.168.1.50", 5000)


@pytest.fixture
def data(env):
    sm.init_storage()


def test_local_requests_need_no_token(data):
    client = TestClient(wm._APP, client=LOCAL)
    assert client.get("/api/status").json()["ok"]
    assert client.get("/panel").status_code == 200


def test_network_requests_are_refused_while_lan_is_off(data):
    client = TestClient(wm._APP, client=PHONE)
    assert client.get("/api/status").status_code == 403
    assert client.get(f"/panel?token={lan.token()}").status_code == 403


def test_pairing_with_token_sets_cookie(data):
    sm.update_settings({"lan-access": True})
    client = TestClient(wm._APP, client=PHONE)
    assert client.get("/panel").status_code == 403
    assert client.get("/api/status").status_code == 403
    assert client.get("/panel?token=wrong").status_code == 403

    paired = client.get(f"/panel?token={lan.token()}", follow_redirects=False)
    assert paired.status_code == 303 and paired.headers["location"] == "/panel"
    assert lan.COOKIE in paired.cookies
    client.cookies.set(lan.COOKIE, paired.cookies[lan.COOKIE])
    assert client.get("/panel").status_code == 200
    assert client.post("/api/profile/1").json()["ok"]
    assert client.get("/panel/assets/icon-192.png").status_code == 200

    lan.reset_token()
    assert client.get("/api/status").status_code == 403, "reset disconnects paired devices"


def test_public_panel_files_without_token(data):
    sm.update_settings({"lan-access": True})
    client = TestClient(wm._APP, client=PHONE)
    assert client.get("/panel/manifest.json").json()["start_url"] == "/panel"
    assert client.get("/panel/assets/nosleep.mp4").status_code == 403, "only icons and the manifest are public"


def test_panel_socket_sends_state(data):
    client = TestClient(wm._APP, client=LOCAL)
    with client.websocket_connect("/panel/ws") as ws:
        state = ws.receive_json()
    assert state["type"] == "state" and state["profiles"][0]["name"] == "sample"
    assert state["advanced"] is False and state["chat_enabled"] is False


def test_sockets_refuse_unpaired_devices(data):
    sm.update_settings({"lan-access": True})
    client = TestClient(wm._APP, client=PHONE)
    for path in ("/panel/ws", "/chat/ws", "/ws"):
        with pytest.raises(Exception):
            with client.websocket_connect(path) as ws:
                ws.receive_json()


def test_addresses_and_urls(data, monkeypatch):
    for address in lan.addresses():
        assert lan._usable(address)
    assert lan.panel_url("192.168.1.5", 8642).startswith("http://192.168.1.5:8642/panel?token=")
    assert lan.is_local("127.0.0.1") and lan.is_local("::1") and not lan.is_local("192.168.1.5")
    assert not lan._usable("169.254.1.1") and not lan._usable("8.8.8.8") and lan._usable("10.0.0.7")
    matrix = lan.qr_matrix("http://192.168.1.5:8642/panel?token=abc")
    assert len(matrix) == len(matrix[0]) >= 21


# --- Twitch chat parsing -----------------------------------------------------------
LINE = ("@badge-info=;color=#1E90FF;display-name=Ник;emotes=25:6-10;id=abc-1;tmi-sent-ts=1 "
        ":nick!nick@nick.tmi.twitch.tv PRIVMSG #chan :hello Kappa !")


def test_parse_privmsg_with_emotes():
    message = tc.message_from(tc.parse_line(LINE))
    assert message["name"] == "Ник" and message["color"] == "#1E90FF" and message["id"] == "abc-1"
    assert [f["type"] for f in message["fragments"]] == ["text", "emote", "text"]
    assert message["fragments"][1]["text"] == "Kappa" and "/25/" in message["fragments"][1]["url"]


def test_action_and_default_color():
    line = ":bob!bob@bob PRIVMSG #chan :\x01ACTION waves\x01"
    message = tc.message_from(tc.parse_line(line))
    assert message["action"] and message["text"] == "waves" and message["color"].startswith("#")


def test_moderation_removes_messages():
    chat = tc.TwitchChat()

    class Sock:
        def sendall(self, data):
            self.sent = data

    sock = Sock()
    chat._handle(sock, LINE)
    chat._handle(sock, LINE.replace("id=abc-1", "id=abc-2").replace("nick!", "eve!"))
    assert len(chat.snapshot()) == 2
    chat._handle(sock, "@target-msg-id=abc-1 :tmi.twitch.tv CLEARMSG #chan :hello")
    assert [m["id"] for m in chat.snapshot()] == ["abc-2"]
    chat._handle(sock, ":tmi.twitch.tv CLEARCHAT #chan :eve")
    assert chat.snapshot() == []
    chat._handle(sock, "PING :tmi.twitch.tv")
    assert sock.sent == b"PONG :tmi.twitch.tv\r\n"


def test_chat_overlay_page_uses_settings(data):
    sm.update_settings({"chat-max": 7, "chat-fade-seconds": 0, "chat-font-size": 30})
    page = TestClient(wm._APP, client=LOCAL).get("/chat").text
    assert "let MAX = 7, FADE = 0 * 1000" in page and "--font: 30px; --bg: 0.72;" in page


def test_chat_filters_bots_and_commands():
    messages = [
        tc.message_from(tc.parse_line(f"@display-name={name} :{name.lower()}!x@x PRIVMSG #c :{text}"))
        for name, text in (("Nightbot", "Follow!"), ("Viewer", "!discord"), ("Viewer", "hi"))
    ]
    settings = {"chat-hidden-users": "NightBot, @someone", "chat-hide-commands": False}
    assert [m["text"] for m in tc.visible(messages, settings)] == ["!discord", "hi"]
    settings["chat-hide-commands"] = True
    assert [m["text"] for m in tc.visible(messages, settings)] == ["hi"]


def test_chat_socket_sends_style_first(data):
    sm.update_settings({"chat-font-size": 26, "chat-bg-opacity": 40})
    with TestClient(wm._APP, client=LOCAL).websocket_connect("/chat/ws") as ws:
        style = ws.receive_json()
    assert style == {"type": "style", "max": 12, "fade": 45, "font": 26, "bg": 0.4}


def test_dark_name_colors_are_lightened():
    assert tc.readable("#000000") != "#000000"
    assert tc.readable("#0000FF") != "#0000FF"
    assert tc.readable("#C8F65A") == "#C8F65A"


# --- panel layout -------------------------------------------------------------------------
_CONTEXT = {
    "params": [
        {"id": "wave", "name": "Wave", "type": "trigger", "min": 0, "max": 1, "hotkey": "", "manual": True},
        {"id": "hat", "name": "Hat", "type": "bool", "min": 0, "max": 1, "hotkey": "F2", "manual": True},
        {"id": "size", "name": "Size", "type": "number", "min": 0, "max": 2, "hotkey": "", "manual": True},
        {"id": "volume", "name": "volume", "type": "number", "min": 0, "max": 1, "hotkey": "", "manual": False},
    ],
    "sequences": [{"id": "dance", "name": "Dance"}],
    "profiles": [{"id": 1, "name": "Fox"}, {"id": 2, "name": "Cat"}],
    "sound_profiles": [{"id": 1, "name": "Mic"}],
}


def _t(key, **kwargs):
    return key


def test_automatic_layout_is_a_grid_of_everything_manual():
    from app.modules import panel_layout as pl

    result = pl.resolve(None, {**_CONTEXT, "chat_enabled": True}, _t)
    assert result["auto"] is True
    main, chat = result["pages"]
    placed = [(w["kind"], w.get("target", w.get("action")), w["x"], w["y"], w["w"], w["h"]) for w in main["widgets"]]
    assert placed == [
        ("button", "wave", 0, 0, 1, 1), ("button", "dance", 1, 0, 1, 1), ("button", "hat", 2, 0, 1, 1),
        ("slider", "size", 0, 1, 4, 1), ("chips", "profile", 0, 2, 4, 1),
    ], "automatic parameters (volume) are never on the panel; one sound profile needs no switcher"
    assert chat["name"] == "panel.chat" and chat["widgets"][0]["kind"] == "chat"
    assert len(pl.resolve(None, _CONTEXT, _t)["pages"]) == 1, "no chat page while the chat is off"


def test_grid_normalize_places_and_resolves():
    from app.modules import panel_layout as pl

    layout = {"pages": [
        {"name": "Main", "cols": 3, "items": [
            {"id": "a", "type": "button", "action": "param", "target": "wave", "label": "Hi!", "color": "#FF6B6B",
             "x": 0, "y": 0, "w": 2, "h": 2},
            {"id": "b", "type": "button", "action": "param", "target": "gone", "x": 2, "y": 0},   # not in this avatar
            {"id": "c", "type": "button", "action": "param", "target": "hat", "x": 1, "y": 1},    # overlaps "a"
            {"id": "d", "type": "slider", "target": "size", "h": 3, "w": 1},                      # no position
            {"id": "e", "type": "button", "action": "profile", "target": 2, "color": "#123456"},
            {"type": "bogus"},
            {"id": "f", "type": "label", "text": "", "x": 0, "y": 9},                            # empty text
            {"id": "g", "type": "chat", "x": 0, "y": 10, "w": 3, "h": 2},                         # chat is off
            {"id": "h", "type": "meter", "w": 9},
        ]},
        {"cols": 99},
    ]}
    normal = pl.normalize(layout)
    page = normal["pages"][0]
    spots = {i["id"]: (i["x"], i["y"], i["w"], i["h"]) for i in page["items"]}
    assert spots["a"] == (0, 0, 2, 2) and spots["b"] == (2, 0, 1, 1)
    assert spots["c"] == (2, 1, 1, 1), "an overlapping widget moves to the next free cell"
    assert spots["d"][2:] == (1, 3) and spots["h"][2] == 3, "too wide widgets are clamped to the columns"
    assert normal["pages"][1]["cols"] == pl.MAX_COLS
    for one in page["items"]:
        for other in page["items"]:
            assert one is other or not (pl.cells(one) & pl.cells(other))

    widgets = {w["id"]: w for w in pl.resolve(layout, _CONTEXT, _t)["pages"][0]["widgets"]}
    assert set(widgets) == {"a", "c", "d", "e", "h"}
    assert widgets["a"]["label"] == "Hi!" and widgets["a"]["action"] == "trigger" and widgets["a"]["color"] == "#FF6B6B"
    assert widgets["c"]["action"] == "toggle" and widgets["c"]["sub"] == "F2"
    assert widgets["d"]["kind"] == "slider" and widgets["d"]["max"] == 2
    assert widgets["e"]["label"] == "Cat" and widgets["e"]["color"] == ""
    assert widgets["h"]["kind"] == "meter"


def test_free_spot_and_fits():
    from app.modules import panel_layout as pl

    items = [{"id": "a", "x": 0, "y": 0, "w": 3, "h": 1}]
    assert pl.free_spot(items, 4, 1, 1) == (3, 0)
    assert pl.free_spot(items, 4, 2, 1) == (0, 1)
    assert not pl.fits(items, 4, 2, 0, 2, 1)
    assert pl.fits(items, 4, 0, 0, 3, 1, ignore="a")
    assert not pl.fits(items, 4, 3, 0, 2, 1), "past the last column"


def test_panel_state_uses_saved_layout(data):
    sm.update_settings({"panel-layout": {"pages": [{"name": "Only", "items": [{"type": "profiles"}, {"type": "meter"}]}]},
                        "chat-enabled": True, "twitch-channel": "someone"})
    state = wm.panel_state()
    assert [p["name"] for p in state["pages"]] == ["Only"]
    assert [w["kind"] for w in state["pages"][0]["widgets"]] == ["chips", "meter"]
    assert state["chat_shown"] is False and state["meter_shown"] is True
    with TestClient(wm._APP, client=LOCAL).websocket_connect("/panel/ws") as ws:
        assert ws.receive_json()["type"] == "state"
        assert ws.receive_json()["type"] == "level"
    sm.update_settings({"panel-layout": None})
    assert wm.panel_state()["chat_shown"] is True, "automatic layout gets a chat page"


def test_sockets_end_when_clients_leave(data):
    import time

    client = TestClient(wm._APP, client=LOCAL)
    for path in ("/panel/ws", "/chat/ws", "/ws"):
        with client.websocket_connect(path) as ws:
            ws.receive_json() if path != "/chat/ws" else None
            assert wm._Feed.active >= 1
        deadline = time.monotonic() + 3
        while wm._Feed.active and time.monotonic() < deadline:
            time.sleep(0.05)
        assert wm._Feed.active == 0, f"{path} kept running after the client left"


def test_silent_panel_client_is_dropped(data, monkeypatch):
    import time

    monkeypatch.setattr(wm, "_PANEL_HEARTBEAT_TIMEOUT", 0.6)
    client = TestClient(wm._APP, client=LOCAL)
    with client.websocket_connect("/panel/ws") as ws:
        ws.receive_json()
        deadline = time.monotonic() + 3
        while wm._Feed.active and time.monotonic() < deadline:
            time.sleep(0.05)
        assert wm._Feed.active == 0, "no pings -> the server lets the connection go"


def test_7tv_emotes_replace_whole_words():
    from app.modules import seventv as stv

    emotes = stv.parse_set([
        {"name": "catJAM", "flags": 0, "data": {"flags": 0, "host": {"url": "//cdn.7tv.app/emote/A", "files": [
            {"name": "1x.webp", "format": "WEBP", "width": 32, "height": 32},
            {"name": "2x.webp", "format": "WEBP", "width": 128, "height": 64},
            {"name": "2x.avif", "format": "AVIF", "width": 128, "height": 64}]}}},
        {"name": "RainTime", "flags": 1, "data": {"flags": 256, "host": {"url": "//cdn.7tv.app/emote/B", "files": [
            {"name": "2x.webp", "format": "WEBP", "width": 64, "height": 64}]}}},
        {"name": "broken"},
    ])
    assert emotes["catJAM"] == {"url": "https://cdn.7tv.app/emote/A/2x.webp", "zero_width": False, "ratio": 2.0}
    assert emotes["RainTime"]["zero_width"] and "broken" not in emotes

    message = tc.message_from(tc.parse_line(
        "@display-name=V;emotes=25:0-4 :v!v@v PRIVMSG #c :Kappa hi catJAM RainTime catJAMs  catJAM"))
    out = stv.apply(message, emotes)
    kinds = [(f["type"], f["text"]) for f in out["fragments"]]
    assert kinds == [
        ("emote", "Kappa"), ("text", " hi "), ("emote", "catJAM"), ("text", " "), ("emote", "RainTime"),
        ("text", " catJAMs  "), ("emote", "catJAM"),
    ], "Twitch emotes stay, only whole words match, spacing is kept"
    assert out["fragments"][4]["zero_width"] and out["fragments"][2]["provider"] == "7tv"
    assert stv.apply(message, {}) is message


def test_7tv_toggle_in_visible(monkeypatch):
    from app.modules import seventv as stv

    monkeypatch.setattr(stv.seventv, "emotes", lambda: {"EZ": {"url": "u", "zero_width": False, "ratio": 1}})
    message = tc.message_from(tc.parse_line(":v!v@v PRIVMSG #c :EZ win"))
    assert tc.visible([message], {})[0]["fragments"][0]["type"] == "emote"
    assert tc.visible([message], {"chat-7tv": False})[0]["fragments"][0]["type"] == "text"


def test_roomstate_loads_channel_emotes(monkeypatch):
    from app.modules import seventv as stv

    rooms = []
    monkeypatch.setattr(stv.seventv, "load", lambda room_id, force=False: rooms.append(room_id))
    chat = tc.TwitchChat()
    chat._handle(None, "@emote-only=0;room-id=641972806 :tmi.twitch.tv ROOMSTATE #kaicenat")
    assert rooms == ["641972806"] and chat.room_id == "641972806" and chat.status == "connected"


# --- chat triggers -------------------------------------------------------------------------


def test_avatar_widget_in_the_panel(data):
    from app.modules import panel_layout as pl

    layout = {"pages": [{"cols": 4, "items": [{"type": "avatar", "x": 1, "y": 0}]}]}
    widget = pl.resolve(layout, _CONTEXT, _t)["pages"][0]["widgets"][0]
    assert widget["kind"] == "avatar" and (widget["w"], widget["h"]) == (2, 2)
    page = TestClient(wm._APP, client=LOCAL).get("/panel").text
    assert 'frame.src = "/widget"' in page, "the panel shows the OBS widget itself"
