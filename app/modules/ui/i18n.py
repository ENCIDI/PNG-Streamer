import locale
import os
import sys
from typing import Dict

from app.modules import storage_manager as sm

_RUSSIAN_SPEAKING_COUNTRIES = {"RU", "BY", "KZ", "KG", "TJ"}

_FLAGS = {"ru": "🇷🇺", "en": "🇬🇧"}

_TRANSLATIONS: Dict[str, Dict[str, str]] = {
    "ru": {
        "nav.launch": "Запуск",
        "nav.sound": "Звук",
        "nav.images": "Изображения",
        "launch.sound_profile": "Профиль звука",
        "launch.image_profile": "Профиль изображений",
        "launch.current_volume": "Текущая громкость",
        "launch.server_section": "Сервер OBS-виджета",
        "launch.server_port": "Порт сервера",
        "launch.status_label": "Статус:",
        "launch.status_running": "Запущен",
        "launch.status_stopped": "Остановлен",
        "launch.start": "Запустить",
        "launch.stop": "Остановить",
        "launch.widget_url": "Адрес виджета",
        "launch.show_console": "Отображать консоль при запуске",
        "launch.server_start_failed": "Не удалось запустить сервер",
        "common.create_profile": "Создать профиль",
        "common.activate_tooltip": "Активировать",
        "common.delete_tooltip": "Удалить",
        "common.active_badge": "Активен",
        "common.empty_state": "Выберите профиль слева или создайте новый",
        "common.new_profile": "Новый профиль",
        "common.editing": "Редактирование: {name}",
        "common.profile_name": "Название профиля",
        "common.save": "Сохранить",
        "common.notify_activated": "Активирован профиль «{name}»",
        "common.notify_deleted": "Профиль «{name}» удалён",
        "common.notify_created": "Профиль «{name}» создан",
        "common.notify_saved": "Профиль «{name}» сохранён",
        "sound.title": "Настройки звука",
        "sound.protocol": "Протокол",
        "sound.microphone": "Микрофон",
        "sound.mic_level": "Уровень микрофона",
        "sound.noise_suppression": "Шумоподавление",
        "sound.noise_algorithm": "Алгоритм шумоподавления",
        "sound.algo_adaptive": "Адаптивный (по фоновому шуму)",
        "sound.algo_fixed": "Фиксированный порог",
        "sound.threshold": "Порог: {value}",
        "sound.compressor": "Компрессор",
        "sound.enabled": "Включён",
        "sound.compressor_threshold": "Порог сжатия: {value}",
        "sound.compressor_ratio": "Соотношение: {value}:1",
        "images.title": "Настройки изображений",
        "images.blink_min": "Мин (мс)",
        "images.blink_max": "Макс (мс)",
        "images.blink_dur": "Длит. (мс)",
        "images.col_index": "#",
        "images.col_image": "Изображение",
        "images.col_blink": "Моргание",
        "images.col_threshold": "Порог",
        "images.col_shake": "Тряска",
        "tray.show": "Показать",
        "tray.quit": "Выход",
    },
    "en": {
        "nav.launch": "Launch",
        "nav.sound": "Sound",
        "nav.images": "Images",
        "launch.sound_profile": "Sound profile",
        "launch.image_profile": "Image profile",
        "launch.current_volume": "Current volume",
        "launch.server_section": "OBS widget server",
        "launch.server_port": "Server port",
        "launch.status_label": "Status:",
        "launch.status_running": "Running",
        "launch.status_stopped": "Stopped",
        "launch.start": "Start",
        "launch.stop": "Stop",
        "launch.widget_url": "Widget address",
        "launch.show_console": "Show console on startup",
        "launch.server_start_failed": "Failed to start the server",
        "common.create_profile": "Create profile",
        "common.activate_tooltip": "Activate",
        "common.delete_tooltip": "Delete",
        "common.active_badge": "Active",
        "common.empty_state": "Select a profile on the left or create a new one",
        "common.new_profile": "New profile",
        "common.editing": "Editing: {name}",
        "common.profile_name": "Profile name",
        "common.save": "Save",
        "common.notify_activated": 'Activated profile "{name}"',
        "common.notify_deleted": 'Profile "{name}" deleted',
        "common.notify_created": 'Profile "{name}" created',
        "common.notify_saved": 'Profile "{name}" saved',
        "sound.title": "Sound settings",
        "sound.protocol": "Protocol",
        "sound.microphone": "Microphone",
        "sound.mic_level": "Microphone level",
        "sound.noise_suppression": "Noise suppression",
        "sound.noise_algorithm": "Noise suppression algorithm",
        "sound.algo_adaptive": "Adaptive (background noise)",
        "sound.algo_fixed": "Fixed threshold",
        "sound.threshold": "Threshold: {value}",
        "sound.compressor": "Compressor",
        "sound.enabled": "Enabled",
        "sound.compressor_threshold": "Compression threshold: {value}",
        "sound.compressor_ratio": "Ratio: {value}:1",
        "images.title": "Image settings",
        "images.blink_min": "Min (ms)",
        "images.blink_max": "Max (ms)",
        "images.blink_dur": "Duration (ms)",
        "images.col_index": "#",
        "images.col_image": "Image",
        "images.col_blink": "Blink",
        "images.col_threshold": "Threshold",
        "images.col_shake": "Shake",
        "tray.show": "Show",
        "tray.quit": "Quit",
    },
}


def detect_system_language() -> str:
    lang_code = ""
    country_code = ""
    try:
        if sys.platform == "win32":
            import ctypes

            lcid = ctypes.windll.kernel32.GetUserDefaultUILanguage()
            locale_name = locale.windows_locale.get(lcid, "")
        else:
            locale_name = locale.getlocale()[0] or os.environ.get("LANG", "")
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


def get_language() -> str:
    if _current_language is None:
        return init_language()
    return _current_language


def set_language(lang: str) -> None:
    global _current_language
    _current_language = lang if lang in _TRANSLATIONS else "ru"
    sm.update_settings({"language": _current_language})


def flag_emoji() -> str:
    return _FLAGS.get(get_language(), _FLAGS["ru"])


def t(key: str, **kwargs) -> str:
    table = _TRANSLATIONS.get(get_language(), _TRANSLATIONS["ru"])
    template = table.get(key, key)
    if kwargs:
        return template.format(**kwargs)
    return template
