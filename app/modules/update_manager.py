"""Self-update from GitHub Releases.

Updates are offered only to installed (frozen) builds whose version exactly
matches a published release tag. Source checkouts and builds with versions
that were never released are left alone, so development is never disturbed.
"""
import hashlib
import json
import os
import re
import ssl
import stat
import subprocess
import sys
import tempfile
import threading
import time
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

import certifi

from app import paths
from app.modules import logging_manager as logm, storage_manager as sm
from app.version import __version__

_LOGGER = logm.get_logger(__name__)

REPOSITORY = "ENCIDI/PNG-Streamer"
RELEASES_URL = os.environ.get(
    "PNGSTREAMER_RELEASES_URL", f"https://api.github.com/repos/{REPOSITORY}/releases"
)
CHECK_INTERVAL_SECONDS = 24 * 60 * 60
SUMS_ASSET = "SHA256SUMS"
_TIMEOUT = 15
_CHUNK = 256 * 1024
_TAG_RE = re.compile(r"^v(\d+)\.(\d+)\.(\d+)$")

Version = Tuple[int, int, int]


@dataclass
class UpdateInfo:
    version: str
    notes: str
    page_url: str
    asset_name: str
    asset_url: str
    sums_url: str


class UpdateError(Exception):
    pass


def parse_tag(tag: str) -> Optional[Version]:
    match = _TAG_RE.match(tag or "")
    return tuple(int(part) for part in match.groups()) if match else None


def platform_key() -> Optional[str]:
    if sys.platform == "win32":
        return "windows"
    if sys.platform.startswith("linux") and os.environ.get("APPIMAGE"):
        return "linux"
    return None


def asset_name(version: str, platform: str) -> str:
    if platform == "windows":
        return f"PNGStreamer-Setup-{version}.exe"
    return f"PNGStreamer-{version}-x86_64.AppImage"


def is_eligible() -> bool:
    return paths.is_frozen() and platform_key() is not None


def find_update(releases: List[Dict[str, Any]], current: str, platform: str) -> Tuple[bool, Optional[UpdateInfo]]:
    """Returns (current version is a published release, newer update or None)."""
    published = [
        release
        for release in releases
        if not release.get("draft") and not release.get("prerelease") and parse_tag(release.get("tag_name", ""))
    ]
    current_tag = f"v{current}"
    if not any(release.get("tag_name") == current_tag for release in published):
        return False, None
    current_version = parse_tag(current_tag)
    newer = [r for r in published if parse_tag(r["tag_name"]) > current_version]
    if not newer:
        return True, None
    latest = max(newer, key=lambda r: parse_tag(r["tag_name"]))
    version = latest["tag_name"][1:]
    assets = {asset.get("name"): asset.get("browser_download_url") for asset in latest.get("assets", [])}
    name = asset_name(version, platform)
    if not assets.get(name) or not assets.get(SUMS_ASSET):
        _LOGGER.warning("Release %s has no %s or %s", latest["tag_name"], name, SUMS_ASSET)
        return True, None
    return True, UpdateInfo(
        version=version,
        notes=latest.get("body") or "",
        page_url=latest.get("html_url") or "",
        asset_name=name,
        asset_url=assets[name],
        sums_url=assets[SUMS_ASSET],
    )


def parse_sums(text: str) -> Dict[str, str]:
    sums = {}
    for line in text.splitlines():
        parts = line.strip().split()
        if len(parts) == 2 and re.fullmatch(r"[0-9a-fA-F]{64}", parts[0]):
            sums[parts[1].lstrip("*")] = parts[0].lower()
    return sums


def _ssl_context() -> ssl.SSLContext:
    # A frozen build's OpenSSL looks for CA certificates at the build machine's
    # paths, which do not exist on most Linux distributions. Trust the system
    # store where it is found and the bundled certifi store everywhere.
    context = ssl.create_default_context()
    context.load_verify_locations(cafile=certifi.where())
    return context


def _open(url: str):
    return urllib.request.urlopen(_request(url), timeout=_TIMEOUT, context=_ssl_context())


def _request(url: str) -> urllib.request.Request:
    return urllib.request.Request(
        url,
        headers={"User-Agent": f"PNGStreamer/{__version__}", "Accept": "application/vnd.github+json"},
    )


def fetch_releases() -> List[Dict[str, Any]]:
    with _open(RELEASES_URL) as response:
        return json.loads(response.read().decode("utf-8"))


@dataclass
class CheckResult:
    eligible: bool
    is_release: bool = False
    update: Optional[UpdateInfo] = None
    error: Optional[str] = None


def check() -> CheckResult:
    if not is_eligible():
        return CheckResult(eligible=False)
    try:
        releases = fetch_releases()
    except Exception as error:  # network errors must never break the app
        _LOGGER.warning("Update check failed: %s", error)
        return CheckResult(eligible=True, error=str(error))
    # Only successful checks count, so a failed one is retried on the next start.
    sm.update_settings({"last-update-check": int(time.time())})
    is_release, update = find_update(releases, __version__, platform_key())
    if update:
        _LOGGER.info("Update available: %s", update.version)
    return CheckResult(eligible=True, is_release=is_release, update=update)


def check_due() -> bool:
    settings = sm.load_settings().get("settings", {})
    if not settings.get("check-updates", True):
        return False
    last = int(settings.get("last-update-check", 0) or 0)
    return time.time() - last >= CHECK_INTERVAL_SECONDS


def check_async(callback: Callable[[CheckResult], None]) -> None:
    threading.Thread(target=lambda: callback(check()), daemon=True).start()


def download(
    info: UpdateInfo,
    progress: Callable[[int], None],
    cancelled: Callable[[], bool] = lambda: False,
) -> Path:
    with _open(info.sums_url) as response:
        expected = parse_sums(response.read().decode("utf-8")).get(info.asset_name)
    if not expected:
        raise UpdateError(f"{info.asset_name} is missing from {SUMS_ASSET}")

    if platform_key() == "linux":
        target_dir = Path(os.environ["APPIMAGE"]).parent
    else:
        target_dir = Path(tempfile.gettempdir()) / "PNGStreamer-update"
    target_dir.mkdir(parents=True, exist_ok=True)
    partial = target_dir / f"{info.asset_name}.part"
    digest = hashlib.sha256()
    with _open(info.asset_url) as response, partial.open("wb") as out:
        total = int(response.headers.get("Content-Length") or 0)
        done = 0
        while True:
            if cancelled():
                raise UpdateError("cancelled")
            chunk = response.read(_CHUNK)
            if not chunk:
                break
            out.write(chunk)
            digest.update(chunk)
            done += len(chunk)
            if total:
                progress(int(done * 100 / total))
    if digest.hexdigest() != expected:
        partial.unlink(missing_ok=True)
        raise UpdateError("checksum mismatch")
    final = partial.with_name(info.asset_name)
    os.replace(partial, final)
    progress(100)
    _LOGGER.info("Update downloaded to %s", final)
    return final


def install(info: UpdateInfo, downloaded: Path) -> None:
    """Start installing; the caller must quit the app right after this returns."""
    sm.backup_data(f"pre-{info.version}")
    if platform_key() == "windows":
        # The installer replaces program files only; data/ is left alone.
        # A short delay lets this process exit and release its files first.
        args = subprocess.list2cmdline(
            [str(downloaded), "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART", f"/DIR={paths.APP_ROOT}"]
        )
        subprocess.Popen(
            f'cmd /c ping -n 3 127.0.0.1 >nul & {args}',
            creationflags=subprocess.CREATE_NO_WINDOW | subprocess.DETACHED_PROCESS,
            close_fds=True,
        )
    else:
        appimage = Path(os.environ["APPIMAGE"])
        downloaded.chmod(downloaded.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        os.replace(downloaded, appimage)
        subprocess.Popen([str(appimage)], start_new_session=True, close_fds=True)
    _LOGGER.info("Installing update %s", info.version)
