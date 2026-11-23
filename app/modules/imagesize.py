"""Read image dimensions from file headers (PNG, GIF, JPEG, WebP) without Qt or Pillow,
so the engine can work in the server thread."""
import struct
from pathlib import Path
from typing import Optional, Tuple


def image_size(path: Path) -> Optional[Tuple[int, int]]:
    try:
        with open(path, "rb") as handle:
            head = handle.read(32)
            if head.startswith(b"\x89PNG\r\n\x1a\n") and head[12:16] == b"IHDR":
                return struct.unpack(">II", head[16:24])
            if head[:6] in (b"GIF87a", b"GIF89a"):
                return struct.unpack("<HH", head[6:10])
            if head[:4] == b"RIFF" and head[8:12] == b"WEBP":
                return _webp(head, handle)
            if head[:2] == b"\xff\xd8":
                handle.seek(2)
                return _jpeg(handle)
    except (OSError, struct.error):
        return None
    return None


def _webp(head: bytes, handle) -> Optional[Tuple[int, int]]:
    chunk = head[12:16]
    if chunk == b"VP8X":
        w = int.from_bytes(head[24:27], "little") + 1
        h = int.from_bytes(head[27:30], "little") + 1
        return w, h
    handle.seek(20)
    data = handle.read(10)
    if chunk == b"VP8 " and len(data) >= 10:
        w, h = struct.unpack("<HH", data[6:10])
        return w & 0x3FFF, h & 0x3FFF
    if chunk == b"VP8L" and len(data) >= 5:
        bits = int.from_bytes(data[1:5], "little")
        return (bits & 0x3FFF) + 1, ((bits >> 14) & 0x3FFF) + 1
    return None


def _jpeg(handle) -> Optional[Tuple[int, int]]:
    while True:
        marker = handle.read(2)
        if len(marker) < 2 or marker[0] != 0xFF:
            return None
        kind = marker[1]
        if kind in (0xD8, 0x01) or 0xD0 <= kind <= 0xD7:
            continue
        length = struct.unpack(">H", handle.read(2))[0]
        if 0xC0 <= kind <= 0xCF and kind not in (0xC4, 0xC8, 0xCC):
            data = handle.read(5)
            h, w = struct.unpack(">HH", data[1:5])
            return w, h
        handle.seek(length - 2, 1)
