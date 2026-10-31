import json
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
    assert _read(data / "profiles.json") == _read(REAL_DEFAULTS_DIR / "profiles.json")
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
