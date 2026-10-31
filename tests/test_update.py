import pytest

from app.modules import update_manager as um


def _release(tag, assets=("PNGStreamer-Setup-{v}.exe", "SHA256SUMS"), draft=False, prerelease=False):
    version = tag[1:]
    return {
        "tag_name": tag,
        "draft": draft,
        "prerelease": prerelease,
        "body": f"notes {tag}",
        "html_url": f"https://example/{tag}",
        "assets": [
            {"name": name.format(v=version), "browser_download_url": f"https://dl/{tag}/{name.format(v=version)}"}
            for name in assets
        ],
    }


def test_parse_tag():
    assert um.parse_tag("v3.0.0") == (3, 0, 0)
    assert um.parse_tag("v10.2.33") == (10, 2, 33)
    for bad in ("v2", "3.0.0", "v3.0", "v3.0.0-rc1", ""):
        assert um.parse_tag(bad) is None


def test_offers_newest_release_when_current_is_released():
    releases = [_release("v3.0.0"), _release("v3.1.0"), _release("v3.0.5")]

    is_release, update = um.find_update(releases, "3.0.0", "windows")

    assert is_release
    assert update.version == "3.1.0"
    assert update.asset_name == "PNGStreamer-Setup-3.1.0.exe"
    assert update.asset_url == "https://dl/v3.1.0/PNGStreamer-Setup-3.1.0.exe"
    assert update.sums_url == "https://dl/v3.1.0/SHA256SUMS"


def test_does_nothing_when_current_version_is_not_a_release():
    releases = [_release("v3.0.0"), _release("v3.1.0")]

    assert um.find_update(releases, "3.0.1", "windows") == (False, None)


def test_drafts_and_prereleases_are_ignored():
    releases = [
        _release("v3.0.0"),
        _release("v3.2.0", prerelease=True),
        _release("v3.3.0", draft=True),
    ]
    assert um.find_update(releases, "3.0.0", "windows") == (True, None)
    # a version that only exists as a prerelease does not count as released
    assert um.find_update(releases, "3.2.0", "windows") == (False, None)


def test_latest_already_installed():
    assert um.find_update([_release("v3.0.0"), _release("v2.9.0")], "3.0.0", "windows") == (True, None)


def test_release_without_platform_asset_or_sums_is_skipped():
    releases = [_release("v3.0.0"), _release("v3.1.0", assets=("PNGStreamer-Setup-{v}.exe",))]
    assert um.find_update(releases, "3.0.0", "windows") == (True, None)

    releases = [_release("v3.0.0"), _release("v3.1.0")]
    assert um.find_update(releases, "3.0.0", "linux") == (True, None)


def test_linux_asset_name():
    releases = [_release("v3.0.0"), _release("v3.1.0", assets=("PNGStreamer-{v}-x86_64.AppImage", "SHA256SUMS"))]

    _, update = um.find_update(releases, "3.0.0", "linux")

    assert update.asset_name == "PNGStreamer-3.1.0-x86_64.AppImage"


def test_parse_sums():
    digest = "a" * 64
    text = f"{digest}  PNGStreamer-Setup-3.1.0.exe\n{'B' * 64} *PNGStreamer-3.1.0-x86_64.AppImage\ngarbage line\n"

    assert um.parse_sums(text) == {
        "PNGStreamer-Setup-3.1.0.exe": digest,
        "PNGStreamer-3.1.0-x86_64.AppImage": "b" * 64,
    }


def test_source_runs_are_never_eligible(monkeypatch):
    monkeypatch.setattr(um.paths, "is_frozen", lambda: False)

    assert not um.is_eligible()
    assert um.check() == um.CheckResult(eligible=False)


@pytest.mark.parametrize("platform", ["win32", "linux"])
def test_frozen_builds_are_eligible(monkeypatch, platform):
    monkeypatch.setattr(um.paths, "is_frozen", lambda: True)
    monkeypatch.setattr(um.sys, "platform", platform)
    monkeypatch.setenv("APPIMAGE", "/tmp/PNGStreamer.AppImage")

    assert um.is_eligible()
