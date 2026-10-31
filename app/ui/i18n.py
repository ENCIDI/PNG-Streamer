import locale
import os
import sys
from typing import Dict

from app.modules import storage_manager as sm

_RUSSIAN_SPEAKING_COUNTRIES = {"RU", "BY", "KZ", "KG", "TJ"}

LANGUAGES = ("ru", "en")

_TRANSLATIONS: Dict[str, Dict[str, str]] = {
    "ru": {
        "nav.launch": "Запуск",
        "nav.sound": "Звук",
        "nav.images": "Изображения",
        "nav.settings": "Настройки",
        "status.live": "В эфире",
        "status.stopped": "Остановлен",
        "launch.title": "Запуск",
        "launch.subtitle": "Аватар реагирует на голос и транслируется в OBS",
        "launch.start": "Запустить",
        "launch.stop": "Остановить",
        "launch.preview": "Предпросмотр",
        "launch.preview_hint": "как в OBS",
        "launch.microphone": "Микрофон",
        "launch.volume": "громкость",
        "launch.profiles": "Профили",
        "launch.sound_profile": "Звук",
        "launch.image_profile": "Изображения",
        "launch.obs_source": "Источник для OBS",
        "launch.copy": "Копировать",
        "launch.copied": "Скопировано",
        "launch.port": "Порт",
        "launch.url_stopped": "Запустите сервер, чтобы получить адрес",
        "launch.obs_hint": "OBS → Источники → «Браузер» → вставьте адрес. Фон прозрачный, рекомендуемый размер 600×600.",
        "launch.server_start_failed": "Не удалось запустить сервер на порту {port}. Возможно, порт занят другой программой.",
        "chip.noise_adaptive": "Шумодав · адаптивный",
        "chip.noise_fixed": "Шумодав · порог {value}",
        "chip.noise_off": "Без шумодава",
        "chip.compressor": "Компрессор {ratio}:1",
        "chip.frames": "Кадров: {count}",
        "chip.blink": "Моргание {min}–{max} с",
        "chip.no_blink": "Без моргания",
        "mic.default": "По умолчанию",
        "mic.error_failed": "Микрофон недоступен",
        "mic.error_fallback": "Выбранный микрофон недоступен, используется микрофон по умолчанию",
        "mic.error_unavailable": "Аудиоподсистема недоступна",
        "preview.empty": "В профиле нет кадров",
        "preview.frame": "Кадр {index}  ·  от {level}",
        "profiles.create": "Новый профиль",
        "profiles.new_name": "Новый профиль",
        "profiles.active": "Активен",
        "profiles.activate": "Сделать активным",
        "profiles.rename": "Переименовать",
        "profiles.duplicate": "Дублировать",
        "profiles.delete": "Удалить",
        "profiles.copy_name": "{name} (копия)",
        "profiles.delete_title": "Удалить профиль?",
        "profiles.delete_text": "Профиль «{name}» будет удалён без возможности восстановления.",
        "profiles.delete_last": "Нельзя удалить единственный профиль",
        "profiles.rename_title": "Название профиля",
        "common.save": "Сохранить",
        "common.revert": "Отменить изменения",
        "common.cancel": "Отмена",
        "common.ok": "OK",
        "common.delete": "Удалить",
        "common.unsaved": "Есть несохранённые изменения",
        "common.discard_title": "Сохранить изменения?",
        "common.discard_text": "В профиле «{name}» есть несохранённые изменения.",
        "common.discard": "Не сохранять",
        "notify.saved": "Профиль «{name}» сохранён",
        "notify.created": "Профиль «{name}» создан",
        "notify.deleted": "Профиль «{name}» удалён",
        "notify.activated": "Активен профиль «{name}»",
        "sound.title": "Звук",
        "sound.subtitle": "Микрофон и обработка сигнала",
        "sound.profiles": "Профили звука",
        "sound.input": "Вход",
        "sound.host_api": "Аудиосистема",
        "sound.microphone": "Устройство",
        "sound.output_suffix": "{name} (выход)",
        "sound.level": "Уровень сейчас",
        "sound.noise": "Шумоподавление",
        "sound.noise_hint": "Срезает фоновый шум, чтобы аватар не реагировал на вентилятор или клавиатуру.",
        "sound.algorithm": "Алгоритм",
        "sound.algo_adaptive": "Адаптивный — подстраивается под фон",
        "sound.algo_fixed": "Фиксированный порог",
        "sound.threshold": "Порог",
        "sound.compressor": "Компрессор",
        "sound.compressor_hint": "Сглаживает громкие пики, чтобы крик не перескакивал через средние кадры.",
        "sound.comp_threshold": "Порог сжатия",
        "sound.comp_ratio": "Соотношение",
        "images.title": "Изображения",
        "images.subtitle": "Кадры аватара и пороги громкости",
        "images.profiles": "Профили изображений",
        "images.frames": "Кадры",
        "images.frames_hint": "Кадр включается, когда громкость достигает его порога.",
        "images.add_frame": "Добавить кадр",
        "images.frame": "Кадр {index}",
        "images.image": "Картинка",
        "images.blink_image": "При моргании",
        "images.threshold": "Порог",
        "images.shake": "Тряска",
        "images.none": "Нет",
        "images.remove_frame": "Удалить кадр",
        "images.blink": "Моргание",
        "images.blink_hint": "Случайный интервал между морганиями и длительность моргания.",
        "images.blink_min": "Интервал от, мс",
        "images.blink_max": "Интервал до, мс",
        "images.blink_duration": "Длительность, мс",
        "images.import": "Добавить картинки",
        "images.open_folder": "Открыть папку",
        "images.imported": "Добавлено картинок: {count}",
        "images.import_filter": "Изображения (*.png *.jpg *.jpeg *.gif *.webp)",
        "images.pick_title": "Выберите картинку",
        "images.drop_hint": "Перетащите картинки в окно, чтобы добавить их",
        "images.preview": "Предпросмотр",
        "images.preview_hint": "с живым микрофоном",
        "images.no_frames": "Добавьте первый кадр",
        "settings.title": "Настройки",
        "settings.subtitle": "Поведение программы",
        "settings.general": "Общие",
        "settings.language": "Язык интерфейса",
        "settings.tray_close": "Сворачивать в трей при закрытии окна",
        "settings.tray_unavailable": "Системный трей недоступен в этом окружении — окно будет закрываться.",
        "settings.autostart": "Запускать вместе с системой",
        "settings.start_minimized": "Запускать свёрнутым в трей",
        "settings.start_server": "Запускать сервер для OBS вместе с программой",
        "settings.updates": "Обновления",
        "settings.check_updates": "Проверять обновления автоматически",
        "settings.check_now": "Проверить сейчас",
        "settings.update_source": "Автообновление работает только в установленной версии программы.",
        "settings.update_none": "Установлена последняя версия",
        "settings.update_checking": "Проверка…",
        "settings.update_error": "Не удалось проверить обновления",
        "settings.update_not_release": "Версия {version} не опубликована как релиз — автообновление отключено.",
        "settings.data": "Данные",
        "settings.data_hint": "Профили, картинки и логи хранятся рядом с программой и не затрагиваются обновлениями.",
        "settings.open_data": "Открыть папку данных",
        "settings.open_logs": "Открыть логи",
        "settings.about": "О программе",
        "settings.version": "Версия {version}",
        "settings.licenses": "PNG Streamer распространяется по лицензии MIT. Интерфейс построен на Qt {qt} (PySide6) по лицензии LGPLv3, шрифт Inter — SIL OFL 1.1. Тексты лицензий лежат в папке licenses.",
        "settings.open_licenses": "Открыть лицензии",
        "update.available": "Доступна версия {version}",
        "update.notes": "Что нового",
        "update.install": "Обновить",
        "update.later": "Позже",
        "update.skip": "Пропустить версию",
        "update.downloading": "Загрузка обновления… {percent}%",
        "update.installing": "Устанавливаю обновление, программа перезапустится…",
        "update.failed": "Не удалось обновить: {error}",
        "tray.open": "Открыть PNG Streamer",
        "tray.quit": "Выход",
        "tray.start": "Запустить сервер",
        "tray.stop": "Остановить сервер",
        "tray.copy_url": "Скопировать адрес для OBS",
        "tray.sound_profile": "Профиль звука",
        "tray.image_profile": "Профиль изображений",
        "tray.status_live": "В эфире · порт {port}",
        "tray.status_stopped": "Сервер остановлен",
        "tray.update": "Обновить до {version}",
        "tray.hint_title": "PNG Streamer работает в трее",
        "tray.hint_text": "Окно скрыто, аватар продолжает работать. Откройте программу через значок в трее.",
        "setup.title": "Установка PNG Streamer",
        "setup.text": "Выберите папку для программы. Рядом с ней будут храниться ваши профили и картинки.",
        "setup.folder": "Папка",
        "setup.browse": "Обзор…",
        "setup.menu_entry": "Добавить в меню приложений",
        "setup.desktop_entry": "Ярлык на рабочем столе",
        "setup.install": "Установить",
        "setup.skip": "Запустить отсюда",
        "setup.failed": "Не удалось установить: {error}",
    },
    "en": {
        "nav.launch": "Launch",
        "nav.sound": "Sound",
        "nav.images": "Images",
        "nav.settings": "Settings",
        "status.live": "Live",
        "status.stopped": "Stopped",
        "launch.title": "Launch",
        "launch.subtitle": "Your avatar reacts to your voice and is streamed to OBS",
        "launch.start": "Start",
        "launch.stop": "Stop",
        "launch.preview": "Preview",
        "launch.preview_hint": "as seen in OBS",
        "launch.microphone": "Microphone",
        "launch.volume": "volume",
        "launch.profiles": "Profiles",
        "launch.sound_profile": "Sound",
        "launch.image_profile": "Images",
        "launch.obs_source": "OBS source",
        "launch.copy": "Copy",
        "launch.copied": "Copied",
        "launch.port": "Port",
        "launch.url_stopped": "Start the server to get the address",
        "launch.obs_hint": "OBS → Sources → Browser → paste the address. The background is transparent, 600×600 is a good size.",
        "launch.server_start_failed": "Could not start the server on port {port}. The port may be used by another program.",
        "chip.noise_adaptive": "Noise gate · adaptive",
        "chip.noise_fixed": "Noise gate · threshold {value}",
        "chip.noise_off": "No noise gate",
        "chip.compressor": "Compressor {ratio}:1",
        "chip.frames": "Frames: {count}",
        "chip.blink": "Blink {min}–{max} s",
        "chip.no_blink": "No blinking",
        "mic.default": "Default",
        "mic.error_failed": "Microphone unavailable",
        "mic.error_fallback": "Selected microphone is unavailable, using the default one",
        "mic.error_unavailable": "Audio subsystem unavailable",
        "preview.empty": "This profile has no frames",
        "preview.frame": "Frame {index}  ·  from {level}",
        "profiles.create": "New profile",
        "profiles.new_name": "New profile",
        "profiles.active": "Active",
        "profiles.activate": "Make active",
        "profiles.rename": "Rename",
        "profiles.duplicate": "Duplicate",
        "profiles.delete": "Delete",
        "profiles.copy_name": "{name} (copy)",
        "profiles.delete_title": "Delete profile?",
        "profiles.delete_text": "Profile \"{name}\" will be deleted permanently.",
        "profiles.delete_last": "The only profile cannot be deleted",
        "profiles.rename_title": "Profile name",
        "common.save": "Save",
        "common.revert": "Discard changes",
        "common.cancel": "Cancel",
        "common.ok": "OK",
        "common.delete": "Delete",
        "common.unsaved": "Unsaved changes",
        "common.discard_title": "Save changes?",
        "common.discard_text": "Profile \"{name}\" has unsaved changes.",
        "common.discard": "Don't save",
        "notify.saved": "Profile \"{name}\" saved",
        "notify.created": "Profile \"{name}\" created",
        "notify.deleted": "Profile \"{name}\" deleted",
        "notify.activated": "Profile \"{name}\" is now active",
        "sound.title": "Sound",
        "sound.subtitle": "Microphone and signal processing",
        "sound.profiles": "Sound profiles",
        "sound.input": "Input",
        "sound.host_api": "Audio system",
        "sound.microphone": "Device",
        "sound.output_suffix": "{name} (output)",
        "sound.level": "Current level",
        "sound.noise": "Noise suppression",
        "sound.noise_hint": "Cuts background noise so the avatar ignores fans and keyboards.",
        "sound.algorithm": "Algorithm",
        "sound.algo_adaptive": "Adaptive — follows the background",
        "sound.algo_fixed": "Fixed threshold",
        "sound.threshold": "Threshold",
        "sound.compressor": "Compressor",
        "sound.compressor_hint": "Tames loud peaks so shouting does not skip the middle frames.",
        "sound.comp_threshold": "Threshold",
        "sound.comp_ratio": "Ratio",
        "images.title": "Images",
        "images.subtitle": "Avatar frames and volume thresholds",
        "images.profiles": "Image profiles",
        "images.frames": "Frames",
        "images.frames_hint": "A frame is shown once the volume reaches its threshold.",
        "images.add_frame": "Add frame",
        "images.frame": "Frame {index}",
        "images.image": "Image",
        "images.blink_image": "While blinking",
        "images.threshold": "Threshold",
        "images.shake": "Shake",
        "images.none": "None",
        "images.remove_frame": "Remove frame",
        "images.blink": "Blinking",
        "images.blink_hint": "Random interval between blinks and how long a blink lasts.",
        "images.blink_min": "Interval from, ms",
        "images.blink_max": "Interval to, ms",
        "images.blink_duration": "Duration, ms",
        "images.import": "Add images",
        "images.open_folder": "Open folder",
        "images.imported": "Images added: {count}",
        "images.import_filter": "Images (*.png *.jpg *.jpeg *.gif *.webp)",
        "images.pick_title": "Choose an image",
        "images.drop_hint": "Drop images onto the window to add them",
        "images.preview": "Preview",
        "images.preview_hint": "with live microphone",
        "images.no_frames": "Add the first frame",
        "settings.title": "Settings",
        "settings.subtitle": "How the app behaves",
        "settings.general": "General",
        "settings.language": "Language",
        "settings.tray_close": "Minimize to tray when the window is closed",
        "settings.tray_unavailable": "No system tray in this environment — closing the window quits the app.",
        "settings.autostart": "Start with the system",
        "settings.start_minimized": "Start minimized to tray",
        "settings.start_server": "Start the OBS server together with the app",
        "settings.updates": "Updates",
        "settings.check_updates": "Check for updates automatically",
        "settings.check_now": "Check now",
        "settings.update_source": "Automatic updates only work in the installed version.",
        "settings.update_none": "You have the latest version",
        "settings.update_checking": "Checking…",
        "settings.update_error": "Could not check for updates",
        "settings.update_not_release": "Version {version} is not a published release — automatic updates are off.",
        "settings.data": "Data",
        "settings.data_hint": "Profiles, images and logs live next to the app and are never touched by updates.",
        "settings.open_data": "Open data folder",
        "settings.open_logs": "Open logs",
        "settings.about": "About",
        "settings.version": "Version {version}",
        "settings.licenses": "PNG Streamer is MIT licensed. The interface is built with Qt {qt} (PySide6) under LGPLv3, the Inter font is under SIL OFL 1.1. License texts are in the licenses folder.",
        "settings.open_licenses": "Open licenses",
        "update.available": "Version {version} is available",
        "update.notes": "What's new",
        "update.install": "Update",
        "update.later": "Later",
        "update.skip": "Skip this version",
        "update.downloading": "Downloading update… {percent}%",
        "update.installing": "Installing the update, the app will restart…",
        "update.failed": "Update failed: {error}",
        "tray.open": "Open PNG Streamer",
        "tray.quit": "Quit",
        "tray.start": "Start server",
        "tray.stop": "Stop server",
        "tray.copy_url": "Copy OBS address",
        "tray.sound_profile": "Sound profile",
        "tray.image_profile": "Image profile",
        "tray.status_live": "Live · port {port}",
        "tray.status_stopped": "Server stopped",
        "tray.update": "Update to {version}",
        "tray.hint_title": "PNG Streamer is running in the tray",
        "tray.hint_text": "The window is hidden and the avatar keeps working. Open the app from the tray icon.",
        "setup.title": "Install PNG Streamer",
        "setup.text": "Choose a folder for the app. Your profiles and images will be stored next to it.",
        "setup.folder": "Folder",
        "setup.browse": "Browse…",
        "setup.menu_entry": "Add to the applications menu",
        "setup.desktop_entry": "Desktop shortcut",
        "setup.install": "Install",
        "setup.skip": "Run from here",
        "setup.failed": "Installation failed: {error}",
    },
}


def _detect_unix_locale_name() -> str:
    # POSIX/gettext priority order: LANGUAGE (colon-separated list) beats
    # LC_ALL, which beats LC_MESSAGES, which beats LANG, which beats LC_CTYPE.
    # These env vars are what actually carries the user's language on Linux -
    # locale.getlocale() only reflects them if setlocale() was already called,
    # which most GUI launchers never do, so relying on it alone left every
    # Linux user detected as "en".
    for var in ("LANGUAGE", "LC_ALL", "LC_MESSAGES", "LANG", "LC_CTYPE"):
        value = os.environ.get(var, "")
        if not value:
            continue
        value = value.split(":")[0].strip()
        if value and value not in ("C", "POSIX"):
            return value
    return locale.getlocale()[0] or ""


def detect_system_language() -> str:
    lang_code = ""
    country_code = ""
    try:
        if sys.platform == "win32":
            import ctypes

            lcid = ctypes.windll.kernel32.GetUserDefaultUILanguage()
            locale_name = locale.windows_locale.get(lcid, "")
        else:
            locale_name = _detect_unix_locale_name()
        if locale_name:
            parts = locale_name.replace("-", "_").split("_")
            lang_code = parts[0].lower()
            if len(parts) > 1:
                country_code = parts[1].upper()
    except Exception:
        pass

    if lang_code == "ru" or country_code in _RUSSIAN_SPEAKING_COUNTRIES:
        return "ru"
    return "en"


_current_language = None


def init_language() -> str:
    global _current_language
    settings = sm.load_settings().get("settings", {})
    saved = settings.get("language")
    if saved in _TRANSLATIONS:
        _current_language = saved
    else:
        _current_language = detect_system_language()
        sm.update_settings({"language": _current_language})
    return _current_language


def use_system_language() -> None:
    """Pick the language without touching settings (used before storage exists)."""
    global _current_language
    _current_language = detect_system_language()


def get_language() -> str:
    if _current_language is None:
        return init_language()
    return _current_language


def set_language(lang: str) -> None:
    global _current_language
    _current_language = lang if lang in _TRANSLATIONS else "ru"
    sm.update_settings({"language": _current_language})


def t(key: str, **kwargs) -> str:
    table = _TRANSLATIONS.get(get_language(), _TRANSLATIONS["ru"])
    template = table.get(key, key)
    if kwargs:
        return template.format(**kwargs)
    return template
