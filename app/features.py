"""Parts of the app that are developed but not released yet.

The Studio (app/studio, app/ui/studio and the modules that only serve it) is kept
out of git and out of the build. The app looks for it at start and hides
everything that needs it when it is missing; set PNGSTREAMER_STUDIO=0 to hide it
even when the code is there.
"""
import importlib.util
import os


def _studio_present() -> bool:
    try:
        return importlib.util.find_spec("app.studio.engine_marker") is not None
    except ImportError:
        return False


STUDIO = os.environ.get("PNGSTREAMER_STUDIO", "1") != "0" and _studio_present()
