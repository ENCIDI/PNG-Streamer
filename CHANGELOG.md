# Changelog

## 3.0.0

### New
- The interface is rebuilt on Qt (PySide6) and works the same on Windows and Linux (X11 and Wayland).
- Live avatar preview on the Launch and Images screens; the volume meter shows frame thumbnails on their thresholds.
- Image profiles: any number of frames, thumbnail image picker, image import by button or drag and drop.
- Profiles can be renamed and duplicated; deletion asks for confirmation; unsaved changes are tracked and never lost silently.
- Sound profile changes are applied live while editing the active profile.
- System tray: status icon, start/stop server, copy the OBS address, switch profiles, update.
- Settings screen: language, tray behaviour, start with the system (optionally minimized and with the server running), updates, data folder.
- Windows installer (per-user, no admin rights) and Linux AppImage with first-run setup.
- Automatic updates from GitHub Releases with SHA-256 verification; only for installed builds whose version matches a published release.
- Only one copy of the app runs at a time; launching it again shows the running window.

### Changed
- User data moved to the `data` folder next to the program. Files from `app/storage` and `images/` are migrated automatically on first start and left in place.
- Settings files are written atomically; a corrupted file is kept aside as `*.broken-<time>` instead of being overwritten; backups are made before data migrations and updates.
- The OBS server now reports a failure when the port is busy instead of pretending to run.

### Removed
- Flet, pystray, Pillow and SpeechRecognition dependencies.
- The "show console" option from the interface (still honoured by `PNGStreamer.bat` for development).
