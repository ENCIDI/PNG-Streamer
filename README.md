# PNG Streamer

PNG Streamer — настольное приложение для стримеров: переключает PNG‑аватар по громкости микрофона и отдаёт виджет для OBS.

## Возможности
- Мониторинг громкости микрофона
- Шумоподавление микрофона
- Профили с порогами громкости для изображений
- Моргание (blink) и список кадров для него
- Веб‑виджет (FastAPI) для источника браузера в OBS
- Переключение отображения консоли при старте

## Запуск
Быстрый старт:
```powershell
PNGStreamer.bat
```

Вручную:
```powershell
python -m venv .venv
.\.venv\Scripts\activate
pip install -r app\requirements.txt
python main.py
```

## Виджет для OBS
Запустите сервер в приложении и используйте:
```
http://127.0.0.1:<port>/widget
```
как источник браузера.

## Хранение данных
- `app/storage/settings.json` — микрофон, шумоподавление, порт сервера, активный профиль, отображение консоли.
- `app/storage/profiles.json` — профили и пороги громкости для изображений, настройки мигания.
- `images/` — PNG‑файлы аватара.

---

# PNG Streamer

PNG Streamer is a desktop app for streamers: it switches a PNG avatar based on microphone volume and serves a widget for OBS.

## Features
- Microphone volume monitoring
- Microphone noise suppression
- Profiles with image volume thresholds
- Blink settings and blink frames
- FastAPI widget for OBS browser source
- Console visibility toggle on startup

## Run
Quick start:
```powershell
PNGStreamer.bat
```

Manual:
```powershell
python -m venv .venv
.\.venv\Scripts\activate
pip install -r app\requirements.txt
python main.py
```

## OBS Widget
Start the server in the app and use:
```
http://127.0.0.1:<port>/widget
```
as a browser source.

## Storage
- `app/storage/settings.json` stores microphone, noise suppression, server port, active profile, console visibility.
- `app/storage/profiles.json` stores profiles, image thresholds, and blink settings.
- `images/` contains avatar PNG files.
