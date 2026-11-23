import json
import zipfile

import pytest

from app.modules import avatar_pack, calibration, storage_manager as sm


# --- calibration -------------------------------------------------------------
def test_calibration_sets_gate_above_noise_and_spreads_thresholds():
    silence = [8, 9, 10, 11, 12] * 20
    speech = [5] * 20 + list(range(30, 90)) * 3

    result = calibration.analyze(silence, speech, frame_count=4)

    assert result.gate == round(calibration.percentile(silence, 95) + calibration.GATE_MARGIN)
    assert result.thresholds[0] == 0
    assert len(result.thresholds) == 4
    assert all(b - a >= calibration.MIN_STEP for a, b in zip(result.thresholds, result.thresholds[1:]))
    assert result.thresholds[-1] <= 100


def test_calibration_with_single_frame():
    assert calibration.analyze([5] * 30, list(range(40, 80)), 1).thresholds == [0]


def test_calibration_rejects_silence_as_speech():
    with pytest.raises(calibration.CalibrationError):
        calibration.analyze([20] * 50, [21] * 50, 3)


def test_gated_matches_audio_manager():
    from app.modules import audio_manager as am

    for level in (0, 10, 25, 50, 99):
        assert calibration.gated(level, 20) == pytest.approx(am._apply_fixed_gate(level, 20))


# --- avatar packs: simple profiles ---------------------------------------------
@pytest.fixture
def library(env):
    sm.init_storage()
    for name in ("a.png", "b.png", "c.png"):
        (sm.paths.IMAGES_DIR / name).write_bytes(name.encode())
    return sm.create_profile(
        "Fox",
        {
            "images": [
                {"id": 0, "path-to-image": "a.png", "volume-level": 0},
                {"id": 1, "path-to-image": "b.png", "volume-level": 40},
            ],
            "blink-images": [{"id": 0, "path-to-image": "c.png"}],
        },
    )


def test_pack_roundtrip(library, tmp_path):
    pack = avatar_pack.export_pack(library, tmp_path / "fox")
    assert pack.name == "fox.pga"
    with zipfile.ZipFile(pack) as archive:
        assert sorted(archive.namelist()) == ["images/a.png", "images/b.png", "images/c.png", "manifest.json"]
        assert json.loads(archive.read("manifest.json"))["kind"] == "simple"

    imported = avatar_pack.import_pack(pack)

    assert imported["name"] == "Fox (2)"
    assert imported["mode"] == "simple"
    assert [f["path-to-image"] for f in imported["images"]] == ["a.png", "b.png"], "identical images reused"


def test_pack_renames_clashing_images(library, tmp_path):
    pack = avatar_pack.export_pack(library, tmp_path / "fox.pga")
    (sm.paths.IMAGES_DIR / "a.png").write_bytes(b"different")

    imported = avatar_pack.import_pack(pack)

    new_name = imported["images"][0]["path-to-image"]
    assert new_name == "a-2.png"
    assert (sm.paths.IMAGES_DIR / new_name).read_bytes() == b"a.png"


def _write_pack(path, manifest, files):
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("manifest.json", json.dumps(manifest))
        for name, data in files.items():
            archive.writestr(name, data)


def test_pack_rejects_bad_files(env, tmp_path):
    sm.init_storage()
    not_zip = tmp_path / "x.pngavatar"
    not_zip.write_text("hello")
    with pytest.raises(avatar_pack.PackError):
        avatar_pack.import_pack(not_zip)

    wrong = tmp_path / "wrong.pngavatar"
    _write_pack(wrong, {"format": "other", "profile": {}}, {})
    with pytest.raises(avatar_pack.PackError):
        avatar_pack.import_pack(wrong)


def test_pack_never_writes_outside_images(env, tmp_path):
    sm.init_storage()
    evil = tmp_path / "evil.pngavatar"
    profile = {"images": [{"id": 0, "path-to-image": "../../evil.png"}]}
    _write_pack(
        evil,
        {"format": "pngstreamer-avatar", "format-version": 1, "name": "evil", "profile": profile},
        {"images/evil.png": b"x", "../evil.png": b"x"},
    )

    imported = avatar_pack.import_pack(evil)

    assert imported["images"][0]["path-to-image"] == "evil.png"
    assert (sm.paths.IMAGES_DIR / "evil.png").exists()
    assert not (sm.paths.DATA_DIR.parent / "evil.png").exists()


# --- avatar packs: Studio projects ---------------------------------------------


