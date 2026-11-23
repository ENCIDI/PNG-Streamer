import locale
import os
import sys
from typing import Dict

from app.modules import storage_manager as sm

_RUSSIAN_SPEAKING_COUNTRIES = {"RU", "BY", "KZ", "KG", "TJ"}

# Russian and English live here; the others are app/assets/locales/<code>.json
# (anything missing there falls back to English).
LANGUAGE_NAMES = {
    "en": "English", "ru": "Русский", "uk": "Українська", "es": "Español", "pt": "Português (Brasil)",
    "de": "Deutsch", "fr": "Français", "it": "Italiano", "pl": "Polski", "tr": "Türkçe",
    "ja": "日本語", "ko": "한국어", "zh": "简体中文",
}
LANGUAGES = ("ru", "en")  # extended below with the locale files that exist

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
        "sound.linux_hint": "PipeWire и PulseAudio работают через ALSA: выберите устройство «pipewire», «pulse» или «По умолчанию» — тогда микрофон берётся из системных настроек звука. Если таких устройств нет, установите пакет pipewire-alsa (или alsa-plugins-pulseaudio).",
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
        "launch.expression": "Выражение",
        "chip.expressions": "Выражений: {count}",
        "tray.expression": "Выражение",
        "images.frames_of": "Кадры · {name}",
        "settings.run_wizard": "Запустить мастер настройки",
        "mode.simple": "Обычный",
        "mode.simple_hint": "Кадры по громкости, моргание и тряска — как раньше.",
        "expressions.title": "Выражения",
        "expressions.hint": "Первое выражение — обычное. Остальные включаются горячими клавишами, кнопками на экране «Запуск», из трея или через API.",
        "expressions.add": "Добавить выражение",
        "expressions.name": "Название",
        "expressions.hotkey": "Горячая клавиша",
        "expressions.hotkey_placeholder": "Нажмите сочетание",
        "expressions.command": "Горячая клавиша системы",
        "expressions.copy_command": "Скопировать команду",
        "expressions.command_copied": "Команда скопирована — назначьте её на сочетание клавиш в настройках системы",
        "expressions.command_hint": "На Linux назначьте скопированную команду на сочетание клавиш в настройках клавиатуры (KDE, GNOME и др.). Сервер для OBS должен быть запущен.",
        "expressions.hotkey_hint": "Работает, даже когда окно свёрнуто. Нажмите поле и затем нужное сочетание клавиш.",
        "expressions.hotkey_busy": "Сочетание {hotkey} уже занято другой программой — выберите другое.",
        "expressions.return_after": "Вернуться через, с",
        "expressions.delete": "Удалить выражение",
        "expressions.delete_title": "Удалить выражение?",
        "expressions.delete_text": "Выражение «{name}» и его кадры будут удалены из профиля.",
        "expressions.default_name": "Обычное",
        "expressions.new_name": "Выражение {index}",
        "animation.title": "Анимация",
        "animation.hint": "Аватар подпрыгивает в начале фразы, слегка тянется и сжимается, дышит в тишине и плавно меняет кадры.",
        "animation.bounce": "Отскок",
        "animation.squash": "Сплющивание",
        "animation.breathing": "Дыхание",
        "animation.transition": "Смена кадров",
        "calibration.button": "Подобрать пороги по голосу",
        "calibration.title": "Подбор порогов по голосу",
        "calibration.intro": "Сначала 3 секунды тишины, затем 6 секунд обычной речи. По записи программа выставит шумодав и пороги кадров.",
        "calibration.start": "Начать",
        "calibration.retry": "Ещё раз",
        "calibration.apply": "Применить",
        "calibration.silence": "Помолчите…",
        "calibration.silence_hint": "Записываем фоновый шум: вентилятор, клавиатуру, комнату.",
        "calibration.speech": "Теперь говорите!",
        "calibration.speech_hint": "Говорите как на стриме: тихо, обычно и пару раз погромче.",
        "calibration.done": "Готово",
        "calibration.result": "Шумодав: {gate}. Пороги кадров: {thresholds}.",
        "calibration.failed": "Голос почти не слышен",
        "calibration.failed_hint": "Проверьте, что выбран правильный микрофон и он не выключен, и попробуйте ещё раз.",
        "calibration.applied": "Пороги подобраны, шумодав: {gate}. Не забудьте сохранить профиль.",
        "onboarding.step": "Шаг {current} из {total}",
        "onboarding.next": "Далее",
        "onboarding.back": "Назад",
        "onboarding.finish": "Готово",
        "onboarding.skip": "Пропустить настройку",
        "onboarding.welcome_title": "Добро пожаловать в PNG Streamer",
        "onboarding.welcome_text": "За пару минут настроим микрофон и аватар и подключим его к OBS. Всё это можно будет поменять позже.",
        "onboarding.mic_title": "Микрофон",
        "onboarding.mic_text": "Выберите микрофон и скажите что-нибудь — индикатор должен двигаться.",
        "onboarding.avatar_title": "Аватар",
        "onboarding.avatar_text": "Начните с примера или добавьте свои картинки.",
        "onboarding.use_sample": "Пример",
        "onboarding.use_own": "Свои картинки",
        "onboarding.pick_images": "Выбрать картинки",
        "onboarding.own_hint": "Картинки встанут кадрами по порядку имён файлов: первая — когда вы молчите, последняя — когда говорите громче всего. Можно перетащить файлы прямо сюда.",
        "onboarding.avatar_name": "Мой аватар",
        "onboarding.calibration_skip": "Можно пропустить — тогда пороги останутся стандартными.",
        "onboarding.done_title": "Всё готово!",
        "onboarding.done_text": "Сервер для OBS запущен. Добавьте аватар на сцену:",
        "packs.import": "Импортировать аватар",
        "packs.export": "Экспортировать аватар…",
        "packs.filter": "Аватар PNG Streamer (*.pga *.pgs *.pngavatar)",
        "packs.imported": "Аватар «{name}» добавлен",
        "packs.exported": "Аватар сохранён: {name}",
        "packs.import_failed": "Не удалось импортировать аватар: {error}",
        "packs.export_failed": "Не удалось экспортировать аватар: {error}",
        "api.title": "Управление извне",
        "api.hint": "Stream Deck, Touch Portal, Bitfocus Companion или горячие клавиши системы могут менять профили изображений и звука, открывая эти адреса (GET или POST). Вместо имени можно указать номер профиля. Сервер для OBS должен быть запущен.",
        "api.example_name": "имя",
        "api.copy": "Скопировать адрес API",
        "api.copied": "Адрес API скопирован",
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
        "sound.linux_hint": "PipeWire and PulseAudio are reached through ALSA: choose the \"pipewire\", \"pulse\" or \"Default\" device to use the microphone selected in your system sound settings. If they are missing, install pipewire-alsa (or alsa-plugins-pulseaudio).",
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
        "launch.expression": "Expression",
        "chip.expressions": "Expressions: {count}",
        "tray.expression": "Expression",
        "images.frames_of": "Frames · {name}",
        "settings.run_wizard": "Run the setup wizard",
        "mode.simple": "Simple",
        "mode.simple_hint": "Frames by volume, blinking and shake — as before.",
        "expressions.title": "Expressions",
        "expressions.hint": "The first expression is the default one. Others are switched by hotkeys, the buttons on the Launch screen, the tray or the API.",
        "expressions.add": "Add expression",
        "expressions.name": "Name",
        "expressions.hotkey": "Hotkey",
        "expressions.hotkey_placeholder": "Press a shortcut",
        "expressions.command": "System shortcut",
        "expressions.copy_command": "Copy command",
        "expressions.command_copied": "Command copied — bind it to a shortcut in your system settings",
        "expressions.command_hint": "On Linux, bind the copied command to a shortcut in your keyboard settings (KDE, GNOME, etc.). The OBS server must be running.",
        "expressions.hotkey_hint": "Works even when the window is minimized. Click the field, then press the key combination.",
        "expressions.hotkey_busy": "{hotkey} is already taken by another program — choose a different one.",
        "expressions.return_after": "Return after, s",
        "expressions.delete": "Delete expression",
        "expressions.delete_title": "Delete expression?",
        "expressions.delete_text": "Expression \"{name}\" and its frames will be removed from the profile.",
        "expressions.default_name": "Default",
        "expressions.new_name": "Expression {index}",
        "animation.title": "Animation",
        "animation.hint": "The avatar hops when you start talking, stretches and squashes a little, breathes while silent and fades between frames.",
        "animation.bounce": "Bounce",
        "animation.squash": "Squash",
        "animation.breathing": "Breathing",
        "animation.transition": "Frame change",
        "calibration.button": "Set thresholds from my voice",
        "calibration.title": "Thresholds from your voice",
        "calibration.intro": "First 3 seconds of silence, then 6 seconds of normal speech. The recording sets the noise gate and the frame thresholds.",
        "calibration.start": "Start",
        "calibration.retry": "Again",
        "calibration.apply": "Apply",
        "calibration.silence": "Stay quiet…",
        "calibration.silence_hint": "Recording background noise: fans, keyboard, the room.",
        "calibration.speech": "Now talk!",
        "calibration.speech_hint": "Talk like on stream: quiet, normal and a couple of times louder.",
        "calibration.done": "Done",
        "calibration.result": "Noise gate: {gate}. Frame thresholds: {thresholds}.",
        "calibration.failed": "Your voice is barely audible",
        "calibration.failed_hint": "Check that the right microphone is selected and not muted, then try again.",
        "calibration.applied": "Thresholds set, noise gate: {gate}. Remember to save the profile.",
        "onboarding.step": "Step {current} of {total}",
        "onboarding.next": "Next",
        "onboarding.back": "Back",
        "onboarding.finish": "Finish",
        "onboarding.skip": "Skip setup",
        "onboarding.welcome_title": "Welcome to PNG Streamer",
        "onboarding.welcome_text": "In a couple of minutes we'll set up your microphone and avatar and connect it to OBS. You can change everything later.",
        "onboarding.mic_title": "Microphone",
        "onboarding.mic_text": "Pick your microphone and say something — the meter should move.",
        "onboarding.avatar_title": "Avatar",
        "onboarding.avatar_text": "Start with the sample or add your own images.",
        "onboarding.use_sample": "Sample",
        "onboarding.use_own": "My images",
        "onboarding.pick_images": "Choose images",
        "onboarding.own_hint": "Images become frames in file name order: the first is shown while you are silent, the last when you are loudest. You can drop files right here.",
        "onboarding.avatar_name": "My avatar",
        "onboarding.calibration_skip": "You can skip this — the thresholds will stay at their defaults.",
        "onboarding.done_title": "All set!",
        "onboarding.done_text": "The OBS server is running. Add the avatar to your scene:",
        "packs.import": "Import avatar",
        "packs.export": "Export avatar…",
        "packs.filter": "PNG Streamer avatar (*.pga *.pgs *.pngavatar)",
        "packs.imported": "Avatar \"{name}\" added",
        "packs.exported": "Avatar saved: {name}",
        "packs.import_failed": "Could not import the avatar: {error}",
        "packs.export_failed": "Could not export the avatar: {error}",
        "api.title": "Remote control",
        "api.hint": "Stream Deck, Touch Portal, Bitfocus Companion or system shortcuts can switch image and sound profiles by opening these addresses (GET or POST). A profile number can be used instead of a name. The OBS server must be running.",
        "api.example_name": "name",
        "api.copy": "Copy API address",
        "api.copied": "API address copied",
    },
}


from app import features  # noqa: E402
from app.ui import i18n_stream  # noqa: E402

_TRANSLATIONS["ru"].update(i18n_stream.RU)
_TRANSLATIONS["en"].update(i18n_stream.EN)
if features.STUDIO:
    from app.ui import i18n_studio

    _TRANSLATIONS["ru"].update(i18n_studio.RU)
    _TRANSLATIONS["en"].update(i18n_studio.EN)
for _obsolete in [k for k in _TRANSLATIONS["ru"] if k.startswith(("animation.", "expressions.")) and k not in (
    "expressions.copy_command", "expressions.command_hint", "expressions.hotkey_placeholder", "expressions.command_copied",
)]:
    _TRANSLATIONS["ru"].pop(_obsolete, None)
    _TRANSLATIONS["en"].pop(_obsolete, None)


def _load_locales() -> None:
    import json

    from app import paths

    global LANGUAGES
    folders = [paths.RESOURCES_DIR / "assets" / "locales"]
    if features.STUDIO:
        folders.append(paths.RESOURCES_DIR / "studio" / "locales")
    loaded = []
    for code in LANGUAGE_NAMES:
        if code in ("ru", "en"):
            continue
        data = {}
        for folder in folders:
            try:
                part = json.loads((folder / f"{code}.json").read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            if isinstance(part, dict):
                data.update(part)
        if data:
            _TRANSLATIONS[code] = {**_TRANSLATIONS["en"], **{k: str(v) for k, v in data.items() if k in _TRANSLATIONS["en"]}}
            loaded.append(code)
    LANGUAGES = tuple(code for code in LANGUAGE_NAMES if code in ("ru", "en") or code in loaded)


_load_locales()


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

    if lang_code in LANGUAGES and lang_code != "ru":
        return lang_code
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
    _current_language = lang if lang in _TRANSLATIONS else "en"
    sm.update_settings({"language": _current_language})


def t(key: str, **kwargs) -> str:
    table = _TRANSLATIONS.get(get_language(), _TRANSLATIONS["en"])
    template = table.get(key) or _TRANSLATIONS["en"].get(key, key)
    if kwargs:
        try:
            return template.format(**kwargs)
        except (KeyError, IndexError, ValueError):  # a broken translation must not crash the UI
            return _TRANSLATIONS["en"].get(key, key).format(**kwargs)
    return template
