# 🎙️ PNG Streamer 🚀

![Python Version](https://img.shields.io/badge/Python-3.13%2B-blue?logo=python&logoColor=white)
![Framework](https://img.shields.io/badge/UI-Qt%20(PySide6)-41CD52?logo=qt&logoColor=white)
![Backend](https://img.shields.io/badge/Backend-FastAPI-009688?logo=fastapi&logoColor=white)
![Platforms](https://img.shields.io/badge/Platforms-Windows%20%7C%20Linux-informational)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

**PNG Streamer** is a desktop app for streamers and content creators. It animates your PNG avatar (PNGTuber / VTuber overlay) from your microphone in real time and serves a transparent web widget you add to OBS Studio as a Browser Source. Frames switch by volume, the avatar blinks and shakes — and on top of that there is a control panel on your phone and a Twitch chat overlay.

> [!NOTE]
> The interface is available in English, Russian, Ukrainian, Spanish, Portuguese (Brazil), German, French, Italian, Polish, Turkish, Japanese, Korean and Simplified Chinese — the language is detected from your system and can be changed in **Settings**.

---

### 🌟 Key Features

*   🖥️ **Native Qt interface:** dark graphite theme with a lime accent, works the same on Windows and Linux (X11 and Wayland). Six sections — **Launch**, **Sound**, **Images**, **Chat**, **Web panel**, **Settings**.
*   🎭 **Image profiles:** frames by volume, random blinking and shake; **In OBS** sets where the avatar stands in the Browser source.
*   📱 **Web control panel:** turn your phone, tablet or laptop into a Stream Deck — profile switches, the live avatar, the microphone level and chat. Scan the QR code in the app, no IP addresses to look up. The screen does not go to sleep while the panel is open.
*   💬 **Twitch chat overlay:** a separate browser source for OBS with names, colors, Twitch and 7TV emotes; messages removed by moderators disappear. Read anonymously — no login.
*   👀 **Live preview:** see exactly what OBS will show. The volume meter shows every frame's thumbnail on its threshold and highlights the active one.
*   🎤 **Microphone monitoring:** real-time RMS volume capture.
*   🎧 **Sound profiles:** audio system, device, noise suppression (adaptive or fixed) and a compressor that tames screaming and laughing — applied live while you edit.
*   🧙 **Setup wizard** and 🎯 **thresholds from your voice:** stay quiet for 3 seconds, talk for 6 — the noise gate and frame thresholds are set automatically.
*   🎛️ **Remote control API** for Stream Deck, Touch Portal, Bitfocus Companion or system shortcuts: switch image and sound profiles.
*   📦 **Avatar packs:** export an avatar into one `.pga` file and import it with a double click — easy to share or sell.
*   🌐 **Real-time OBS widget:** fed over WebSocket with all images preloaded — no lag and no flicker.
*   📥 **System tray**, 🔄 **automatic updates** from GitHub Releases that never touch your data, and ⚙️ **start with the system**.

---

### 📦 Installation

Download the latest version from the [Releases](https://github.com/ENCIDI/PNG-Streamer/releases) page.

#### 💻 Windows
Run `PNGStreamer-Setup-X.Y.Z.exe`. The installer does not need administrator rights: it lets you choose a folder (by default `%LOCALAPPDATA%\Programs\PNGStreamer`) and whether to create Start menu and desktop shortcuts.

> [!NOTE]
> The installer is not code-signed yet, so Windows SmartScreen may warn about an unknown publisher on the first run: click **More info → Run anyway**.

#### 🐧 Linux
Download `PNGStreamer-X.Y.Z-x86_64.AppImage`, make it executable and run it:
```bash
chmod +x PNGStreamer-*-x86_64.AppImage
./PNGStreamer-*-x86_64.AppImage
```
On the first start the app offers to move itself into a permanent folder (by default `~/Applications/PNGStreamer`) and to add itself to the applications menu and the desktop. You can also choose **Run from here**.

> [!TIP]
> *   On **GNOME** the tray icon needs the [AppIndicator](https://extensions.gnome.org/extension/615/appindicator-support/) extension (preinstalled on Ubuntu). Without a tray, closing the window quits the app.
> *   If the AppImage does not start because FUSE is missing, install `libfuse2` / `fuse` or run it with `--appimage-extract-and-run`.

#### 🛠️ From source (development)
Requires Python 3.13+.
```bash
python -m venv .venv
# Windows: .\.venv\Scripts\activate    Linux: source .venv/bin/activate
pip install -r requirements-dev.txt
python main.py
```
On Windows `PNGStreamer.bat` does all of this automatically (including installing Python 3.13 via winget). On Linux, install `libportaudio2` from your distribution first.

---

### 🎬 Setting Up OBS Studio

1. Open **Launch**, pick a sound profile and an image profile, then click **Start**.
2. Click **Copy** next to the address (default `http://127.0.0.1:8642/widget`).
3. In OBS Studio add a **Browser** source and paste the address into the URL field.
4. Set the size, e.g. `600` × `600`. The background is transparent.

---

### 🖼️ In OBS: where the avatar stands

In **Images**, the **In OBS** card of every profile sets where the avatar stands in the Browser source: anchor (e.g. bottom center), scale, offset and a horizontal flip. Drag the preview, the wheel scales, a double click puts it back. Profiles with differently sized images then stay in place when you switch between them.

### 🎛️ Remote control API

While the OBS server is running, any tool that can open a URL can switch profiles (GET or POST, names are case-insensitive, a profile number works too):

```text
http://127.0.0.1:8642/api/profile/Fox            switch the image profile
http://127.0.0.1:8642/api/sound-profile/Night    switch the sound profile
http://127.0.0.1:8642/api/status                 current state (JSON)
http://127.0.0.1:8642/api/profiles               all profiles (JSON)
```

**Stream Deck:** use a "Website" / HTTP request action (for example the *API Ninja* or *Web Requests* plugin). **Bitfocus Companion:** the *Generic HTTP* module. **Touch Portal:** the *HTTP GET* action.

### 📱 Web control panel

1. Open **Web panel → Connect** and turn on **Access from other devices**. It is off by default.
2. Scan the QR code with your phone's camera (or open the link). The device must be on the same Wi-Fi network. If the computer has several networks, pick the right address in the list.
3. On Windows the firewall may ask once whether to allow the app — allow it for **private networks**.

The link contains a secret key; after the first visit the device remembers it. **Disconnect all devices** creates a new key, and old links stop working. The panel shows the live avatar, the microphone level, the image and sound profiles and, if enabled, the chat. The **⛶** button in its header switches to full screen; added to the home screen it opens like an app. The screen stays on while the panel is open (tap once if the browser asks).

**Your own layout** (**Web panel → Layout**): until you change anything, the panel shows the avatar, the microphone level and the profile switchers. The editor is a grid like a Stream Deck: drag widgets from the list onto the cells, move them, resize them by the corner and split them into pages with their own number of columns. Widgets: image and sound profile buttons or switchers, headings, the microphone level, the Twitch chat and the live **avatar**. Buttons get their own labels and colors. Everything is saved at once and appears on connected devices right away; **Ctrl+Z** undoes, **Open panel** shows the result in your browser.

### 💬 Twitch chat overlay

1. In **Chat**, enter your channel name (or paste its link) and turn on **Connect chat**.
2. Add another **Browser** source in OBS with `http://127.0.0.1:8642/chat` (e.g. `400` × `600`).
3. The number of messages, how long they stay (0 — forever), the font size and the background are set next to a live preview. Bots (Nightbot, StreamElements…) and !commands can be hidden. Changes reach the overlay in OBS without reloading it.

The chat is read anonymously, without logging in. Messages removed by moderators and timed-out users disappear from the overlay too. **7TV** emotes (global and the channel's own, including zero-width ones like RainTime) are shown in the overlay, the preview and the web panel; they can be turned off.

### 📦 Avatar packs

In **Images**, open a profile's **⋯** menu → **Export avatar…** to save it with all its images into one `.pga` file. Import with the download button above the profile list, by dropping the file onto the window or — on Windows — by double-clicking it.

---

### 🔄 Updates and your data

*   Profiles, images and logs live in the `data` folder **next to the program**. Updates and reinstalls never touch it; the uninstaller asks before deleting it.
*   The app checks [Releases](https://github.com/ENCIDI/PNG-Streamer/releases) once a day (can be turned off in **Settings**) and shows a banner when a new version is out. The download is verified with SHA-256, a backup of your settings is saved to `data/backups/`, and the app restarts into the new version.
*   Updates are only offered to the installed app whose version exactly matches a published release. Running from source or a build of an unreleased version never updates itself.

---

### 📁 Folder Structure

```text
PNGStreamer/
├── PNGStreamer.exe / .AppImage    # The program (main.py when run from source)
└── data/                          # Your data, kept across updates
    ├── settings.json              # General settings
    ├── profiles.json              # Image profiles (frames, thresholds, blink, shake)
    ├── sound_profiles.json        # Sound profiles (device, noise suppression, compressor)
    ├── images/                    # Simple-mode images (*.png, *.jpg, *.gif, *.webp)
    ├── logs/                      # app.log
    └── backups/                   # Settings backups made before updates
```

Repository layout: `app/ui` — Qt interface, `app/modules` — audio, storage, web server, LAN access, Twitch chat, updates and autostart, `app/assets/panel` — the web panel and chat overlay pages, `app/defaults` — the sample profile copied into `data` on first start, `packaging` — PyInstaller, Inno Setup and AppImage build files, `tests` — pytest suite.

---

### ⚙️ Configuration File Schema

Everything is editable in the app, but the files in `data/` are plain JSON. Missing fields are filled with defaults automatically.

#### 1. System settings (`settings.json`)
```json
{
  "schema-version": 4,
  "settings": {
    "active-image-profile-id": 1,
    "active-sound-profile-id": 1,
    "server-port": 8642,
    "language": "en",
    "minimize-to-tray-on-close": true,
    "start-minimized": false,
    "start-server-on-launch": false,
    "check-updates": true,
    "lan-access": false,
    "twitch-channel": "",
    "chat-enabled": false,
    "chat-max": 12,
    "chat-fade-seconds": 45,
    "chat-font-size": 20,
    "chat-bg-opacity": 72,
    "chat-hide-commands": false,
    "chat-7tv": true,
    "chat-hidden-users": "nightbot, streamelements, moobot, fossabot, streamlabs",
    "panel-layout": null
  }
}
```
- `schema-version` — data format version, used to migrate files after updates.
- `active-image-profile-id` / `active-sound-profile-id` — the active profiles.
- `server-port` — port of the OBS widget server.
- `language` — `"en"`, `"ru"`, `"uk"`, `"es"`, `"pt"`, `"de"`, `"fr"`, `"it"`, `"pl"`, `"tr"`, `"ja"`, `"ko"` or `"zh"`.
- `minimize-to-tray-on-close`, `start-minimized`, `start-server-on-launch`, `check-updates` — the switches from **Settings**.
- `lan-access` — the web panel is reachable from other devices; the pairing key is stored in `lan-token`.
- `twitch-channel`, `chat-enabled`, `chat-max`, `chat-fade-seconds` (0 — never hide), `chat-font-size`, `chat-bg-opacity` (0–100), `chat-hide-commands`, `chat-hidden-users`, `chat-7tv` — the chat overlay.
- `panel-layout` — the web panel layout: pages with `cols` and widgets with their cell position `x`, `y` and size `w`, `h`; `null` — automatic.
- The app also stores window geometry and update-check bookkeeping here.

#### 2. Sound profiles (`sound_profiles.json`)
```json
{
  "sound-profiles": [
    {
      "id": 1,
      "name": "default",
      "host-api": null,
      "microphone": null,
      "microphone-name": "Default",
      "unnoised": false,
      "noise-algorithm": "adaptive",
      "noise-threshold": 15.0,
      "compressor-enabled": false,
      "compressor-threshold": 60.0,
      "compressor-ratio": 4.0,
      "effects": []
    }
  ]
}
```
- `host-api` — audio system index in PortAudio, `null` — automatic.
- `microphone` / `microphone-name` — device ID and name (the name is used when the ID changes, e.g. after replugging a USB microphone).
- `unnoised`, `noise-algorithm` (`"adaptive"` / `"fixed"`), `noise-threshold` (0–100) — noise suppression.
- `compressor-enabled`, `compressor-threshold` (0–100), `compressor-ratio` (1–20) — compressor.

#### 3. Image profiles (`profiles.json`)
```json
{
  "profiles": [
    {
      "id": 1,
      "name": "sample",
      "mode": "simple",
      "images": [
        { "id": 0, "path-to-image": "image3.png", "volume-level": 0, "shake-level": 0 },
        { "id": 1, "path-to-image": "image2.png", "volume-level": 30, "shake-level": 1 }
      ],
      "blink": { "interval-min-ms": 2000, "interval-max-ms": 5000, "duration-ms": 100 },
      "blink-images": [
        { "id": 0, "path-to-image": "image0.png" },
        { "id": 1, "path-to-image": "image1.png" }
      ],
      "output": { "anchor": "bottom", "scale": 1.0, "x": 0, "y": 0, "flip": false }
    }
  ]
}
```
- `output` — where the avatar stands in OBS: `anchor` (`center`, `bottom`, `bottom-left`, `top-right`…), `scale`, `x` and `y` in % of the source, `flip`.
- `images[].path-to-image` — file name in `data/images` (or an absolute path), shown when volume `>= volume-level`.
- `images[].shake-level` — shake amplitude in the OBS widget (0 — none).
- `blink` — interval between blinks and blink duration, in milliseconds.
- `blink-images` — the closed-eyes image for the frame with the same `id`.

Profiles from 3.0 are converted automatically.

---

### 🧑‍💻 Development

```bash
python -m pytest            # tests (Qt runs offscreen)
pip install pyinstaller
pyinstaller --noconfirm packaging/pngstreamer.spec   # dist/PNGStreamer
dist/PNGStreamer/PNGStreamer --self-test             # smoke test of the build
```
Releases are built by GitHub Actions: bump `app/version.py`, push a tag `vX.Y.Z` with the same version, and the workflow builds the Windows installer and the Linux AppImage, then creates a **draft** release with `SHA256SUMS`. Users get the update only after the draft is published.

---

### 📜 License
PNG Streamer is distributed under the **MIT License** — free for personal and commercial use, including streams and videos. Builds include Qt (PySide6) under the LGPLv3 and the Inter font under the SIL OFL 1.1; see [`licenses/`](licenses/THIRD_PARTY_NOTICES.md).
