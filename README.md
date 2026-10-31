# 🎙️ PNG Streamer 🚀

![Python Version](https://img.shields.io/badge/Python-3.13%2B-blue?logo=python&logoColor=white)
![Framework](https://img.shields.io/badge/UI-Qt%20(PySide6)-41CD52?logo=qt&logoColor=white)
![Backend](https://img.shields.io/badge/Backend-FastAPI-009688?logo=fastapi&logoColor=white)
![Platforms](https://img.shields.io/badge/Platforms-Windows%20%7C%20Linux-informational)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

**EN [English](#english)&nbsp;&nbsp;|&nbsp;&nbsp;RU [Русский](#русский)**

---

## English

**PNG Streamer** is a desktop app for streamers and content creators. It switches your PNG avatar's (PNGTuber / VTuber overlay) frames in real time based on your microphone volume, makes it blink and shake, and serves a transparent web widget you add to OBS Studio as a Browser Source.

> [!NOTE]
> The interface is available in Russian and English — the language is detected from your system and can be changed in **Settings**.

---

### 🌟 Key Features

*   🖥️ **Native Qt interface:** dark graphite theme with a lime accent, works the same on Windows and Linux (X11 and Wayland). Four sections — **Launch**, **Sound**, **Images**, **Settings**.
*   👀 **Live preview:** see exactly what OBS will show, including blinking and shaking. The volume meter shows every frame's thumbnail on its threshold and highlights the frame that is currently active.
*   🎤 **Microphone monitoring:** real-time RMS volume capture, updated at 30 FPS.
*   🎧 **Sound profiles:** audio system, device, noise suppression and compressor are saved as switchable profiles. Changes to the active profile are applied live while you edit, so you can tune them by ear.
*   🤫 **Two noise suppression algorithms:** adaptive (follows the background noise) and fixed threshold.
*   🎚️ **Dynamic range compressor:** tames screaming and laughing so loud peaks do not skip the middle frames.
*   🎭 **Image profiles:** any number of profiles and frames, image picker with thumbnails, drag-and-drop import of new images, explicit save with unsaved-changes tracking.
*   🫨 **Shake level** per frame and 👁️ **random blinking** with a closed-eyes image per frame.
*   🌐 **FastAPI OBS widget:** transparent HTML5 page; if there is no frame it serves a transparent pixel instead of a broken image.
*   📥 **System tray:** status at a glance (live / stopped / microphone error), start and stop the server, copy the OBS address and switch profiles without opening the window.
*   🔄 **Automatic updates** from GitHub Releases that never touch your profiles and images.
*   ⚙️ **Start with the system**, optionally minimized to tray and with the OBS server already running.

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
    ├── images/                    # Avatar images (*.png, *.jpg, *.gif, *.webp)
    ├── logs/                      # app.log
    └── backups/                   # Settings backups made before updates
```

Repository layout: `app/ui` — Qt interface, `app/modules` — audio, storage, web server, updates and autostart, `app/defaults` — the sample profile copied into `data` on first start, `packaging` — PyInstaller, Inno Setup and AppImage build files, `tests` — pytest suite.

---

### ⚙️ Configuration File Schema

Everything is editable in the app, but the files in `data/` are plain JSON. Missing fields are filled with defaults automatically.

#### 1. System settings (`settings.json`)
```json
{
  "schema-version": 1,
  "settings": {
    "active-image-profile-id": 1,
    "active-sound-profile-id": 1,
    "server-port": 8642,
    "language": "en",
    "minimize-to-tray-on-close": true,
    "start-minimized": false,
    "start-server-on-launch": false,
    "check-updates": true
  }
}
```
- `schema-version` — data format version, used to migrate files after updates.
- `active-image-profile-id` / `active-sound-profile-id` — the active profiles.
- `server-port` — port of the OBS widget server.
- `language` — `"ru"` or `"en"`.
- `minimize-to-tray-on-close`, `start-minimized`, `start-server-on-launch`, `check-updates` — the switches from **Settings**.
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
      "images": [
        { "id": 0, "path-to-image": "image3.png", "volume-level": 0, "shake-level": 0 },
        { "id": 1, "path-to-image": "image2.png", "volume-level": 30, "shake-level": 1 },
        { "id": 2, "path-to-image": "image2.png", "volume-level": 80, "shake-level": 99 }
      ],
      "blink": { "interval-min-ms": 2000, "interval-max-ms": 5000, "duration-ms": 100 },
      "blink-images": [
        { "id": 0, "path-to-image": "image0.png" },
        { "id": 1, "path-to-image": "image1.png" }
      ]
    }
  ]
}
```
- `images[].path-to-image` — file name in `data/images` (or an absolute path), shown when volume `>= volume-level`.
- `images[].shake-level` — shake amplitude in the OBS widget (0 — none).
- `blink` — interval between blinks and blink duration, in milliseconds.
- `blink-images` — the closed-eyes image for the frame with the same `id`.

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

---

## Русский

**PNG Streamer** — настольное приложение для стримеров и контент-мейкеров. Оно в реальном времени переключает кадры вашего PNG-аватара (PNGTuber / VTuber-оверлея) в зависимости от громкости микрофона, заставляет его моргать и трястись и отдаёт прозрачный веб-виджет, который добавляется в OBS Studio как источник «Браузер».

> [!NOTE]
> Интерфейс доступен на русском и английском — язык определяется по системе и меняется в **Настройках**.

---

### 🌟 Ключевые возможности

*   🖥️ **Нативный интерфейс на Qt:** тёмная графитовая тема с лаймовым акцентом, одинаково работает на Windows и Linux (X11 и Wayland). Четыре раздела — **Запуск**, **Звук**, **Изображения**, **Настройки**.
*   👀 **Живой предпросмотр:** ровно то, что покажет OBS, включая моргание и тряску. На индикаторе громкости миниатюры кадров стоят на своих порогах, текущий кадр подсвечен.
*   🎤 **Мониторинг микрофона:** расчёт RMS-громкости в реальном времени, обновление 30 раз в секунду.
*   🎧 **Профили звука:** аудиосистема, устройство, шумоподавление и компрессор сохраняются как переключаемые профили. Изменения активного профиля применяются сразу во время редактирования — настраивать можно на слух.
*   🤫 **Два алгоритма шумоподавления:** адаптивный (подстраивается под фоновый шум) и фиксированный порог.
*   🎚️ **Компрессор динамического диапазона:** сглаживает крик и смех, чтобы громкие пики не перескакивали через средние кадры.
*   🎭 **Профили изображений:** любое число профилей и кадров, выбор картинок по миниатюрам, импорт перетаскиванием, явное сохранение с отслеживанием несохранённых изменений.
*   🫨 **Тряска** для каждого кадра и 👁️ **случайное моргание** со своей картинкой закрытых глаз для каждого кадра.
*   🌐 **OBS-виджет на FastAPI:** прозрачная HTML5-страница; если кадра нет, отдаётся прозрачный пиксель вместо битой картинки.
*   📥 **Системный трей:** статус по значку (в эфире / остановлен / ошибка микрофона), запуск и остановка сервера, копирование адреса для OBS и смена профилей без открытия окна.
*   🔄 **Автообновление** из GitHub Releases, которое никогда не трогает ваши профили и картинки.
*   ⚙️ **Запуск вместе с системой** — при желании свёрнутым в трей и сразу с запущенным сервером для OBS.

---

### 📦 Установка

Скачайте последнюю версию со страницы [Releases](https://github.com/ENCIDI/PNG-Streamer/releases).

#### 💻 Windows
Запустите `PNGStreamer-Setup-X.Y.Z.exe`. Установщику не нужны права администратора: он предложит выбрать папку (по умолчанию `%LOCALAPPDATA%\Programs\PNGStreamer`) и создать ярлыки в меню «Пуск» и на рабочем столе.

> [!NOTE]
> Установщик пока не подписан цифровой подписью, поэтому Windows SmartScreen при первом запуске может предупредить о неизвестном издателе: нажмите **Подробнее → Выполнить в любом случае**.

#### 🐧 Linux
Скачайте `PNGStreamer-X.Y.Z-x86_64.AppImage`, сделайте файл исполняемым и запустите:
```bash
chmod +x PNGStreamer-*-x86_64.AppImage
./PNGStreamer-*-x86_64.AppImage
```
При первом запуске программа предложит переместить себя в постоянную папку (по умолчанию `~/Applications/PNGStreamer`) и добавить себя в меню приложений и на рабочий стол. Можно выбрать **Запустить отсюда**.

> [!TIP]
> *   В **GNOME** для значка в трее нужно расширение [AppIndicator](https://extensions.gnome.org/extension/615/appindicator-support/) (в Ubuntu оно стоит по умолчанию). Если трея нет, закрытие окна завершает программу.
> *   Если AppImage не запускается из-за отсутствия FUSE, установите `libfuse2` / `fuse` или запустите с ключом `--appimage-extract-and-run`.

#### 🛠️ Из исходников (для разработки)
Нужен Python 3.13+.
```bash
python -m venv .venv
# Windows: .\.venv\Scripts\activate    Linux: source .venv/bin/activate
pip install -r requirements-dev.txt
python main.py
```
На Windows всё это автоматически делает `PNGStreamer.bat` (включая установку Python 3.13 через winget). На Linux предварительно установите `libportaudio2` из репозитория дистрибутива.

---

### 🎬 Настройка в OBS Studio

1. Откройте **Запуск**, выберите профиль звука и профиль изображений и нажмите **Запустить**.
2. Нажмите **Копировать** рядом с адресом (по умолчанию `http://127.0.0.1:8642/widget`).
3. В OBS Studio добавьте источник **«Браузер»** и вставьте адрес в поле URL.
4. Задайте размер, например `600` × `600`. Фон прозрачный.

---

### 🔄 Обновления и ваши данные

*   Профили, картинки и логи хранятся в папке `data` **рядом с программой**. Обновления и переустановка её не трогают, а деинсталлятор спрашивает, прежде чем её удалить.
*   Раз в сутки программа проверяет [Releases](https://github.com/ENCIDI/PNG-Streamer/releases) (отключается в **Настройках**) и показывает плашку, когда вышла новая версия. Скачанный файл проверяется по SHA-256, копия настроек сохраняется в `data/backups/`, и программа перезапускается уже в новой версии.
*   Обновление предлагается только установленной программе, чья версия точно совпадает с опубликованным релизом. Запуск из исходников или сборка неопубликованной версии никогда не обновляются сами.

---

### 📁 Структура папок

```text
PNGStreamer/
├── PNGStreamer.exe / .AppImage    # Программа (main.py при запуске из исходников)
└── data/                          # Ваши данные, сохраняются при обновлениях
    ├── settings.json              # Общие настройки
    ├── profiles.json              # Профили изображений (кадры, пороги, моргание, тряска)
    ├── sound_profiles.json        # Профили звука (устройство, шумоподавление, компрессор)
    ├── images/                    # Картинки аватара (*.png, *.jpg, *.gif, *.webp)
    ├── logs/                      # app.log
    └── backups/                   # Копии настроек перед обновлениями
```

Устройство репозитория: `app/ui` — интерфейс на Qt, `app/modules` — звук, хранилище, веб-сервер, обновления и автозапуск, `app/defaults` — пример профиля, который копируется в `data` при первом запуске, `packaging` — файлы сборки PyInstaller, Inno Setup и AppImage, `tests` — тесты pytest.

---

### ⚙️ Схема файлов конфигурации

Всё настраивается в программе, но файлы в `data/` — обычный JSON. Недостающие поля заполняются значениями по умолчанию автоматически.

#### 1. Системные настройки (`settings.json`)
```json
{
  "schema-version": 1,
  "settings": {
    "active-image-profile-id": 1,
    "active-sound-profile-id": 1,
    "server-port": 8642,
    "language": "ru",
    "minimize-to-tray-on-close": true,
    "start-minimized": false,
    "start-server-on-launch": false,
    "check-updates": true
  }
}
```
- `schema-version` — версия формата данных, по ней файлы мигрируют после обновлений.
- `active-image-profile-id` / `active-sound-profile-id` — активные профили.
- `server-port` — порт сервера OBS-виджета.
- `language` — `"ru"` или `"en"`.
- `minimize-to-tray-on-close`, `start-minimized`, `start-server-on-launch`, `check-updates` — переключатели из **Настроек**.
- Также программа хранит здесь размер окна и служебные данные проверки обновлений.

#### 2. Профили звука (`sound_profiles.json`)
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
- `host-api` — индекс аудиосистемы в PortAudio, `null` — автоматически.
- `microphone` / `microphone-name` — ID устройства и его имя (имя используется, если ID изменился, например после переподключения USB-микрофона).
- `unnoised`, `noise-algorithm` (`"adaptive"` / `"fixed"`), `noise-threshold` (0–100) — шумоподавление.
- `compressor-enabled`, `compressor-threshold` (0–100), `compressor-ratio` (1–20) — компрессор.

#### 3. Профили изображений (`profiles.json`)
```json
{
  "profiles": [
    {
      "id": 1,
      "name": "sample",
      "images": [
        { "id": 0, "path-to-image": "image3.png", "volume-level": 0, "shake-level": 0 },
        { "id": 1, "path-to-image": "image2.png", "volume-level": 30, "shake-level": 1 },
        { "id": 2, "path-to-image": "image2.png", "volume-level": 80, "shake-level": 99 }
      ],
      "blink": { "interval-min-ms": 2000, "interval-max-ms": 5000, "duration-ms": 100 },
      "blink-images": [
        { "id": 0, "path-to-image": "image0.png" },
        { "id": 1, "path-to-image": "image1.png" }
      ]
    }
  ]
}
```
- `images[].path-to-image` — имя файла в `data/images` (или абсолютный путь); кадр показывается при громкости `>= volume-level`.
- `images[].shake-level` — амплитуда тряски в OBS-виджете (0 — без тряски).
- `blink` — интервал между морганиями и длительность моргания, в миллисекундах.
- `blink-images` — картинка закрытых глаз для кадра с тем же `id`.

---

### 🧑‍💻 Разработка

```bash
python -m pytest            # тесты (Qt работает без окна)
pip install pyinstaller
pyinstaller --noconfirm packaging/pngstreamer.spec   # dist/PNGStreamer
dist/PNGStreamer/PNGStreamer --self-test             # быстрая проверка сборки
```
Релизы собирает GitHub Actions: поднимите версию в `app/version.py`, отправьте тег `vX.Y.Z` с той же версией — workflow соберёт установщик для Windows и AppImage для Linux и создаст **черновик** релиза с `SHA256SUMS`. Пользователи получат обновление только после публикации черновика.

---

### 📜 Лицензия
PNG Streamer распространяется по лицензии **MIT** — свободно для личного и коммерческого использования, включая трансляции и видео. Сборки содержат Qt (PySide6) по лицензии LGPLv3 и шрифт Inter по лицензии SIL OFL 1.1; подробности в [`licenses/`](licenses/THIRD_PARTY_NOTICES.md).
