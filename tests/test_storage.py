import json
import os
from pathlib import Path

from app import paths
from app.modules import storage_manager as sm

REAL_DEFAULTS_DIR = paths.DEFAULTS_DIR


def _write(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")


def _read(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_fresh_install_seeds_defaults(env):
    sm.init_storage()

    data = env / "data"
    assert _read(data / "settings.json")["schema-version"] == sm.SCHEMA_VERSION
    seeded = _read(data / "profiles.json")["profiles"]
    shipped = _read(REAL_DEFAULTS_DIR / "profiles.json")["profiles"]
    assert seeded == [sm.normalize_image_profile(p) for p in shipped]
    assert seeded[0]["mode"] == "simple"
    assert sm.list_sound_profiles()[0]["name"] == "default"
    assert sorted(p.name for p in (data / "images").iterdir()) == sorted(
        p.name for p in (REAL_DEFAULTS_DIR / "images").iterdir()
    )
    assert not (data / "backups").exists()


def test_legacy_data_is_migrated(env):
    legacy = env / "app" / "storage"
    _write(legacy / "settings.json", {"settings": {"server-port": 9000, "custom": "keep"}})
    _write(legacy / "profiles.json", {"profiles": [{"id": 7, "name": "mine", "images": []}]})
    _write(legacy / "sound_profiles.json", {"sound-profiles": [{"id": 3, "name": "loud"}]})
    (env / "images").mkdir()
    (env / "images" / "me.png").write_bytes(b"png")

    sm.init_storage()

    settings = sm.load_settings()
    assert settings["schema-version"] == sm.SCHEMA_VERSION
    assert settings["settings"]["server-port"] == 9000
    assert settings["settings"]["custom"] == "keep"
    assert [p["name"] for p in sm.list_profiles()] == ["mine"]
    assert [p["name"] for p in sm.list_sound_profiles()] == ["loud"]
    assert [p.name for p in (env / "data" / "images").iterdir()] == ["me.png"]
    assert (legacy / "settings.json").exists(), "legacy files must be left in place"

    backups = list((env / "data" / "backups").iterdir())
    assert len(backups) == 1
    assert _read(backups[0] / "settings.json") == {"settings": {"server-port": 9000, "custom": "keep"}}


def test_existing_data_wins_over_legacy(env):
    _write(env / "data" / "settings.json", {"schema-version": sm.SCHEMA_VERSION, "settings": {"server-port": 1111}})
    _write(env / "app" / "storage" / "settings.json", {"settings": {"server-port": 2222}})

    sm.init_storage()

    assert sm.load_settings()["settings"]["server-port"] == 1111


def test_init_is_idempotent(env):
    sm.init_storage()
    sm.update_settings({"server-port": 5555})
    sm.init_storage()

    assert sm.load_settings()["settings"]["server-port"] == 5555


def test_missing_fields_are_filled_from_defaults(env):
    _write(env / "data" / "settings.json", {"settings": {"server-port": 9000}})
    _write(env / "data" / "profiles.json", {"profiles": [{"id": 1, "name": "p", "images": [], "blink": {"duration-ms": 50}}]})
    _write(env / "data" / "sound_profiles.json", {"sound-profiles": [{"id": 1, "name": "s", "unnoised": True}]})

    assert sm.load_settings()["settings"]["minimize-to-tray-on-close"] is True

    blink = sm.get_profile_by_id(1)["blink"]
    assert blink == {"interval-min-ms": 2000, "interval-max-ms": 5000, "duration-ms": 50}
    assert sm.get_profile_by_id(1)["mode"] == "simple"
    assert sm.get_profile_by_id(1)["blink-images"] == []

    sound = sm.get_sound_profile_by_id(1)
    assert sound["unnoised"] is True
    assert sound["compressor-ratio"] == 4.0


def test_defaults_are_not_mutated(env):
    sm.update_settings({"server-port": 1234})

    assert sm.DEFAULT_SETTINGS["settings"]["server-port"] == 8642


def test_broken_json_is_moved_aside(env):
    settings_path = env / "data" / "settings.json"
    settings_path.parent.mkdir(parents=True)
    settings_path.write_text("{not json", encoding="utf-8")

    assert sm.load_settings() == sm.DEFAULT_SETTINGS
    assert not settings_path.exists()
    assert len(list(settings_path.parent.glob("settings.json.broken-*"))) == 1


def test_save_leaves_no_temp_files(env):
    sm.update_settings({"server-port": 4321})

    assert [p.name for p in (env / "data").iterdir()] == ["settings.json"]


def test_backups_are_pruned(env, monkeypatch):
    monkeypatch.setattr(sm, "_MAX_BACKUPS", 2)
    sm.update_settings({"server-port": 1})
    for label in ("a", "b", "c"):
        sm.backup_data(label)

    names = sorted(p.name for p in (env / "data" / "backups").iterdir())
    assert [n.rsplit("-", 1)[1] for n in names] == ["b", "c"]


def test_schema_1_profiles_stay_simple(env):
    legacy = {
        "profiles": [
            {
                "id": 1,
                "name": "old",
                "images": [{"id": 0, "path-to-image": "a.png", "volume-level": 0, "shake-level": 0}],
                "blink": {"interval-min-ms": 1000, "interval-max-ms": 2000, "duration-ms": 90},
                "blink-images": [{"id": 0, "path-to-image": "b.png"}],
            }
        ]
    }
    _write(env / "data" / "settings.json", {"schema-version": 1, "settings": {"server-port": 9000}})
    _write(env / "data" / "profiles.json", legacy)
    _write(env / "data" / "sound_profiles.json", {"sound-profiles": []})

    sm.init_storage()

    stored = _read(env / "data" / "profiles.json")["profiles"][0]
    assert stored["mode"] == "simple"
    assert stored["images"] == legacy["profiles"][0]["images"]
    assert stored["blink-images"] == legacy["profiles"][0]["blink-images"]
    settings = sm.load_settings()
    assert settings["schema-version"] == sm.SCHEMA_VERSION == 4
    assert settings["settings"]["onboarding-done"] is True, "existing users skip the first-run wizard"


def test_dev_expressions_format_is_flattened(env):
    dev = {"profiles": [{"id": 1, "name": "dev", "mode": "advanced", "animation": {"bounce": 50},
                         "expressions": [{"id": 0, "images": [{"id": 0, "path-to-image": "x.png"}],
                                          "blink-images": [{"id": 0, "path-to-image": "y.png"}]},
                                         {"id": 1, "images": []}]}]}
    _write(env / "data" / "settings.json", {"schema-version": 2, "settings": {}})
    _write(env / "data" / "profiles.json", dev)
    _write(env / "data" / "sound_profiles.json", {"sound-profiles": []})

    sm.init_storage()

    stored = _read(env / "data" / "profiles.json")["profiles"][0]
    assert stored["mode"] == "simple", "advanced without an avatar project falls back"
    assert "expressions" not in stored and "animation" not in stored
    assert stored["images"][0]["path-to-image"] == "x.png"
    assert stored["blink-images"][0]["path-to-image"] == "y.png"


def test_advanced_profiles_keep_frames_and_avatar():
    profile = sm.normalize_image_profile({"id": 3, "name": "s", "mode": "advanced", "avatar": "ab12",
                                          "images": [{"id": 0, "path-to-image": "x.png"}]})
    assert profile["mode"] == "advanced" and profile["avatar"] == "ab12"
    assert profile["images"], "frames survive for switching back to simple"
    back = sm.normalize_image_profile({**profile, "mode": "simple"})
    assert back["mode"] == "simple" and back["avatar"] == "ab12"


def test_fresh_install_shows_onboarding(env):
    sm.init_storage()

    assert sm.load_settings()["settings"]["onboarding-done"] is False
    assert sm.list_profiles()[0]["images"]


def test_create_profile_normalizes(env):
    sm.init_storage()

    created = sm.create_profile("new", {"images": [{"id": 0, "path-to-image": "x.png", "volume-level": 0}]})

    assert created["id"] == 2 and created["mode"] == "simple"
    assert created["images"][0]["path-to-image"] == "x.png"
    assert sm.get_profile_by_id(2)["name"] == "new"


def test_locked_file_is_not_treated_as_broken(env, monkeypatch):
    sm.update_settings({"server-port": 9001})
    sm.load_settings()
    path = sm._settings_path()
    real = Path.read_text

    def locked(self, *args, **kwargs):
        if self == path:
            raise PermissionError(13, "locked")
        return real(self, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", locked)
    monkeypatch.setattr(sm.time, "sleep", lambda _: None)
    os.utime(path, None)  # invalidate the cache signature
    assert sm.load_settings()["settings"]["server-port"] == 9001
    assert path.exists()
    assert not list(path.parent.glob("settings.json.broken-*"))


