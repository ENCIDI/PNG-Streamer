# PNG Streamer

PNG Streamer — настольное приложение для стримеров: переключает PNG‑аватар по громкости микрофона и отдаёт виджет для OBS.

## Возможности
- Мониторинг громкости микрофона
- Профили с порогами громкости для изображений
- Веб‑виджет (FastAPI) для источника браузера в OBS

## Требования
- Python 3.10+
- Зависимости в `app/requirements.txt`

## Запуск
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
- `app/storage/settings.json` — микрофон, шумоподавление, порт сервера, активный профиль.
- `app/storage/profiles.json` — профили и пороги громкости для изображений.
- `images/` — PNG‑файлы аватара.

---

# PNG Streamer

PNG Streamer is a desktop app for streamers: it switches a PNG avatar based on microphone volume and serves a widget for OBS.

## Features
- Microphone volume monitoring
- Profiles with image volume thresholds
- FastAPI widget for OBS browser source

## Requirements
- Python 3.10+
- Dependencies in `app/requirements.txt`

## Run
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
- `app/storage/settings.json` stores microphone, noise suppression, server port, active profile id.
- `app/storage/profiles.json` stores profiles and image thresholds.
- `images/` contains avatar PNG files.
