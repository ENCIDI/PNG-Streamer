"""Access from other devices on the local network (the web control panel).

Off by default. When on, the server listens on all interfaces and every
request that does not come from this computer must carry the access token
(set as a cookie when the QR link is opened)."""
import ipaddress
import secrets
import socket
from typing import List, Optional

from app.modules import storage_manager as sm

COOKIE = "pngs_token"
_LOCAL_HOSTS = {"127.0.0.1", "::1", "localhost"}


def enabled() -> bool:
    return bool(sm.load_settings()["settings"].get("lan-access", False))


def token() -> str:
    """The pairing token; created on first use and kept in settings."""
    current = str(sm.load_settings()["settings"].get("lan-token") or "")
    if len(current) < 16:
        current = secrets.token_urlsafe(18)
        sm.update_settings({"lan-token": current})
    return current


def reset_token() -> str:
    """New token: every paired device has to scan the QR code again."""
    new = secrets.token_urlsafe(18)
    sm.update_settings({"lan-token": new})
    return new


def check_token(value: Optional[str]) -> bool:
    return bool(value) and secrets.compare_digest(str(value), token())


def is_local(host: Optional[str]) -> bool:
    if not host:
        return False
    if host in _LOCAL_HOSTS:
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def _usable(address: str) -> bool:
    try:
        ip = ipaddress.ip_address(address)
    except ValueError:
        return False
    return ip.version == 4 and ip.is_private and not ip.is_loopback and not ip.is_link_local


def addresses() -> List[str]:
    """IPv4 addresses other devices can use to reach this computer, best first.

    The first one is the address of the interface that routes to the internet
    (found by "connecting" a UDP socket — no packet is sent), which is what a
    phone on the same Wi-Fi needs; nobody has to look it up in the router."""
    found: List[str] = []
    for target in ("8.8.8.8", "192.168.0.1", "10.0.0.1"):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as probe:
                probe.connect((target, 80))
                address = probe.getsockname()[0]
            if _usable(address) and address not in found:
                found.append(address)
                break
        except OSError:
            continue
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            address = info[4][0]
            if _usable(address) and address not in found:
                found.append(address)
    except OSError:
        pass
    # Home networks (192.168.x.x) before VPN/virtual adapters (10.x, 172.16-31.x).
    primary, rest = found[:1], found[1:]
    rest.sort(key=lambda a: (not a.startswith("192.168."), a))
    return primary + rest


def panel_url(address: str, port: int, with_token: bool = True) -> str:
    url = f"http://{address}:{port}/panel"
    return f"{url}?token={token()}" if with_token else url


def qr_matrix(text: str) -> List[List[bool]]:
    import segno

    code = segno.make(text, error="m")
    return [[bool(cell) for cell in row] for row in code.matrix]
