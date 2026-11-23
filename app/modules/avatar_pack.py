"""Avatar packs: one .pga file (a zip) with an image profile and its images.

    manifest.json   {"format": "pngstreamer-avatar", "format-version": 1, "kind": "simple",
                     "name": ..., "profile": {...}}
    images/<file>   every image the profile references
Other kinds of packs belong to parts of the app that may not be in this copy
(see app/features.py). Hotkeys are personal and are never exported.
"""
import copy
import hashlib
import json
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any, Dict, List

from app import features, paths
from app.modules import logging_manager as logm, logic_manager as lm, storage_manager as sm
from app.version import __version__

_LOGGER = logm.get_logger(__name__)

EXTENSION = ".pga"          # a profile: images or a scene + its controls
LEGACY_EXTENSION = ".pngavatar"  # 3.1 development builds
OPEN_EXTENSIONS = (EXTENSION, LEGACY_EXTENSION)
FORMAT = "pngstreamer-avatar"
FORMAT_VERSION = 1
MAX_FILES = 1000
MAX_TOTAL_BYTES = 400 * 1024 * 1024


class PackError(Exception):
    pass


def _image_items(profile: Dict[str, Any]) -> List[Dict[str, Any]]:
    return [i for i in list(profile.get("images", [])) + list(profile.get("blink-images", [])) if isinstance(i, dict)]


def _with_extension(destination: Path, extension: str = EXTENSION) -> Path:
    destination = Path(destination)
    if destination.suffix.lower() != extension:
        destination = destination.with_name(destination.name + extension)
    destination.parent.mkdir(parents=True, exist_ok=True)
    return destination


def _manifest(kind: str, name: str, **extra: Any) -> str:
    return json.dumps(
        {"format": FORMAT, "format-version": FORMAT_VERSION, "kind": kind, "app-version": __version__, "name": name, **extra},
        ensure_ascii=False,
        indent=2,
    )


def export_pack(profile: Dict[str, Any], destination: Path) -> Path:
    profile = sm.normalize_image_profile(copy.deepcopy(profile))
    destination = _with_extension(destination)
    tmp = destination.with_name(destination.name + ".tmp")
    if lm.is_advanced(profile):
        from app.studio.packs import export_studio

        export_studio(profile, tmp)
    else:
        _export_simple(profile, tmp)
    tmp.replace(destination)
    _LOGGER.info("Avatar exported: %s", destination)
    return destination


def _export_simple(profile: Dict[str, Any], target: Path) -> None:
    archive_names: Dict[str, str] = {}
    used = set()
    for value in lm.referenced_images(profile):
        source = lm.resolve_image_path(value)
        if source is None:
            raise PackError(f"image not found: {value}")
        name, counter = source.name, 2
        while name.lower() in used:
            name = f"{source.stem}-{counter}{source.suffix}"
            counter += 1
        used.add(name.lower())
        archive_names[value] = name
    for item in _image_items(profile):
        item["path-to-image"] = archive_names[item["path-to-image"]]
    profile.pop("id", None)
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("manifest.json", _manifest("simple", profile.get("name", "avatar"), profile=profile))
        for value, name in archive_names.items():
            archive.write(lm.resolve_image_path(value), f"images/{name}")


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _unique_name(base: str) -> str:
    names = {p.get("name") for p in sm.list_profiles()}
    name, counter = base, 2
    while name in names:
        name = f"{base} ({counter})"
        counter += 1
    return name


def _open(source: Path):
    try:
        archive = zipfile.ZipFile(source)
    except (OSError, zipfile.BadZipFile) as error:
        raise PackError("not an avatar file") from error
    infos = archive.infolist()
    if len(infos) > MAX_FILES or sum(i.file_size for i in infos) > MAX_TOTAL_BYTES:
        archive.close()
        raise PackError("avatar file is too large")
    try:
        manifest = json.loads(archive.read("manifest.json").decode("utf-8"))
    except (KeyError, ValueError) as error:
        archive.close()
        raise PackError("manifest.json is missing or broken") from error
    if manifest.get("format") != FORMAT:
        archive.close()
        raise PackError("not an avatar file")
    if int(manifest.get("format-version", 0)) > FORMAT_VERSION:
        archive.close()
        raise PackError("avatar was made by a newer version of PNG Streamer")
    return archive, manifest


def import_pack(source: Path) -> Dict[str, Any]:
    """Unpack into data/ and add a profile for it."""
    try:
        archive = zipfile.ZipFile(source)
    except (OSError, zipfile.BadZipFile) as error:
        raise PackError("not an avatar file") from error
    with archive:
        infos = archive.infolist()
        if len(infos) > MAX_FILES or sum(i.file_size for i in infos) > MAX_TOTAL_BYTES:
            raise PackError("avatar file is too large")
        try:
            manifest = json.loads(archive.read("manifest.json").decode("utf-8"))
        except (KeyError, ValueError) as error:
            raise PackError("manifest.json is missing or broken") from error
        if manifest.get("format") != FORMAT:
            raise PackError("not an avatar file")
        if int(manifest.get("format-version", 0)) > FORMAT_VERSION:
            raise PackError("avatar was made by a newer version of PNG Streamer")
        if manifest.get("kind") == "studio":
            if not features.STUDIO:
                raise PackError("this avatar needs a newer version of PNG Streamer")
            from app.studio.packs import import_studio

            return import_studio(archive, manifest)
        if not isinstance(manifest.get("profile"), dict):
            raise PackError("not an avatar file")
        return _import_simple(archive, manifest)


def _members(archive: zipfile.ZipFile, folder: str) -> Dict[str, zipfile.ZipInfo]:
    return {
        PurePosixPath(i.filename).name: i
        for i in archive.infolist()
        if not i.is_dir() and PurePosixPath(i.filename).parent == PurePosixPath(folder)
    }


def _import_simple(archive: zipfile.ZipFile, manifest: Dict[str, Any]) -> Dict[str, Any]:
    profile = sm.normalize_image_profile(manifest["profile"])
    profile["mode"] = "simple"
    members = _members(archive, "images")
    paths.IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    renamed: Dict[str, str] = {}
    for value in lm.referenced_images(profile):
        name = PurePosixPath(value).name  # never trust paths from the archive
        if name not in members or Path(name).suffix.lower() not in lm.IMAGE_SUFFIXES:
            raise PackError(f"image missing in avatar file: {value}")
        data = archive.read(members[name])
        target = paths.IMAGES_DIR / name
        counter = 2
        while target.exists() and _sha256(target.read_bytes()) != _sha256(data):
            target = paths.IMAGES_DIR / f"{Path(name).stem}-{counter}{Path(name).suffix}"
            counter += 1
        if not target.exists():
            target.write_bytes(data)
        renamed[value] = target.name
    for item in _image_items(profile):
        item["path-to-image"] = renamed[item["path-to-image"]]
    created = sm.create_profile(_unique_name(str(manifest.get("name") or profile.get("name") or "avatar")), profile)
    _LOGGER.info("Avatar imported -> profile %s", created["id"])
    return created
