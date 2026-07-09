# 🎙️ PNG Streamer 🚀

![Python Version](https://img.shields.io/badge/Python-3.13%2B-blue?logo=python&logoColor=white)
![Framework](https://img.shields.io/badge/UI-Flet-9146FF?logo=python&logoColor=white)
![Backend](https://img.shields.io/badge/Backend-FastAPI-009688?logo=fastapi&logoColor=white)
![Server](https://img.shields.io/badge/Server-Uvicorn-purple?logo=uvicorn&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

**🇬🇧 [English](#english)&nbsp;&nbsp;|&nbsp;&nbsp;🇷🇺 [Русский](#русский)**

---

## English

**PNG Streamer** is a modern, flexible desktop app for streamers and content creators. It switches your PNG avatar's (VTuber overlay) frames in real time based on your microphone volume, blinks its eyes, and generates an interactive web widget for smooth integration into OBS Studio as a Browser Source.

> [!NOTE]
> The interface is available in Russian and English — the language is auto-detected from your system, but can be switched manually via the flag button in the app.

---

### 🌟 Key Features

Beyond basic image switching, PNG Streamer packs a number of advanced fine-tuning features:

*   🖥️ **Modern Flet-based UI:** dark purple theme with soft background geometry, a resizable, frameless window, and sidebar navigation with three sections — **Launch**, **Sound Settings**, **Image Settings**. Profile editing happens inline on the page, with no pop-up windows.
*   🌍 **Localization (RU / EN):** the interface language is auto-detected from your system language (Russian for Russia and CIS countries, English otherwise), and can be switched manually with the flag button at the bottom of the sidebar — no restart required.
*   🎤 **Microphone volume monitoring:** high-precision real-time RMS volume capture, with the indicator updating at 30 FPS.
*   🎧 **Independent sound profiles:** microphone, audio protocol (Host API), and noise suppression settings are saved as separate, switchable profiles — just like image profiles, but fully independent from them.
*   🤫 **Two noise suppression algorithms to choose from:** adaptive (continuously tracks the background noise level and adjusts the cutoff threshold) and fixed threshold (a simple, manually configured static gate).
*   🎚️ **Dynamic range compressor:** configurable threshold and ratio — smooths out sharp volume spikes (screaming, laughing) without affecting quiet sounds.
*   📈 **Volume smoothing:** a dedicated smoothing filter — fast attack and slow release — avoids unpleasant frame flickering.
*   🎭 **Multiple image profiles:** unlimited number of profiles, up to 10 volume ranges with individual frames, including an image preview right in the editor.
*   🫨 **Dynamic shake effect (Shake Level):** a vibration level can be set for each volume threshold — the OBS widget smoothly shifts the avatar along the X and Y axes using a sinusoidal noise model.
*   👁️ **Random blinking (Blink Engine):** configurable blink frequency and duration, with automatic selection of the closed-eye frame matching the current volume level.
*   🌐 **High-performance FastAPI OBS widget:** a transparent HTML5 widget; if no frame is available, it serves a transparent 1×1 pixel, preventing a black screen or broken images in OBS.
*   📥 **System tray support:** closing the window minimizes the app to the tray instead of exiting — the server and monitoring keep running in the background.
*   ⚡ **Smart automatic launch:** `.bat` (Windows) or `.sh` (macOS/Linux) will check and install Python 3.13, create a virtual environment, install dependencies (caching them via SHA256 hashes), and launch the app in visible or fully hidden console mode — when the console is shown, the app's full log is mirrored into it.

---

### 📦 Quick Start

#### 💻 Method 1: Automatic (Recommended for Windows)
Just download the project and double-click:
```powershell
PNGStreamer.bat
```
*The script will automatically prepare the environment, install dependencies, and launch the app.*

#### 🛠️ Method 2: Manual, via console
1. Create and activate a virtual environment:
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\activate
   ```
2. Install dependencies:
   ```powershell
   pip install -r app/requirements.txt
   ```
3. Launch the app:
   ```powershell
   python main.py
   ```

---

### 🎬 Setting Up OBS Studio

1. Open the **"Launch"** tab in PNG Streamer, pick a sound profile and an image profile, then click **"Start"**.
2. Copy the widget link from the "Widget address" field (default `http://127.0.0.1:8642/widget`).
3. In OBS Studio, add a new **"Browser"** source (Browser Source).
4. Paste the copied link into the URL field.
5. Set the desired width and height (e.g. `800` by `800` or `1920` by `1080`, depending on your avatar's size).
6. Check **"Control audio via OBS"** if needed, then click **"OK"**.

---

### 📁 Folder & Storage Structure

```text
PNGSteramer/
├── PNGStreamer.bat               # Quick start for Windows
├── PNGStreamer.sh                # Quick start for Linux/macOS
├── main.py                       # Program entry point
├── images/                       # Avatar images go here (*.png)
│   ├── image0.png (Eyes closed / Silent)
│   ├── image1.png (Eyes closed / Speaking)
│   ├── image2.png (Eyes open / Silent)
│   └── image3.png (Eyes open / Speaking)
└── app/
    ├── storage/                  # Configuration storage
    │   ├── settings.json         # General app settings
    │   ├── profiles.json         # Image profiles (volume thresholds, blink, shake)
    │   └── sound_profiles.json   # Sound profiles (microphone, protocol, noise suppression, compressor)
    └── modules/                  # The app's core logic
        └── ui/                   # Flet UI (tabs, tray, shared components)
```

---

### ⚙️ Configuration File Schema

Advanced users can manually edit the settings files in the `app/storage/` folder.

#### 1. System settings (`settings.json`)
```json
{
  "settings": {
    "active-image-profile-id": 1,
    "active-sound-profile-id": 1,
    "server-port": 8642,
    "show-console": false,
    "language": "ru"
  }
}
```
- `active-image-profile-id` / `active-sound-profile-id` — ID of the currently active image / sound profile.
- `server-port` — the FastAPI widget server's port.
- `show-console` — whether to show the console window on startup (controlled by `PNGStreamer.bat`/`.sh`).
- `language` — interface language, `"ru"` or `"en"`. Auto-detected and saved here on first launch; changed afterwards via the flag button in the app.

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
- `host-api` — the audio protocol's (Host API) index in `sounddevice`, `null` — auto.
- `microphone` / `microphone-name` — microphone device ID and its display name (fallback if the ID disappears, e.g. when a USB microphone is unplugged).
- `unnoised` — whether noise suppression is enabled.
- `noise-algorithm` — `"adaptive"` (adaptive, based on background noise) or `"fixed"` (fixed threshold).
- `noise-threshold` — the threshold for the `"fixed"` algorithm (0–100).
- `compressor-enabled` / `compressor-threshold` / `compressor-ratio` — enabling and parameters of the dynamic range compressor.
- `effects` — reserved for future audio effects.

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
      "blink": {
        "interval-min-ms": 2000,
        "interval-max-ms": 5000,
        "duration-ms": 100
      },
      "blink-images": [
        { "id": 0, "path-to-image": "image0.png" },
        { "id": 1, "path-to-image": "image1.png" }
      ]
    }
  ]
}
```
- `images[].path-to-image` — the image, activated when volume is `>= volume-level` (in percent).
- `images[].shake-level` — the vibration level in the OBS widget (0 — no shake).
- `blink` — the minimum/maximum interval between blinks and the duration of closed eyes, in milliseconds.
- `blink-images` — the closed-eyes frame for each `id` from `images`.

---

### 📜 License
This project is distributed under the **MIT License**. You are free to modify and use it for any personal or commercial purpose (including streams and videos).

---

## Русский

**PNG Streamer** — это современное и гибкое настольное приложение для стримеров и контент-мейкеров. Оно позволяет в реальном времени переключать кадры вашего PNG-аватара (VTuber-оверлея) в зависимости от громкости голоса с микрофона, моргать глазами и генерировать интерактивный веб-виджет для плавной интеграции в OBS Studio в качестве Browser Source.

> [!NOTE]
> Интерфейс доступен на русском и английском языках — язык определяется автоматически по системе, но его можно переключить вручную кнопкой-флагом в приложении.

---

### 🌟 Ключевые возможности (Features)

Помимо базового переключения картинок, PNG Streamer содержит множество продвинутых функций для тонкой настройки:

*   🖥️ **Современный интерфейс на Flet:** тёмная фиолетовая тема с мягкой фоновой геометрией, resizable-окно без системной рамки и боковая навигация с тремя разделами — **Запуск**, **Настройки звука**, **Настройки изображений**. Редактирование профилей происходит прямо на странице, без всплывающих окон.
*   🌍 **Локализация (RU / EN):** язык интерфейса определяется автоматически по системному языку (русский — для России и стран СНГ, иначе английский), а переключить его вручную можно кнопкой с флагом внизу боковой панели — без перезапуска приложения.
*   🎤 **Мониторинг громкости микрофона:** высокоточный захват и расчёт RMS громкости в реальном времени, индикатор обновляется с частотой 30 FPS.
*   🎧 **Независимые профили звука:** микрофон, аудио-протокол (Host API) и настройки шумоподавления сохраняются как отдельные переключаемые профили — точно так же, как профили изображений, но полностью независимо от них.
*   🤫 **Два алгоритма шумоподавления на выбор:** адаптивный (сам отслеживает фоновый уровень шума и подстраивает порог отсечки) и фиксированный порог (простой статический гейт с ручной настройкой).
*   🎚️ **Компрессор динамического диапазона:** настраиваемые порог сжатия и соотношение — сглаживает резкие скачки громкости (крик, смех) без потери тихих звуков.
*   📈 **Сглаживание движений (Volume Smoothing):** применяется специальный фильтр сглаживания звука — быстрая атака и медленный релиз, избегая неприятного мерцания кадров.
*   🎭 **Множество профилей изображений:** неограниченное число профилей, до 10 диапазонов громкости с индивидуальными кадрами, включая превью картинки прямо в редакторе.
*   🫨 **Эффект динамической тряски (Shake Level):** для каждого порога громкости можно задать уровень вибрации — OBS-виджет плавно смещает аватар по осям X и Y через синусоидальную модель шума.
*   👁️ **Случайное моргание (Blink Engine):** настраиваемая частота и длительность моргания, с автоматическим подбором закрытого кадра для текущего уровня громкости.
*   🌐 **Высокопроизводительный FastAPI OBS-виджет:** прозрачный HTML5-виджет; при отсутствии кадра отдаёт прозрачный пиксель 1×1, предотвращая чёрный экран или битые изображения в OBS.
*   📥 **Работа в трее (System Tray Icon):** закрытие окна сворачивает приложение в трей вместо выхода — сервер и мониторинг продолжают работать в фоне.
*   ⚡ **Умный автоматический запуск:** `.bat` (Windows) или `.sh` (macOS/Linux) сами проверят и установят Python 3.13, создадут виртуальное окружение, установят зависимости (кэшируя их через хэш-суммы SHA256) и запустят программу в видимом или полностью скрытом консольном режиме — при включённой консоли в неё дублируется весь лог приложения.

---

### 📦 Быстрый старт (Quick Start)

#### 💻 Способ 1: Автоматический (Рекомендуемый для Windows)
Просто скачайте проект и дважды кликните по файлу:
```powershell
PNGStreamer.bat
```
*Скрипт автоматически подготовит окружение, установит зависимости и запустит программу.*

#### 🛠️ Способ 2: Вручную через консоль
1. Создайте виртуальное окружение и активируйте его:
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\activate
   ```
2. Установите зависимости:
   ```powershell
   pip install -r app/requirements.txt
   ```
3. Запустите приложение:
   ```powershell
   python main.py
   ```

---

### 🎬 Настройка в OBS Studio

1. Откройте вкладку **«Запуск»** в приложении PNG Streamer, выберите профиль звука и профиль изображений, затем нажмите кнопку **«Запустить»**.
2. Скопируйте ссылку на виджет из поля «Адрес виджета» (по умолчанию `http://127.0.0.1:8642/widget`).
3. В OBS Studio добавьте новый источник **«Браузер»** (Browser Source).
4. Вставьте скопированную ссылку в поле URL.
5. Установите нужную ширину и высоту (например, `800` на `800` или `1920` на `1080` в зависимости от размера аватара).
6. Поставьте галочку **«Контролировать аудио с помощью OBS»** (при необходимости) и нажмите **«ОК»**.

---

### 📁 Структура папок и хранения данных

```text
PNGSteramer/
├── PNGStreamer.bat               # Быстрый старт Windows
├── PNGStreamer.sh                # Быстрый старт Linux/macOS
├── main.py                       # Точка входа в программу
├── images/                       # Сюда загружаются изображения аватара (*.png)
│   ├── image0.png (Глаза закрыты / Молчание)
│   ├── image1.png (Глаза закрыты / Говорение)
│   ├── image2.png (Глаза открыты / Молчание)
│   └── image3.png (Глаза открыты / Говорение)
└── app/
    ├── storage/                  # Хранилище конфигураций
    │   ├── settings.json         # Общие настройки приложения
    │   ├── profiles.json         # Профили изображений (пороги громкости, моргание, тряска)
    │   └── sound_profiles.json   # Профили звука (микрофон, протокол, шумоподавление, компрессор)
    └── modules/                  # Логическое ядро приложения
        └── ui/                   # Flet-интерфейс (вкладки, трей, общие компоненты)
```

---

### ⚙️ Схема файлов конфигурации

Для опытных пользователей доступно ручное редактирование файлов настроек в папке `app/storage/`.

#### 1. Системные настройки (`settings.json`)
```json
{
  "settings": {
    "active-image-profile-id": 1,
    "active-sound-profile-id": 1,
    "server-port": 8642,
    "show-console": false,
    "language": "ru"
  }
}
```
- `active-image-profile-id` / `active-sound-profile-id` — ID текущего активного профиля изображений / звука.
- `server-port` — порт FastAPI-сервера для виджета.
- `show-console` — показывать ли окно консоли при старте (управляется `PNGStreamer.bat`/`.sh`).
- `language` — язык интерфейса, `"ru"` или `"en"`. При первом запуске определяется автоматически и сохраняется сюда; дальше меняется кнопкой-флагом в приложении.

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
- `host-api` — индекс аудио-протокола (Host API) в `sounddevice`, `null` — авто.
- `microphone` / `microphone-name` — ID устройства микрофона и его отображаемое имя (запасной вариант, если ID пропал, например при отключении USB-микрофона).
- `unnoised` — включено ли шумоподавление.
- `noise-algorithm` — `"adaptive"` (адаптивный по фоновому шуму) или `"fixed"` (фиксированный порог).
- `noise-threshold` — порог для алгоритма `"fixed"` (0–100).
- `compressor-enabled` / `compressor-threshold` / `compressor-ratio` — включение и параметры компрессора динамического диапазона.
- `effects` — зарезервировано под будущие аудиоэффекты.

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
      "blink": {
        "interval-min-ms": 2000,
        "interval-max-ms": 5000,
        "duration-ms": 100
      },
      "blink-images": [
        { "id": 0, "path-to-image": "image0.png" },
        { "id": 1, "path-to-image": "image1.png" }
      ]
    }
  ]
}
```
- `images[].path-to-image` — картинка, активируется при громкости `>= volume-level` (в процентах).
- `images[].shake-level` — уровень вибрации в OBS-виджете (0 — без тряски).
- `blink` — минимальный/максимальный интервал между морганиями и длительность закрытых глаз, в миллисекундах.
- `blink-images` — кадр закрытых глаз для каждого `id` из `images`.

---

### 📜 Лицензия
Этот проект распространяется под лицензией **MIT License**. Вы можете свободно модифицировать и использовать его в любых личных или коммерческих целях (включая трансляции и видеоролики).
