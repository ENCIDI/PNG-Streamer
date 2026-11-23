"""The one door from the app into the Studio.

When the Studio code is not part of this copy (see app/features.py), `service`
is a stand-in that has no avatar, no inputs and ignores every command, so the
rest of the app works without asking each time."""
from typing import Any, Dict, List, Optional

from app import features


class _NoStudio:
    avatar_id: Optional[str] = None
    frame_revision = 0

    def start(self) -> None:
        pass

    def stop(self) -> None:
        pass

    def doc(self) -> Optional[Dict[str, Any]]:
        return None

    def params(self) -> List[Dict[str, Any]]:
        return []

    def frame(self) -> Optional[Dict[str, Any]]:
        return None

    def debug(self) -> Dict[str, Any]:
        return {}

    def fire(self, key: Any) -> bool:
        return False

    def set_param(self, key: Any, value: Any) -> bool:
        return False

    def play_sequence(self, key: Any) -> bool:
        return False

    def set_mouse(self, *args: Any) -> None:
        pass

    def set_held_keys(self, *args: Any) -> None:
        pass


if features.STUDIO:
    from app.studio.service import service
else:
    service = _NoStudio()


def bound_params(profile: Optional[Dict[str, Any]]) -> list:
    """The inputs of a profile's scene with the profile's bindings (none without the Studio)."""
    if not features.STUDIO:
        return []
    from app.studio.bindings import bound_params as bound

    return bound(profile)


def is_manual(binding: Dict[str, Any]) -> bool:
    return binding.get("source", "none") in ("none", "chat")
